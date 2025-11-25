"""
Main decorator for tracing LLM calls
"""

import asyncio
import functools
import inspect
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, cast

from langsmith import Client as LangSmithClient
from langsmith import traceable

from kurral.core.artifact import ArtifactGenerator
from kurral.core.config import get_config
from kurral.models.kurral import (
    GraphVersion,
    KurralArtifact,
    ModelConfig,
    ResolvedPrompt,
    ToolCall,
    TokenUsage,
)

T = TypeVar("T")


class TraceContext:
    """Context for capturing trace data during execution"""

    def __init__(
        self,
        function_name: str,
        semantic_bucket: Optional[str],
        tenant_id: str,
        environment: str,
    ):
        self.function_name = function_name
        self.semantic_bucket = semantic_bucket
        self.tenant_id = tenant_id
        self.environment = environment
        self.start_time = datetime.utcnow()
        self.llm_config: Optional[ModelConfig] = None
        self.prompt: Optional[ResolvedPrompt] = None
        self.tool_calls: list[ToolCall] = []
        self.inputs: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}
        self.error: Optional[str] = None
        self.token_usage: Optional["TokenUsage"] = None
        self.graph_version: Optional["GraphVersion"] = None


def _sanitize_for_serialization(obj: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
    """
    Sanitize an object for JSON serialization.
    Replaces non-serializable objects with string representations.
    """
    if current_depth > max_depth:
        return "<max_depth_reached>"
    
    # Handle None, basic types
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        try:
            filtered_items = []
            for item in obj:
                # Skip callback objects in lists
                if hasattr(item, '__class__') and 'Callback' in item.__class__.__name__:
                    continue
                # Skip callable objects
                if callable(item) and not isinstance(item, type):
                    continue
                filtered_items.append(_sanitize_for_serialization(item, max_depth, current_depth + 1))
            return filtered_items
        except Exception:
            return f"<{type(obj).__name__}>"
    
    # Handle dictionaries
    if isinstance(obj, dict):
        try:
            result = {}
            for k, v in obj.items():
                # Skip callbacks and other non-serializable keys
                if k in ("callbacks", "callback_manager"):
                    continue
                # Skip callable objects
                if callable(v):
                    continue
                # Skip callback handler instances
                if hasattr(v, '__class__') and 'Callback' in v.__class__.__name__:
                    continue
                
                result[str(k)] = _sanitize_for_serialization(v, max_depth, current_depth + 1)
            return result
        except Exception:
            return f"<{type(obj).__name__}>"
    
    # Try to serialize with JSON to check if it's serializable
    try:
        import json
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # Not serializable - return a string representation
        return f"<{type(obj).__module__}.{type(obj).__name__} at {hex(id(obj))}>"


def trace_llm(
    semantic_bucket: Optional[str] = None,
    tenant_id: str = "default",
    environment: Optional[str] = None,
    auto_export: Optional[bool] = None,
    export_path: Optional[str] = None,
    langsmith_enabled: Optional[bool] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to trace LLM function calls and generate .kurral artifacts

    Usage:
        @trace_llm(semantic_bucket="customer_support", tenant_id="acme_prod")
        def handle_query(query: str) -> str:
            response = client.chat.completions.create(...)
            return response.choices[0].message.content

    Args:
        semantic_bucket: Business logic category (e.g., "refund_flow")
        tenant_id: Tenant/organization identifier
        environment: Environment name (defaults to config)
        auto_export: Whether to auto-export artifacts (defaults to config)
        export_path: Custom export path (defaults to config storage)
        langsmith_enabled: Enable LangSmith integration (defaults to config)

    Returns:
        Decorated function that captures and exports traces
    """
    config = get_config()

    # Use config defaults if not specified
    if environment is None:
        environment = config.environment
    if auto_export is None:
        auto_export = config.auto_export
    if langsmith_enabled is None:
        langsmith_enabled = config.langsmith_enabled

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Check if function is an async generator
        if inspect.isasyncgenfunction(func):
            @functools.wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any):
                # Create trace context
                context = TraceContext(
                    function_name=func.__name__,
                    semantic_bucket=semantic_bucket,
                    tenant_id=tenant_id,
                    environment=environment,
                )

                # Capture inputs (sanitize non-serializable objects)
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                context.inputs = _sanitize_for_serialization(dict(bound.arguments))

                # Extract graph version (hash of graph structure and tool schemas)
                context.graph_version = _extract_graph_version(args, kwargs)

                # Start timing
                start_ms = time.time() * 1000
                
                outputs_collected = []
                captured_metadata = {}
                generator_error = None
                stream_map = []  # Track streaming positions and timing

                try:
                    # Execute async generator and yield results
                    current_offset = 0
                    idx = 0
                    async for item in func(*args, **kwargs):
                        # Capture timing for this fragment
                        fragment_timestamp_ms = int(time.time() * 1000 - start_ms)
                        
                        # Collect raw items (sanitize later to avoid overhead during streaming)
                        outputs_collected.append(item)
                        
                        # Build stream map for string fragments
                        if isinstance(item, str):
                            fragment_length = len(item)
                            stream_map.append({
                                "fragment": item,
                                "offset": current_offset,
                                "length": fragment_length,
                                "index": idx,
                                "timestamp_ms": fragment_timestamp_ms,
                            })
                            current_offset += fragment_length
                        
                        # Try to capture LLM metadata from streaming chunks
                        # (for LangGraph streams that yield message objects)
                        if hasattr(item, 'response_metadata') and item.response_metadata:
                            captured_metadata.update(item.response_metadata)
                        
                        yield item
                        idx += 1
                    
                except Exception as e:
                    # Capture the error but don't raise yet - we need to generate artifact first
                    generator_error = e
                    context.error = str(e)
                
                finally:
                    # This runs whether generator completes successfully or with error
                    # Stop timing
                    duration_ms = int(time.time() * 1000 - start_ms)
                    
                    # Store outputs (sanitize only the stored subset, not during streaming)
                    total_items = len(outputs_collected)
                    max_items_to_store = 100
                    
                    # Sanitize only the items we're storing (much faster than sanitizing during streaming)
                    sanitized_items = [
                        _sanitize_for_serialization(item) 
                        for item in outputs_collected[:max_items_to_store]
                    ]
                    
                    full_output = ""
                    if outputs_collected and all(isinstance(item, str) for item in outputs_collected):
                        full_output = "".join(str(item) for item in outputs_collected)
                    
                    context.outputs = {
                        "items": sanitized_items,
                        "total_items": total_items,
                        "truncated": total_items > max_items_to_store,
                        "full_text": full_output if full_output else None,
                    }
                    
                    # Add stream map if we captured string fragments
                    if stream_map:
                        # Calculate streaming metrics
                        total_stream_ms = stream_map[-1]["timestamp_ms"] if stream_map else 0
                        avg_fragment_length = sum(f["length"] for f in stream_map) / len(stream_map) if stream_map else 0
                        
                        # Limit stream map size (same as items)
                        truncated_stream_map = stream_map[:max_items_to_store]
                        
                        context.outputs["stream_map"] = truncated_stream_map
                        context.outputs["stream_metadata"] = {
                            "total_fragments": len(stream_map),
                            "total_stream_duration_ms": total_stream_ms,
                            "avg_fragment_length": round(avg_fragment_length, 2),
                            "fragments_per_second": round(len(stream_map) / (total_stream_ms / 1000), 2) if total_stream_ms > 0 else 0,
                            "stream_map_truncated": len(stream_map) > max_items_to_store,
                        }
                    
                    if generator_error:
                        context.outputs["error"] = str(generator_error)

                    # Extract model config, token usage, and prompt from captured metadata
                    if captured_metadata:
                        context.llm_config = _extract_model_config_from_metadata(captured_metadata)
                        context.token_usage = _extract_token_usage_from_metadata(captured_metadata)
                    else:
                        context.llm_config = _extract_model_config_from_result(None)
                    
                    context.prompt = _extract_prompt_from_args(kwargs)

                    # Generate artifact immediately (can't be fully async or it gets garbage collected)
                    if auto_export:
                        # Create artifact synchronously (fast)
                        artifact, artifact_path = _generate_and_export_artifact(
                            context, duration_ms, export_path, config
                        )
                        
                        # Send to LangSmith if enabled
                        if langsmith_enabled and config.langsmith_api_key:
                            try:
                                _send_to_langsmith(artifact, config)
                            except Exception as e:
                                if config.debug:
                                    print(f"⚠️  Failed to send to LangSmith: {e}")
                        
                        # Enrich from LangSmith in background thread (not async task)
                        # Using thread because input() blocks the event loop
                        if langsmith_enabled and config.langsmith_api_key and artifact_path:
                            if config.debug:
                                print(f"🔄 Starting background enrichment for: {artifact_path}")
                            
                            # Run enrichment in a daemon thread so it doesn't block program exit
                            enrichment_thread = threading.Thread(
                                target=_enrich_artifact_from_langsmith_sync,
                                args=(artifact_path, func.__name__, config, duration_ms),
                                daemon=True  # Daemon thread won't prevent program exit
                            )
                            enrichment_thread.start()
                    
                    # Now raise the original error if there was one
                    if generator_error:
                        raise generator_error

            return cast(Callable[..., T], async_gen_wrapper)
        
        # Check if function is async (but not a generator)
        elif inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                # Create trace context
                context = TraceContext(
                    function_name=func.__name__,
                    semantic_bucket=semantic_bucket,
                    tenant_id=tenant_id,
                    environment=environment,
                )

                # Capture inputs (sanitize non-serializable objects)
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                context.inputs = _sanitize_for_serialization(dict(bound.arguments))

                # Start timing
                start_ms = time.time() * 1000

                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    context.outputs = {"result": _sanitize_for_serialization(result)}

                    # Stop timing
                    duration_ms = int(time.time() * 1000 - start_ms)

                    # Try to extract model config and prompt from context
                    context.llm_config = _extract_model_config_from_result(result)
                    context.prompt = _extract_prompt_from_args(kwargs)

                    # Generate artifact
                    if auto_export:
                        artifact, _ = _generate_and_export_artifact(
                            context, duration_ms, export_path, config
                        )

                        # Also send to LangSmith if enabled
                        if langsmith_enabled and config.langsmith_api_key:
                            _send_to_langsmith(artifact, config)

                    return result

                except Exception as e:
                    context.error = str(e)
                    duration_ms = int(time.time() * 1000 - start_ms)

                    # Still try to export even on error
                    if auto_export:
                        artifact, _ = _generate_and_export_artifact(
                            context, duration_ms, export_path, config
                        )

                    raise

            # If LangSmith is enabled, wrap with @traceable
            if langsmith_enabled:
                return traceable(name=func.__name__)(async_wrapper)

            return cast(Callable[..., T], async_wrapper)
        
        else:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                # Create trace context
                context = TraceContext(
                    function_name=func.__name__,
                    semantic_bucket=semantic_bucket,
                    tenant_id=tenant_id,
                    environment=environment,
                )

                # Capture inputs (sanitize non-serializable objects)
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                context.inputs = _sanitize_for_serialization(dict(bound.arguments))

                # Start timing
                start_ms = time.time() * 1000

                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    context.outputs = {"result": _sanitize_for_serialization(result)}

                    # Stop timing
                    duration_ms = int(time.time() * 1000 - start_ms)

                    # Try to extract model config and prompt from context
                    context.llm_config = _extract_model_config_from_result(result)
                    context.prompt = _extract_prompt_from_args(kwargs)

                    # Generate artifact
                    if auto_export:
                        artifact, _ = _generate_and_export_artifact(
                            context, duration_ms, export_path, config
                        )

                        # Also send to LangSmith if enabled
                        if langsmith_enabled and config.langsmith_api_key:
                            _send_to_langsmith(artifact, config)

                    return result

                except Exception as e:
                    context.error = str(e)
                    duration_ms = int(time.time() * 1000 - start_ms)

                    # Still try to export even on error
                    if auto_export:
                        artifact, _ = _generate_and_export_artifact(
                            context, duration_ms, export_path, config
                        )

                    raise

            # If LangSmith is enabled, wrap with @traceable
            if langsmith_enabled:
                return traceable(name=func.__name__)(wrapper)

            return cast(Callable[..., T], wrapper)

    return decorator


def _extract_model_config_from_metadata(metadata: dict[str, Any]) -> ModelConfig:
    """
    Extract model configuration from response metadata (from streaming chunks)
    
    Args:
        metadata: Response metadata dictionary from LLM response
    
    Returns:
        ModelConfig with extracted parameters
    """
    from kurral.models.kurral import LLMParameters
    
    # Extract model name and provider
    model_name = metadata.get("model_name", metadata.get("model", "unknown"))
    
    # Determine provider from model name
    provider = "unknown"
    if "gpt" in model_name.lower() or "o1" in model_name.lower():
        provider = "openai"
    elif "claude" in model_name.lower():
        provider = "anthropic"
    elif "gemini" in model_name.lower():
        provider = "google"
    elif "llama" in model_name.lower():
        provider = "meta"
    
    # Build LLM parameters dict, only including non-None values
    llm_params = {
        "temperature": metadata.get("temperature", 0.7),  # Default temperature
    }
    
    # Only add optional params if they have actual values
    if metadata.get("top_p"):
        llm_params["top_p"] = metadata.get("top_p")
    if metadata.get("top_k"):
        llm_params["top_k"] = metadata.get("top_k")
    if metadata.get("max_tokens"):
        llm_params["max_tokens"] = metadata.get("max_tokens")
    if metadata.get("frequency_penalty"):
        llm_params["frequency_penalty"] = metadata.get("frequency_penalty")
    if metadata.get("presence_penalty"):
        llm_params["presence_penalty"] = metadata.get("presence_penalty")
    if metadata.get("seed"):
        llm_params["seed"] = metadata.get("seed")
    
    params = LLMParameters(**llm_params)
    
    # Extract model version if available (exclude if same as model_name)
    model_version = metadata.get("system_fingerprint")
    if model_version == model_name:
        model_version = None
    
    # Build model config dict, only including non-None/non-empty values
    model_config_dict = {
        "model_name": model_name,
        "provider": provider,
        "parameters": params,
    }
    
    if model_version:
        model_config_dict["model_version"] = model_version
    
    # Only include additional_params if there are actually additional params
    additional = {k: v for k, v in metadata.items() 
                 if k not in ["model_name", "model", "temperature", "top_p", 
                             "top_k", "max_tokens", "frequency_penalty", 
                             "presence_penalty", "seed", "system_fingerprint"]}
    if additional:
        model_config_dict["additional_params"] = additional
    
    return ModelConfig(**model_config_dict)


def _extract_token_usage_from_metadata(metadata: dict[str, Any]) -> "TokenUsage":
    """
    Extract token usage from response metadata
    
    Args:
        metadata: Response metadata dictionary from LLM response
    
    Returns:
        TokenUsage with extracted metrics
    """
    from kurral.models.kurral import TokenUsage
    
    # Extract token counts (different providers use different keys)
    prompt_tokens = (
        metadata.get("prompt_tokens") 
        or metadata.get("input_tokens")
        or metadata.get("usage", {}).get("prompt_tokens")
        or 0
    )
    
    completion_tokens = (
        metadata.get("completion_tokens")
        or metadata.get("output_tokens")
        or metadata.get("usage", {}).get("completion_tokens")
        or 0
    )
    
    total_tokens = (
        metadata.get("total_tokens")
        or metadata.get("usage", {}).get("total_tokens")
        or (prompt_tokens + completion_tokens)
    )
    
    # Extract caching metrics (OpenAI and Anthropic support this)
    cached_tokens = (
        metadata.get("cached_tokens")
        or metadata.get("cache_read_input_tokens")
        or metadata.get("usage", {}).get("prompt_tokens_details", {}).get("cached_tokens")
        or None
    )
    
    cache_creation_tokens = (
        metadata.get("cache_creation_input_tokens")
        or metadata.get("usage", {}).get("prompt_tokens_details", {}).get("cache_creation_tokens")
        or None
    )
    
    # Calculate cache hit rate
    cache_hit_rate = None
    if cached_tokens and prompt_tokens:
        cache_hit_rate = cached_tokens / prompt_tokens
    
    # Extract reasoning tokens (for models like o1)
    reasoning_tokens = (
        metadata.get("reasoning_tokens")
        or metadata.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens")
        or None
    )
    
    # Build token usage dict, only including non-None/non-zero values
    usage_dict = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    
    if cached_tokens:
        usage_dict["cached_tokens"] = cached_tokens
    if cache_creation_tokens:
        usage_dict["cache_creation_tokens"] = cache_creation_tokens
    if cache_hit_rate is not None:
        usage_dict["cache_hit_rate"] = cache_hit_rate
    if reasoning_tokens:
        usage_dict["reasoning_tokens"] = reasoning_tokens
    
    return TokenUsage(**usage_dict)


def _extract_model_config_from_result(result: Any) -> ModelConfig:
    """
    Extract model configuration from LLM response
    
    Attempts to extract from OpenAI/Anthropic/LangChain response objects
    """
    from kurral.models.kurral import LLMParameters
    
    # Try to extract from various response types
    model_name = "unknown"
    provider = "unknown"
    model_version = None
    params = {}
    
    # OpenAI Response
    if hasattr(result, "model"):
        model_name = getattr(result, "model", "unknown")
        provider = "openai"
        
        # Extract model version from name (e.g., "gpt-4-0613" -> "0613")
        if "-" in model_name:
            parts = model_name.split("-")
            if len(parts) > 2 and parts[-1].isdigit():
                model_version = parts[-1]
    
    # Anthropic Response
    elif hasattr(result, "type") and hasattr(result, "model"):
        model_name = getattr(result, "model", "unknown")
        provider = "anthropic"
    
    # LangChain Response
    elif hasattr(result, "response_metadata"):
        metadata = getattr(result, "response_metadata", {})
        model_name = metadata.get("model_name", metadata.get("model", "unknown"))
        
        # Try to determine provider from model name
        if "gpt" in model_name.lower() or "o1" in model_name.lower():
            provider = "openai"
        elif "claude" in model_name.lower():
            provider = "anthropic"
        elif "gemini" in model_name.lower():
            provider = "google"
    
    # Try to extract parameters from response metadata or usage
    if hasattr(result, "response_metadata"):
        metadata = getattr(result, "response_metadata", {})
        params = {
            "temperature": metadata.get("temperature"),
            "top_p": metadata.get("top_p"),
            "max_tokens": metadata.get("max_tokens"),
            "seed": metadata.get("seed"),
        }
    
    # Build LLM parameters dict, only including non-None values
    llm_params = {
        "temperature": params.get("temperature", 0.7),
    }
    
    # Only add optional params if they have actual values
    for param_name in ["top_p", "top_k", "max_tokens", "frequency_penalty", "presence_penalty", "seed"]:
        if params.get(param_name):
            llm_params[param_name] = params.get(param_name)
    
    # Exclude model_version if same as model_name
    if model_version == model_name:
        model_version = None
    
    # Build model config dict, only including non-None values
    model_config_dict = {
        "model_name": model_name,
        "provider": provider,
        "parameters": LLMParameters(**llm_params),
    }
    
    if model_version:
        model_config_dict["model_version"] = model_version
    
    return ModelConfig(**model_config_dict)


def _extract_prompt_from_args(kwargs: dict[str, Any]) -> ResolvedPrompt:
    """
    Extract prompt from function arguments with enhanced tracking
    
    Captures template, variables, and computes all hashes
    """
    template = ""
    template_id = None
    variables = {}
    final_text = ""
    system_prompt = None
    messages = None
    
    # Extract from various argument patterns
    if "messages" in kwargs:
        messages_list = kwargs["messages"]
        if messages_list:
            # Convert messages to final text
            parts = []
            for msg in messages_list:
                if hasattr(msg, "content"):
                    # LangChain message object
                    role = msg.__class__.__name__.replace("Message", "").lower()
                    content = msg.content
                    parts.append(f"{role}: {content}")
                elif isinstance(msg, dict):
                    # Dict message
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    parts.append(f"{role}: {content}")
            
            final_text = "\n".join(parts)
            
            # Extract system prompt if present
            if hasattr(messages_list[0], "content") and messages_list[0].__class__.__name__ == "SystemMessage":
                system_prompt = messages_list[0].content
            elif isinstance(messages_list[0], dict) and messages_list[0].get("role") == "system":
                system_prompt = messages_list[0].get("content", "")
        
        messages = messages_list
    
    elif "prompt" in kwargs:
        prompt_val = kwargs["prompt"]
        final_text = str(prompt_val)
        template = final_text
    
    elif "input" in kwargs:
        # LangChain-style input
        input_val = kwargs["input"]
        if isinstance(input_val, dict):
            final_text = str(input_val)
            variables = input_val
        else:
            final_text = str(input_val)
    
    # Extract template_id if provided
    if "template_id" in kwargs:
        template_id = kwargs["template_id"]
    
    # Extract any variables from kwargs
    if "variables" in kwargs:
        variables.update(kwargs["variables"])
    
    # If we have kwargs with config, include that as a variable (sanitized)
    if "config" in kwargs and not variables:
        variables = {"config": _sanitize_for_serialization(kwargs["config"])}
    
    # Sanitize variables and messages before storing
    sanitized_variables = _sanitize_for_serialization(variables or kwargs)
    sanitized_messages = _sanitize_for_serialization(messages) if messages else None
    
    # Create ResolvedPrompt with auto-hashing
    return ResolvedPrompt(
        template=template or final_text,
        template_id=template_id,
        variables=sanitized_variables,
        final_text=final_text,
        system_prompt=system_prompt,
        messages=sanitized_messages,
    )


def _create_enhanced_tool_call(
    tool_name: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    **kwargs
) -> ToolCall:
    """
    Create an enhanced ToolCall with all tracking fields
    
    Args:
        tool_name: Name of the tool
        inputs: Tool input parameters
        outputs: Tool output/response
        **kwargs: Additional fields (namespace, agent_id, effect_type, etc.)
    """
    from kurral.models.kurral import ToolCall, EffectType, ToolCallStatus
    import time
    
    # Determine effect type based on tool name heuristics
    effect_type = kwargs.get("effect_type")
    if not effect_type:
        tool_lower = tool_name.lower()
        if any(x in tool_lower for x in ["http", "api", "request", "fetch", "get", "post"]):
            effect_type = EffectType.HTTP
        elif any(x in tool_lower for x in ["db", "database", "write", "update", "insert", "delete"]):
            effect_type = EffectType.DB_WRITE
        elif any(x in tool_lower for x in ["email", "send_email", "mail"]):
            effect_type = EffectType.EMAIL
        elif any(x in tool_lower for x in ["file", "fs", "write_file", "read_file"]):
            effect_type = EffectType.FS
        elif any(x in tool_lower for x in ["mcp", "slack", "github"]):
            effect_type = EffectType.MCP
        else:
            effect_type = EffectType.OTHER
    
    # Determine status
    error_text = kwargs.get("error_text") or kwargs.get("error")
    status = ToolCallStatus.ERROR if error_text else ToolCallStatus.OK
    
    return ToolCall(
        tool_name=tool_name,
        namespace=kwargs.get("namespace"),
        agent_id=kwargs.get("agent_id"),
        input=inputs,
        output=outputs,
        summary=kwargs.get("summary"),
        effect_type=effect_type,
        latency_ms=kwargs.get("latency_ms") or kwargs.get("duration_ms"),
        status=status,
        error_flag=bool(error_text),
        error_text=error_text,
        stubbed_in_replay=kwargs.get("stubbed_in_replay", False),
        # Legacy fields for backward compatibility
        inputs=inputs,
        outputs=outputs,
        error=error_text,
        duration_ms=kwargs.get("duration_ms") or kwargs.get("latency_ms"),
    )


def _extract_graph_version(args: tuple, kwargs: dict) -> Optional["GraphVersion"]:
    """
    Extract graph and tool versioning information from function arguments
    
    Attempts to extract from LangGraph CompiledStateGraph objects and tools
    """
    import hashlib
    import json
    from kurral.models.kurral import GraphVersion
    
    graph_hash = None
    graph_checksum = None
    tool_schemas_hash = None
    tools_list = None
    
    # Try to find LangGraph graph in arguments
    graph = None
    if "graph" in kwargs:
        graph = kwargs["graph"]
    else:
        # Check positional args for graph-like objects
        for arg in args:
            if hasattr(arg, "__class__") and "Graph" in arg.__class__.__name__:
                graph = arg
                break
    
    if graph:
        try:
            # Hash the graph structure
            graph_data = {}
            
            # Extract graph nodes
            if hasattr(graph, "nodes"):
                graph_data["nodes"] = list(graph.nodes.keys()) if hasattr(graph.nodes, "keys") else str(graph.nodes)
            
            # Extract graph edges
            if hasattr(graph, "edges"):
                edges_repr = []
                for edge in graph.edges:
                    edges_repr.append(str(edge))
                graph_data["edges"] = edges_repr
            
            # Extract config if available
            if hasattr(graph, "config"):
                try:
                    graph_data["config"] = str(graph.config)
                except:
                    pass
            
            # Compute hash
            graph_str = json.dumps(graph_data, sort_keys=True, default=str)
            graph_hash = hashlib.sha256(graph_str.encode()).hexdigest()
            
            # Compute more detailed checksum including configs
            if hasattr(graph, "__dict__"):
                try:
                    full_repr = str(sorted(graph.__dict__.keys()))
                    graph_checksum = hashlib.sha256(full_repr.encode()).hexdigest()
                except:
                    graph_checksum = graph_hash
            
        except Exception:
            pass  # Silently fail if can't extract graph info
    
    # Try to extract tools
    if "tools" in kwargs:
        tools_arg = kwargs["tools"]
        if isinstance(tools_arg, list):
            tools_list = []
            schemas_for_hash = []
            
            for tool in tools_arg:
                tool_info = {}
                
                # Extract tool name
                if hasattr(tool, "name"):
                    tool_info["name"] = tool.name
                elif hasattr(tool, "__name__"):
                    tool_info["name"] = tool.__name__
                else:
                    tool_info["name"] = str(tool)
                
                # Extract tool schema/description
                schema_str = ""
                if hasattr(tool, "args_schema"):
                    try:
                        schema_str = str(tool.args_schema.schema()) if hasattr(tool.args_schema, "schema") else str(tool.args_schema)
                        tool_info["schema_hash"] = hashlib.sha256(schema_str.encode()).hexdigest()
                    except:
                        pass
                
                if hasattr(tool, "description"):
                    tool_info["description"] = tool.description
                
                # Compute individual tool hash
                tool_str = json.dumps(tool_info, sort_keys=True, default=str)
                tool_info["hash"] = hashlib.sha256(tool_str.encode()).hexdigest()
                
                tools_list.append(tool_info)
                schemas_for_hash.append(tool_str)
            
            # Compute combined tools hash
            if schemas_for_hash:
                combined_schemas = "".join(sorted(schemas_for_hash))
                tool_schemas_hash = hashlib.sha256(combined_schemas.encode()).hexdigest()
    
    # Return GraphVersion if we extracted anything
    if graph_hash or tool_schemas_hash:
        return GraphVersion(
            graph_hash=graph_hash,
            graph_checksum=graph_checksum,
            tool_schemas_hash=tool_schemas_hash,
            tools=tools_list,
        )
    
    return None


def _generate_and_export_artifact(
    context: TraceContext,
    duration_ms: int,
    export_path: Optional[str],
    config: Any,
) -> KurralArtifact:
    """Generate artifact and export to storage"""
    generator = ArtifactGenerator()

    # Use captured or default model config
    from kurral.models.kurral import LLMParameters
    llm_config = context.llm_config or ModelConfig(
        model_name="unknown",
        provider="unknown",
        parameters=LLMParameters(
            temperature=0.7,
        ),
    )

    # Use captured or default prompt
    prompt = context.prompt or ResolvedPrompt(
        template="", variables={}, final_text=""
    )

    # Build semantic buckets
    semantic_buckets = []
    if context.semantic_bucket:
        semantic_buckets.append(context.semantic_bucket)
    semantic_buckets.append(context.function_name)

    # Generate artifact
    artifact = generator.generate(
        run_id=f"local_{context.function_name}_{int(context.start_time.timestamp())}",
        tenant_id=context.tenant_id,
        inputs=context.inputs,
        outputs=context.outputs,
        llm_config=llm_config,
        resolved_prompt=prompt,
        tool_calls=context.tool_calls,
        semantic_buckets=semantic_buckets,
        environment=context.environment,
        duration_ms=duration_ms,
        token_usage=context.token_usage,
        graph_version=context.graph_version,
        error=context.error,
        created_by=f"decorator:{context.function_name}",
    )

    # Export to storage
    saved_path = None
    if export_path:
        artifact.save(export_path)
        saved_path = export_path
    elif config.storage_backend == "memory":
        # Save to in-memory storage (fast access, no I/O)
        try:
            from kurral.storage.memory import get_memory_storage
            mem_storage = get_memory_storage()
            uri = mem_storage.upload(artifact, artifact.kurral_id)
            saved_path = uri
            if config.debug:
                stats = mem_storage.get_stats()
                print(f"💾 Stored in memory: {uri} (count: {stats['artifact_count']}, size: {stats['total_size_mb']}MB)")
        except Exception as e:
            if config.debug:
                print(f"⚠️  Memory storage failed: {e}")
    elif config.storage_backend == "local":
        # Save to local storage
        filename = f"{artifact.kurral_id}.kurral"
        path = config.local_storage_path / filename
        artifact.save(path)
        saved_path = str(path)
    elif config.storage_backend == "api":
        # Upload to Kurral API (cloud storage)
        try:
            from kurral.storage.api import KurralAPIClient
            
            if not config.kurral_api_key:
                raise ValueError("KURRAL_API_KEY is required for API storage mode")
            
            api_client = KurralAPIClient(
                api_key=config.kurral_api_key,
                api_url=config.kurral_api_url,
            )
            uri = api_client.save(artifact)
            saved_path = uri
            if config.debug:
                print(f"✅ Uploaded artifact to Kurral Cloud: {uri}")
        except Exception as e:
            # Fall back to local storage if API fails
            if config.debug:
                print(f"⚠️  Kurral API upload failed: {e}, falling back to local storage")
            filename = f"{artifact.kurral_id}.kurral"
            path = config.local_storage_path / filename
            artifact.save(path)
            saved_path = str(path)
    elif config.custom_bucket_enabled:
        # Upload to user's custom bucket
        try:
            from kurral.storage.r2 import R2Storage
            
            if not config.custom_bucket_name:
                raise ValueError("Custom bucket name is required")
            if not config.custom_bucket_access_key_id:
                raise ValueError("Custom bucket access key ID is required")
            if not config.custom_bucket_secret_access_key:
                raise ValueError("Custom bucket secret access key is required")
            
            # Determine account_id for R2 or use empty string for S3
            account_id = config.custom_bucket_account_id or ""
            
            r2 = R2Storage(
                bucket=config.custom_bucket_name,
                account_id=account_id,
                r2_access_key_id=config.custom_bucket_access_key_id,
                r2_secret_access_key=config.custom_bucket_secret_access_key,
                endpoint_url=config.custom_bucket_endpoint,
                region=config.custom_bucket_region,
            )
            uri = r2.save(artifact)
            saved_path = uri
            if config.debug:
                print(f"✅ Uploaded artifact to custom bucket: {uri}")
        except Exception as e:
            # Fall back to local storage if custom bucket fails
            if config.debug:
                print(f"⚠️  Custom bucket upload failed: {e}, falling back to local storage")
            filename = f"{artifact.kurral_id}.kurral"
            path = config.local_storage_path / filename
            artifact.save(path)
            saved_path = str(path)
    elif config.storage_backend == "r2":
        # Auto-upload to R2 (legacy mode)
        try:
            from kurral.storage.r2 import R2Storage
            
            if not config.r2_bucket:
                raise ValueError("R2 bucket name is required")
            if not config.r2_account_id:
                raise ValueError("R2 account ID is required")
            if not config.r2_access_key_id:
                raise ValueError("R2 access key ID is required")
            if not config.r2_secret_access_key:
                raise ValueError("R2 secret access key is required")
            
            r2 = R2Storage(
                bucket=config.r2_bucket,
                account_id=config.r2_account_id,
                r2_access_key_id=config.r2_access_key_id,
                r2_secret_access_key=config.r2_secret_access_key,
            )
            uri = r2.save(artifact)
            saved_path = uri
            if config.debug:
                print(f"✅ Auto-uploaded artifact to R2: {uri}")
        except Exception as e:
            # Fall back to local storage if R2 fails
            if config.debug:
                print(f"⚠️  R2 upload failed: {e}, falling back to local storage")
            filename = f"{artifact.kurral_id}.kurral"
            path = config.local_storage_path / filename
            artifact.save(path)
            saved_path = str(path)

    return artifact, saved_path


def _send_to_langsmith(artifact: KurralArtifact, config: Any) -> None:
    """Send artifact metadata to LangSmith"""
    try:
        if not config.langsmith_api_key:
            return

        client = LangSmithClient(api_key=config.langsmith_api_key)

        # Send as feedback or metadata
        # This is a simplified version - in production, you'd use proper LangSmith APIs
        # to attach the kurral_id and replay_level as metadata to the trace

    except Exception as e:
        # Don't fail the main execution if LangSmith fails
        print(f"Warning: Failed to send to LangSmith: {e}")


# Convenience function for manual artifact creation
def create_artifact_from_trace(
    run_id: str,
    tenant_id: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    model_name: str,
    provider: str,
    temperature: float,
    prompt_text: str,
    semantic_bucket: Optional[str] = None,
    duration_ms: int = 0,
    **kwargs: Any,
) -> KurralArtifact:
    """
    Manually create a Kurral artifact from trace data

    Useful when you can't use the decorator (e.g., legacy code)

    Example:
        artifact = create_artifact_from_trace(
            run_id="manual_123",
            tenant_id="acme",
            inputs={"query": "hello"},
            outputs={"response": "hi there"},
            model_name="gpt-4",
            provider="openai",
            temperature=0.0,
            prompt_text="You are a helpful assistant",
            semantic_bucket="greetings"
        )
        artifact.save("trace.kurral")
    """
    generator = ArtifactGenerator()

    from kurral.models.kurral import LLMParameters
    model_config = ModelConfig(
        model_name=model_name,
        provider=provider,
        parameters=LLMParameters(
            temperature=temperature,
            seed=kwargs.get("random_seed"),
            max_tokens=kwargs.get("max_tokens"),
        ),
    )

    prompt = ResolvedPrompt(
        template=prompt_text,
        variables=kwargs.get("variables", {}),
        final_text=prompt_text,
    )

    semantic_buckets = [semantic_bucket] if semantic_bucket else []

    return generator.generate(
        run_id=run_id,
        tenant_id=tenant_id,
        inputs=inputs,
        outputs=outputs,
        llm_config=model_config,  # local variable is model_config, parameter is llm_config
        resolved_prompt=prompt,
        semantic_buckets=semantic_buckets,
        duration_ms=duration_ms,
        **kwargs,
    )


def _enrich_artifact_from_langsmith_sync(
    artifact_path: str,
    function_name: str,
    config: Any,
    duration_ms: int
) -> None:
    """
    Background thread to enrich artifact with LangSmith data
    
    This runs in a separate thread and updates the artifact file after LangSmith indexing completes.
    Uses threading instead of async to avoid being blocked by input() calls.
    """
    try:
        if config.debug:
            print(f"⏰ Waiting 2s for LangSmith to index trace...")
        
        # Wait for LangSmith to finish indexing the trace
        time.sleep(2.0)  # Use time.sleep() instead of await asyncio.sleep()
        
        if config.debug:
            print(f"⏰ Sleep complete, loading artifact: {artifact_path}")
        
        # Load the artifact
        import json
        from pathlib import Path
        artifact_file = Path(artifact_path)
        
        if not artifact_file.exists():
            return
        
        with open(artifact_file, 'r') as f:
            artifact_data = json.load(f)
        
        # Create a temporary context to hold enriched data
        context = TraceContext(
            function_name=function_name,
            semantic_bucket=artifact_data.get("semantic_buckets", [""])[0],
            tenant_id=artifact_data.get("tenant_id", ""),
            environment=artifact_data.get("environment", "development"),
        )
        
        # Enrich from LangSmith
        _enrich_context_from_langsmith(context, function_name, config)
        
        # Update artifact with enriched data using Pydantic serialization (excludes None values)
        if context.llm_config and context.llm_config.model_name != "unknown":
            # Use model_dump with exclude_none=True to automatically skip null fields
            artifact_data["llm_config"] = json.loads(
                context.llm_config.model_dump_json(exclude_none=True)
            )
        
        if context.tool_calls:
            # Use model_dump with exclude_none=True for each tool call
            artifact_data["tool_calls"] = [
                json.loads(tc.model_dump_json(exclude_none=True))
                for tc in context.tool_calls
            ]
        
        if context.token_usage and context.token_usage.total_tokens > 0:
            # Use model_dump with exclude_none=True for token usage
            artifact_data["token_usage"] = json.loads(
                context.token_usage.model_dump_json(exclude_none=True)
            )
        
        # Write updated artifact
        with open(artifact_file, 'w') as f:
            json.dump(artifact_data, f, indent=2, default=str)
        
        if config.debug:
            print(f"✅ Artifact enriched with LangSmith data: {artifact_path}")
            
    except Exception as e:
        if config.debug:
            print(f"⚠️  Background enrichment failed: {e}")
        import logging
        logging.debug(f"Failed to enrich artifact from LangSmith: {e}")


def _enrich_context_from_langsmith(context: TraceContext, function_name: str, config: Any) -> None:
    """
    Enrich context with data from LangSmith trace
    
    Fetches the most recent LangSmith run for this function and extracts:
    - Tool calls with full details
    - LLM configuration (model, temperature, etc.)
    - Token usage
    """
    import logging
    logger = logging.getLogger(__name__)
    debug = config.debug
    
    try:
        if not config.langsmith_api_key:
            if debug:
                print("⚠️  No LangSmith API key configured, skipping enrichment")
            return
            
        client = LangSmithClient(api_key=config.langsmith_api_key)
        project_name = config.langsmith_project or "default"
        
        if debug:
            print(f"🔍 Searching LangSmith for traces in project: {project_name}")
        
        # Search for LLM/Chain runs (not tool runs) - these contain the model config
        runs = client.list_runs(
            project_name=project_name,
            limit=20,  # Get more runs to find the right one
        )
        
        runs_list = list(runs)
        if debug:
            print(f"✅ Found {len(runs_list)} total runs in LangSmith")
        
        if not runs_list:
            if debug:
                print(f"❌ No LangSmith runs found in project {project_name}")
            return
        
        # Find the ROOT run (the one without a parent - this has all child runs)
        # First try to find a run without parent_run_id (root of trace)
        latest_run = None
        for run in runs_list:
            # Root runs have no parent_run_id or it's None
            if not hasattr(run, 'parent_run_id') or run.parent_run_id is None:
                latest_run = run
                break
        
        # Fallback to first run if no root found
        if not latest_run:
            latest_run = runs_list[0]
        
        if debug:
            print(f"📝 Using run: {latest_run.name} (Type: {latest_run.run_type}, ID: {latest_run.id})")
        
        # Fetch ALL descendant runs (children, grandchildren, etc.)
        child_runs = []
        llm_run_for_config = None
        try:
            # Get all runs that are part of this trace
            trace_id = latest_run.trace_id if hasattr(latest_run, "trace_id") else latest_run.id
            
            if debug:
                print(f"🔎 Querying descendants with trace_id: {trace_id}")
            
            all_descendants = client.list_runs(
                project_name=project_name,
                filter=f'eq(trace_id, "{trace_id}")',
                limit=100,  # Get more runs
            )
            descendants_list = list(all_descendants)
            
            if debug:
                print(f"🔎 Query returned {len(descendants_list)} runs total")
            
            # Filter out the root run itself and organize by type
            for desc in descendants_list:
                if str(desc.id) == str(latest_run.id):
                    continue  # Skip root
                
                child_dict = {
                    "id": str(desc.id),
                    "name": desc.name,
                    "run_type": desc.run_type,
                    "start_time": desc.start_time.isoformat() if desc.start_time else None,
                    "end_time": desc.end_time.isoformat() if desc.end_time else None,
                    "inputs": desc.inputs or {},
                    "outputs": desc.outputs or {},
                    "error": desc.error,
                    "serialized": desc.serialized or {},
                    "extra": desc.extra or {},
                    # Token usage from direct fields
                    "prompt_tokens": getattr(desc, "prompt_tokens", None),
                    "completion_tokens": getattr(desc, "completion_tokens", None),
                    "total_tokens": getattr(desc, "total_tokens", None),
                }
                child_runs.append(child_dict)
                
                # Find the first LLM run for config extraction
                if desc.run_type == "llm" and not llm_run_for_config:
                    llm_run_for_config = child_dict
                    if debug:
                        print(f"  - 🤖 LLM: {desc.name}")
                elif desc.run_type == "tool":
                    if debug:
                        print(f"  - 🔧 Tool: {desc.name}")
                elif debug:
                    print(f"  - {desc.name} ({desc.run_type})")
            
            if debug:
                print(f"👶 Found {len(child_runs)} descendant runs (tools, LLMs, etc.)")
        except Exception as child_err:
            if debug:
                print(f"⚠️  Failed to fetch descendant runs: {child_err}")
        
        # Convert run to dict for processing (include token usage fields)
        run_dict = {
            "id": str(latest_run.id),
            "name": latest_run.name,
            "run_type": latest_run.run_type,
            "start_time": latest_run.start_time.isoformat() if latest_run.start_time else None,
            "end_time": latest_run.end_time.isoformat() if latest_run.end_time else None,
            "inputs": latest_run.inputs or {},
            "outputs": latest_run.outputs or {},
            "serialized": latest_run.serialized or {},
            "error": latest_run.error,
            "tags": latest_run.tags or [],
            "extra": latest_run.extra or {},
            "child_runs": child_runs,
            # Token usage from direct fields
            "prompt_tokens": getattr(latest_run, "prompt_tokens", None),
            "completion_tokens": getattr(latest_run, "completion_tokens", None),
            "total_tokens": getattr(latest_run, "total_tokens", None),
        }
        
        # Extract model config from LangSmith run (try LLM child run first)
        generator = ArtifactGenerator()
        if not context.llm_config or context.llm_config.model_name == "unknown":
            try:
                # Try to extract from LLM child run first (more accurate)
                if llm_run_for_config:
                    if debug:
                        print(f"📊 Extracting from LLM run: {llm_run_for_config.get('name')}")
                        # Debug the structure
                        serialized = llm_run_for_config.get('serialized', {})
                        kwargs = serialized.get('kwargs', {})
                        print(f"📊   serialized.id: {serialized.get('id')}")
                        print(f"📊   kwargs.model_name: {kwargs.get('model_name')}")
                        print(f"📊   run name: {llm_run_for_config.get('name')}")
                    extracted_config = generator._extract_model_config(llm_run_for_config)
                else:
                    # Fallback to root run
                    if debug:
                        print(f"📊 No LLM child run, using root run: {run_dict.get('name')}")
                    extracted_config = generator._extract_model_config(run_dict)
                
                if extracted_config and extracted_config.model_name != "unknown":
                    context.llm_config = extracted_config
                    if debug:
                        print(f"🤖 Extracted LLM config: {extracted_config.model_name} (provider: {extracted_config.provider})")
                else:
                    if debug:
                        print(f"⚠️  Failed to extract valid LLM config (got: {extracted_config.model_name if extracted_config else 'None'})")
            except Exception as config_err:
                if debug:
                    print(f"❌ Error extracting model config: {config_err}")
                    import traceback
                    traceback.print_exc()
        
        # Extract token usage from LangSmith run
        if not context.token_usage or context.token_usage.total_tokens == 0:
            try:
                # Try to extract from LLM child run first (most accurate)
                run_for_usage = llm_run_for_config or run_dict
                
                # Check multiple locations for token usage
                usage_data = {}
                
                # 1. Check outputs field (common location)
                outputs = run_for_usage.get("outputs", {})
                if isinstance(outputs, dict):
                    # Check for usage in llm_output
                    llm_output = outputs.get("llm_output", {})
                    if isinstance(llm_output, dict) and "token_usage" in llm_output:
                        token_usage_dict = llm_output["token_usage"]
                        if isinstance(token_usage_dict, dict):
                            usage_data.update(token_usage_dict)
                    
                    # Check for direct usage field
                    if "usage" in outputs:
                        usage = outputs["usage"]
                        if isinstance(usage, dict):
                            usage_data.update(usage)
                
                # 2. Check extra.metadata
                if not usage_data.get("total_tokens"):
                    metadata = run_for_usage.get("extra", {}).get("metadata", {})
                    if isinstance(metadata, dict):
                        usage_data.update(metadata)
                
                # 3. Check direct fields on run
                if not usage_data.get("total_tokens"):
                    usage_data.update({
                        "prompt_tokens": run_for_usage.get("prompt_tokens"),
                        "completion_tokens": run_for_usage.get("completion_tokens"),
                        "total_tokens": run_for_usage.get("total_tokens"),
                    })
                
                # 4. Try to get from root run if using child run didn't work
                if (not usage_data.get("total_tokens")) and llm_run_for_config:
                    root_outputs = run_dict.get("outputs", {})
                    if isinstance(root_outputs, dict):
                        llm_output = root_outputs.get("llm_output", {})
                        if isinstance(llm_output, dict) and "token_usage" in llm_output:
                            usage_data.update(llm_output["token_usage"])
                
                if debug:
                    print(f"🔍 Checking token usage in run: {run_for_usage.get('name')}")
                    print(f"🔍   outputs type: {type(outputs)}, keys: {list(outputs.keys()) if isinstance(outputs, dict) else 'N/A'}")
                    if isinstance(outputs, dict) and 'llm_output' in outputs:
                        llm_out = outputs['llm_output']
                        print(f"🔍   llm_output type: {type(llm_out)}, keys: {list(llm_out.keys()) if isinstance(llm_out, dict) else 'N/A'}")
                    print(f"🔍 Token usage data found: {usage_data}")
                
                if usage_data and (usage_data.get("total_tokens") or usage_data.get("prompt_tokens")):
                    context.token_usage = _extract_token_usage_from_metadata(usage_data)
                    if debug and context.token_usage:
                        print(f"💰 Extracted token usage: {context.token_usage.total_tokens} total ({context.token_usage.prompt_tokens} prompt + {context.token_usage.completion_tokens} completion)")
                        if context.token_usage.cached_tokens:
                            print(f"    💾 Cached: {context.token_usage.cached_tokens} tokens ({context.token_usage.cache_hit_rate:.1%} hit rate)")
                else:
                    if debug:
                        print(f"⚠️  No token usage found in run outputs or metadata")
            except Exception as usage_err:
                if debug:
                    print(f"❌ Error extracting token usage: {usage_err}")
                    import traceback
                    traceback.print_exc()
        
        # Extract tool calls from LangSmith run (includes child runs)
        if not context.tool_calls:
            try:
                if debug:
                    print(f"🔧 Attempting to extract tool calls from run_dict with {len(child_runs)} child runs")
                
                extracted_tools = generator._extract_tool_calls(run_dict)
                if extracted_tools:
                    context.tool_calls = extracted_tools
                    if debug:
                        print(f"🔧 Extracted {len(extracted_tools)} tool calls")
                        for tc in extracted_tools[:3]:  # Show first 3
                            print(f"     - {tc.tool_name}")
                else:
                    if debug:
                        print(f"ℹ️  No tool calls found in run (child_runs in dict: {len(run_dict.get('child_runs', []))})")
            except Exception as tools_err:
                if debug:
                    print(f"❌ Error extracting tool calls: {tools_err}")
                    import traceback
                    traceback.print_exc()
        
    except Exception as e:
        if debug:
            print(f"❌ Failed to enrich from LangSmith: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        pass

