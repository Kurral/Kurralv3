"""
trace_llm decorator for automatic artifact generation
"""
import functools
import inspect
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, cast

from kurral.models.kurral import (
    ModelConfig,
    LLMParameters,
    ResolvedPrompt,
    ToolCall,
    TokenUsage,
)
from kurral.artifact_manager import ArtifactManager
from kurral.artifact_generator import ArtifactGenerator

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
        self.token_usage: Optional[TokenUsage] = None


def _sanitize_for_serialization(obj: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
    """Sanitize an object for JSON serialization"""
    # Check simple types FIRST - they don't count towards depth and should always be preserved
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # Check empty collections - they don't need depth increment
    if isinstance(obj, (list, tuple)) and len(obj) == 0:
        return []
    if isinstance(obj, dict) and len(obj) == 0:
        return {}
    
    # Now check depth for complex types only
    if current_depth > max_depth:
        return "<max_depth_reached>"
    
    # Handle LangChain message objects
    if hasattr(obj, '__class__'):
        class_name = obj.__class__.__name__
        # Extract content from LangChain messages
        if "Message" in class_name or "AIMessage" in class_name or "HumanMessage" in class_name:
            if hasattr(obj, "content"):
                return str(obj.content)
            elif hasattr(obj, "text"):
                return str(obj.text)
        
        # Handle LangChain Document objects
        if "Document" in class_name:
            if hasattr(obj, "page_content"):
                return {
                    "page_content": str(obj.page_content),
                    "metadata": _sanitize_for_serialization(getattr(obj, "metadata", {}), max_depth, current_depth + 1) if hasattr(obj, "metadata") else {}
                }
    
    if isinstance(obj, (list, tuple)):
        try:
            filtered_items = []
            for item in obj:
                if hasattr(item, '__class__') and 'Callback' in item.__class__.__name__:
                    continue
                if callable(item) and not isinstance(item, type):
                    continue
                filtered_items.append(_sanitize_for_serialization(item, max_depth, current_depth + 1))
            return filtered_items
        except Exception:
            return f"<{type(obj).__name__}>"
    
    if isinstance(obj, dict):
        try:
            result = {}
            for k, v in obj.items():
                if k in ("callbacks", "callback_manager"):
                    continue
                if callable(v):
                    continue
                if hasattr(v, '__class__') and 'Callback' in v.__class__.__name__:
                    continue
                result[str(k)] = _sanitize_for_serialization(v, max_depth, current_depth + 1)
            return result
        except Exception:
            return f"<{type(obj).__name__}>"
    
    try:
        import json
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return f"<{type(obj).__module__}.{type(obj).__name__} at {hex(id(obj))}>"


def _extract_model_config_from_llm_object(llm_obj: Any) -> Optional[ModelConfig]:
    """Extract model config from LangChain LLM object"""
    if llm_obj is None:
        return None
    
    model_name = "unknown"
    provider = "unknown"
    temperature = 0.0
    
    # Try to extract from LangChain LLM objects
    # ChatOllama
    if hasattr(llm_obj, "model"):
        model_name = getattr(llm_obj, "model", "unknown")
        if hasattr(llm_obj, "temperature"):
            temperature = getattr(llm_obj, "temperature", 0.0)
        # Check class name to determine provider
        class_name = llm_obj.__class__.__name__.lower()
        if "ollama" in class_name or "llama" in class_name:
            provider = "ollama"
        elif "openai" in class_name:
            provider = "openai"
        elif "anthropic" in class_name or "claude" in class_name:
            provider = "anthropic"
        elif "google" in class_name or "gemini" in class_name:
            provider = "google"
        else:
            # Fallback: determine from model name
            model_lower = str(model_name).lower()
            if "gpt" in model_lower or "o1" in model_lower or "openai" in model_lower:
                provider = "openai"
            elif "claude" in model_lower or "anthropic" in model_lower:
                provider = "anthropic"
            elif "llama" in model_lower or "ollama" in model_lower:
                provider = "ollama"
            elif "gemini" in model_lower or "google" in model_lower:
                provider = "google"
    
    if model_name != "unknown":
        params = LLMParameters(temperature=temperature)
        return ModelConfig(
            model_name=str(model_name),
            provider=provider,
            parameters=params,
        )
    
    return None


def _extract_token_usage_from_result(result: Any) -> Optional[TokenUsage]:
    """Extract token usage from result (for LangChain responses)"""
    if result is None:
        return None
    
    # Try to extract from LangChain response
    if hasattr(result, "response_metadata"):
        metadata = getattr(result, "response_metadata", {})
        
        # Check for usage_metadata (LangChain standard)
        usage_metadata = metadata.get("usage_metadata")
        if usage_metadata:
            return TokenUsage(
                prompt_tokens=usage_metadata.get("input_tokens", 0),
                completion_tokens=usage_metadata.get("output_tokens", 0),
                total_tokens=usage_metadata.get("total_tokens", 0),
            )
        
        # Check for token_usage (OpenAI format)
        token_usage = metadata.get("token_usage")
        if token_usage:
            if isinstance(token_usage, dict):
                return TokenUsage(
                    prompt_tokens=token_usage.get("prompt_tokens", 0),
                    completion_tokens=token_usage.get("completion_tokens", 0),
                    total_tokens=token_usage.get("total_tokens", 0),
                )
        
        # Check for direct usage fields in metadata
        prompt_tokens = metadata.get("prompt_tokens") or metadata.get("input_tokens") or 0
        completion_tokens = metadata.get("completion_tokens") or metadata.get("output_tokens") or 0
        total_tokens = metadata.get("total_tokens") or (prompt_tokens + completion_tokens)
        
        if prompt_tokens > 0 or completion_tokens > 0:
            return TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
    
    # Try to extract from llm_output if available
    if hasattr(result, "llm_output") and result.llm_output:
        token_usage = result.llm_output.get("token_usage")
        if token_usage and isinstance(token_usage, dict):
            return TokenUsage(
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0),
            )
    
    return None


def _extract_model_config_from_result(result: Any) -> Optional[ModelConfig]:
    """Extract model config from result (for LangChain responses)"""
    if result is None:
        return None
    
    # Try to extract from LangChain response
    if hasattr(result, "response_metadata"):
        metadata = getattr(result, "response_metadata", {})
        model_name = metadata.get("model_name", "unknown")
        
        # Determine provider from model name
        provider = "unknown"
        model_lower = model_name.lower()
        if "gpt" in model_lower or "o1" in model_lower or "openai" in model_lower:
            provider = "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            provider = "anthropic"
        elif "llama" in model_lower or "ollama" in model_lower:
            provider = "ollama"
        elif "gemini" in model_lower or "google" in model_lower:
            provider = "google"
        
        params = LLMParameters(
            temperature=metadata.get("temperature", 0.0),
        )
        
        return ModelConfig(
            model_name=model_name,
            provider=provider,
            parameters=params,
        )
    
    return None


def _extract_prompt_from_args(kwargs: dict[str, Any]) -> ResolvedPrompt:
    """Extract prompt from function arguments"""
    if "question" in kwargs:
        question = kwargs["question"]
        return ResolvedPrompt(
            template="",
            variables={"question": question},
            final_text=str(question),
        )
    
    if "input" in kwargs:
        input_val = kwargs["input"]
        return ResolvedPrompt(
            template="",
            variables={"input": input_val},
            final_text=str(input_val),
        )
    
    return ResolvedPrompt(
        template="",
        variables={},
        final_text="",
    )


def _generate_and_export_artifact(
    context: TraceContext,
    duration_ms: int,
    export_path: Optional[str],
    artifacts_dir: Optional[str] = None,
    caller_file_path: Optional[str] = None,
) -> tuple[Any, Optional[str]]:
    """Generate artifact and export to storage
    
    Args:
        context: Trace context with execution data
        duration_ms: Execution duration in milliseconds
        export_path: Optional explicit path to save artifact
        artifacts_dir: Optional explicit artifacts directory (deprecated, use caller_file_path)
        caller_file_path: Path to the file calling the decorator (used to determine agent folder)
    """
    generator = ArtifactGenerator()

    # Use captured or default model config
    llm_config = context.llm_config or ModelConfig(
        model_name="unknown",
        provider="unknown",
        parameters=LLMParameters(temperature=0.7),
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
    run_id = f"local_{context.function_name}_{int(context.start_time.timestamp())}"
    artifact = generator.generate(
        run_id=run_id,
        tenant_id=context.tenant_id,
        inputs=context.inputs,
        outputs=context.outputs,
        llm_config=llm_config,
        resolved_prompt=prompt,
        tool_calls=context.tool_calls,
        duration_ms=duration_ms,
        error=context.error,
        token_usage=context.token_usage,
    )

    # Export to storage
    saved_path = None
    if export_path:
        artifact.save(Path(export_path))
        saved_path = export_path
    else:
        # Determine artifacts directory based on caller location
        if caller_file_path:
            # Get the directory of the file that called the decorator
            caller_dir = Path(caller_file_path).parent.resolve()
            # Create artifacts folder in the same directory as the caller
            agent_artifacts_dir = caller_dir / "artifacts"
            agent_artifacts_dir.mkdir(parents=True, exist_ok=True)
            artifacts_dir = str(agent_artifacts_dir)
        elif artifacts_dir:
            # Fallback to provided artifacts_dir
            Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
        else:
            # Default fallback (shouldn't happen, but just in case)
            artifacts_dir = "./artifacts"
            Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
        
        # Use ArtifactManager with config loading from agent directory
        agent_dir = Path(caller_file_path).parent.resolve() if caller_file_path else None
        manager = ArtifactManager(
            storage_path=Path(artifacts_dir),
            agent_dir=agent_dir
        )
        saved_path = str(manager.save(artifact))

    return artifact, saved_path


def trace_llm(
    semantic_bucket: Optional[str] = None,
    tenant_id: str = "default",
    environment: str = "production",
    auto_export: bool = True,
    export_path: Optional[str] = None,
    llm_config: Optional[ModelConfig] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to trace LLM function calls and generate .kurral artifacts
    
    Usage:
        @trace_llm(semantic_bucket="my_bucket", tenant_id="my_tenant")
        def run_agent(question: str):
            # Your agent code here
            return result
    
    Args:
        llm_config: Optional ModelConfig to use (if not provided, will try to extract from LLM objects)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Create trace context
            context = TraceContext(
                function_name=func.__name__,
                semantic_bucket=semantic_bucket,
                tenant_id=tenant_id,
                environment=environment,
            )

            # Capture inputs
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            context.inputs = _sanitize_for_serialization(dict(bound.arguments))

            # Try to extract LLM config from function's module globals
            # This allows capturing model info from LLM objects defined in the module
            if llm_config is None:
                try:
                    func_module = inspect.getmodule(func)
                    if func_module:
                        # Look for common LLM variable names in module globals
                        for var_name in ["llm", "json_llm", "chat_llm", "model"]:
                            if hasattr(func_module, var_name):
                                llm_obj = getattr(func_module, var_name)
                                # Skip if it's a function or None
                                if llm_obj is None or callable(llm_obj) and not hasattr(llm_obj, "model"):
                                    continue
                                extracted_config = _extract_model_config_from_llm_object(llm_obj)
                                if extracted_config and extracted_config.model_name != "unknown":
                                    context.llm_config = extracted_config
                                    break
                except Exception:
                    pass  # Silently fail if extraction fails
            
            # If still no config, use provided one
            if context.llm_config is None and llm_config:
                context.llm_config = llm_config

            # Start timing
            start_ms = time.time() * 1000

            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Extract outputs
                if isinstance(result, dict):
                    # If result is a dict (like final_state from graph), extract relevant info
                    context.outputs = _sanitize_for_serialization(result)
                    
                    # Extract tool calls from result if present
                    if "tool_calls" in result:
                        tool_calls_list = []
                        for tc in result.get("tool_calls", []):
                            if isinstance(tc, dict):
                                tool_call = ToolCall(
                                    tool_name=tc.get("tool_name", "unknown"),
                                    inputs=tc.get("inputs", {}),
                                    outputs=tc.get("outputs", {}),
                                    cache_key=ToolCall.generate_cache_key(
                                        tc.get("tool_name", "unknown"),
                                        tc.get("inputs", {})
                                    ),
                                    timestamp=datetime.fromisoformat(tc.get("timestamp", datetime.utcnow().isoformat())),
                                )
                                tool_calls_list.append(tool_call)
                        context.tool_calls = tool_calls_list
                    
                    # Try to extract LLM config from result if not already set
                    if context.llm_config is None or context.llm_config.model_name == "unknown":
                        context.llm_config = _extract_model_config_from_result(result)
                    
                    # Extract token usage from result
                    context.token_usage = _extract_token_usage_from_result(result)
                    
                    # Extract prompt from inputs or result
                    if "question" in result:
                        question_text = result.get("question", "")
                        context.prompt = ResolvedPrompt(
                            template="",
                            variables={"question": question_text},
                            final_text=str(question_text),
                        )
                    elif "question" in context.inputs:
                        context.prompt = ResolvedPrompt(
                            template="",
                            variables={"question": context.inputs["question"]},
                            final_text=str(context.inputs["question"]),
                        )
                    elif "user_input" in context.inputs:
                        # Fallback to user_input if question not found
                        user_input = context.inputs.get("user_input", "")
                        context.prompt = ResolvedPrompt(
                            template="",
                            variables={"user_input": user_input},
                            final_text=str(user_input),
                        )
                else:
                    context.outputs = {"result": _sanitize_for_serialization(result)}
                    # Try to extract LLM config from result if not already set
                    if context.llm_config is None or context.llm_config.model_name == "unknown":
                        context.llm_config = _extract_model_config_from_result(result)
                    # Extract token usage from result
                    context.token_usage = _extract_token_usage_from_result(result)
                    context.prompt = _extract_prompt_from_args(kwargs)

                # Stop timing
                duration_ms = int(time.time() * 1000 - start_ms)

                # Generate artifact
                if auto_export:
                    # Get the file path of the function being decorated
                    caller_file = inspect.getfile(func)
                    artifact, saved_path = _generate_and_export_artifact(
                        context, duration_ms, export_path, caller_file_path=caller_file
                    )
                    print(f"\n[SUCCESS] Kurral artifact saved to: {saved_path}")
                    print(f"  Kurral ID: {artifact.kurral_id}")
                    print(f"  Note: Replay level will be determined during replay (A or B)")

                return result

            except Exception as e:
                context.error = str(e)
                duration_ms = int(time.time() * 1000 - start_ms)

                # Still try to export even on error
                if auto_export:
                    # Get the file path of the function being decorated
                    caller_file = inspect.getfile(func)
                    artifact, saved_path = _generate_and_export_artifact(
                        context, duration_ms, export_path, caller_file_path=caller_file
                    )
                    print(f"\n[WARNING] Kurral artifact saved (with error): {saved_path}")

                raise

        return cast(Callable[..., T], wrapper)

    return decorator

