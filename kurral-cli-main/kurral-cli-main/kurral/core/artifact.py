"""
Artifact generation from traces
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from kurral.core.determinism import DeterminismScorer
from kurral.models.kurral import (
    KurralArtifact,
    ModelConfig,
    ReplayLevel,
    ResolvedPrompt,
    TimeEnvironment,
    TokenUsage,
    ToolCall,
)


class ArtifactGenerator:
    """
    Generate .kurral artifacts from trace data
    """

    def __init__(self):
        """Initialize with determinism scorer"""
        self.scorer = DeterminismScorer()

    def generate(
        self,
        run_id: str,
        tenant_id: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        llm_config: ModelConfig,
        resolved_prompt: ResolvedPrompt,
        tool_calls: Optional[list[ToolCall]] = None,
        semantic_buckets: Optional[list[str]] = None,
        environment: str = "production",
        duration_ms: int = 0,
        cost_usd: Optional[float] = None,
        token_usage: Optional["TokenUsage"] = None,
        graph_version: Optional["GraphVersion"] = None,
        error: Optional[str] = None,
        tags: Optional[dict[str, str]] = None,
        created_by: Optional[str] = None,
        **kwargs,
    ) -> KurralArtifact:
        """
        Generate a .kurral artifact from trace data

        Args:
            run_id: Source trace/run ID
            tenant_id: Tenant/organization ID
            inputs: Function inputs
            outputs: Function outputs
            llm_config: LLM model configuration
            resolved_prompt: Prompt with variables
            tool_calls: List of tool invocations
            semantic_buckets: Business logic categories
            environment: Environment name (prod/staging/dev)
            duration_ms: Execution time in milliseconds
            cost_usd: Estimated cost
            token_usage: Token usage stats
            error: Error message if failed
            tags: Custom tags
            created_by: User/service identifier
            **kwargs: Additional metadata

        Returns:
            KurralArtifact ready to be saved
        """
        # Generate unique ID
        kurral_id = uuid4()

        # Capture time environment
        now = datetime.utcnow()
        time_env = TimeEnvironment(
            timestamp=now,
            timezone="UTC",
            wall_clock_time=now.isoformat(),
            environment_vars=kwargs.get("environment_vars", {}),
        )

        # Calculate determinism score
        tool_calls_list = tool_calls or []
        determinism_report = self.scorer.score(
            llm_config=llm_config,
            prompt=resolved_prompt,
            tool_calls=tool_calls_list,
            artifact=None,  # Will be set in validator
        )

        # Assign replay level
        replay_level = self.scorer.assign_replay_level(determinism_report.overall_score)

        # Set deterministic flag
        deterministic = determinism_report.overall_score >= 0.90

        # Create artifact
        artifact = KurralArtifact(
            kurral_id=kurral_id,
            run_id=run_id,
            tenant_id=tenant_id,
            semantic_buckets=semantic_buckets or [],
            environment=environment,
            schema_version="1.0.0",
            created_at=now,
            created_by=created_by,
            deterministic=deterministic,
            replay_level=replay_level,
            determinism_report=determinism_report,
            inputs=inputs,
            outputs=outputs,
            error=error,
            llm_config=llm_config,
            resolved_prompt=resolved_prompt,
            graph_version=graph_version,
            tool_calls=tool_calls_list,
            time_env=time_env,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            token_usage=token_usage or TokenUsage(),
            tags=tags or {},
        )

        return artifact

    def from_langsmith_run(self, run: dict[str, Any], tenant_id: str) -> KurralArtifact:
        """
        Convert LangSmith run to KurralArtifact

        Args:
            run: LangSmith run data
            tenant_id: Tenant ID to assign

        Returns:
            KurralArtifact
        """
        # Extract model config
        llm_config = self._extract_model_config(run)

        # Extract prompt
        resolved_prompt = self._extract_prompt(run)

        # Extract tool calls
        tool_calls = self._extract_tool_calls(run)

        # Calculate duration
        duration_ms = 0
        if run.get("end_time") and run.get("start_time"):
            start = datetime.fromisoformat(run["start_time"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(run["end_time"].replace("Z", "+00:00"))
            duration_ms = int((end - start).total_seconds() * 1000)

        # Extract token usage from LangSmith run
        from kurral.models.kurral import TokenUsage
        
        prompt_tokens = run.get("prompt_tokens", 0) or 0
        completion_tokens = run.get("completion_tokens", 0) or 0
        total_tokens = run.get("total_tokens", 0) or prompt_tokens + completion_tokens
        
        # Extract caching metrics if available
        usage_metadata = run.get("extra", {}).get("usage_metadata", {})
        cached_tokens = usage_metadata.get("cached_tokens") or usage_metadata.get("cache_read_input_tokens")
        cache_creation_tokens = usage_metadata.get("cache_creation_input_tokens")
        
        # Calculate cache hit rate if we have cached tokens
        cache_hit_rate = None
        if cached_tokens and prompt_tokens:
            cache_hit_rate = cached_tokens / prompt_tokens
        
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cached_tokens,  # Alias
            cache_hit_rate=cache_hit_rate,
            reasoning_tokens=usage_metadata.get("reasoning_tokens"),
            audio_tokens=usage_metadata.get("audio_tokens"),
        )

        # Extract semantic buckets from tags
        semantic_buckets = [tag for tag in run.get("tags", []) if tag.startswith("bucket:")]
        semantic_buckets = [b.replace("bucket:", "") for b in semantic_buckets]

        return self.generate(
            run_id=run.get("id", str(uuid4())),
            tenant_id=tenant_id,
            inputs=run.get("inputs", {}),
            outputs=run.get("outputs", {}),
            llm_config=llm_config,
            resolved_prompt=resolved_prompt,
            tool_calls=tool_calls,
            semantic_buckets=semantic_buckets,
            environment=run.get("extra", {}).get("environment", "production"),
            duration_ms=duration_ms,
            token_usage=token_usage,
            error=run.get("error"),
        )

    def _extract_model_config(self, run: dict[str, Any]) -> ModelConfig:
        """Extract model config from LangSmith run"""
        serialized = run.get("serialized", {})
        kwargs = serialized.get("kwargs", {})
        extra = run.get("extra", {})
        invocation_params = extra.get("invocation_params", {})

        # Extract metadata (LangSmith stores lots of useful info here)
        metadata = extra.get("metadata", {})
        
        # Try multiple places to find model_name
        model_name = (
            metadata.get("ls_model_name")  # LangSmith metadata (most reliable)
            or run.get("model_name") 
            or kwargs.get("model_name")
            or kwargs.get("model")
            or invocation_params.get("model")
            or invocation_params.get("model_name")
            or run.get("name")  # Sometimes the run name IS the model name
            or "unknown"
        )
        
        # Extract provider from multiple sources
        provider = (
            metadata.get("ls_provider")  # LangSmith metadata (most reliable)
            or run.get("provider")
            or kwargs.get("provider")
            or "unknown"
        )
        
        # Fallback: try to extract from serialized ID
        if provider == "unknown" and serialized.get("id"):
            provider_list = serialized.get("id", [])
            if isinstance(provider_list, list) and len(provider_list) > 0:
                provider = provider_list[0]
            elif isinstance(provider_list, str):
                provider = provider_list

        from kurral.models.kurral import LLMParameters
        
        # Extract model_version, but exclude if same as model_name
        model_version = (
            metadata.get("ls_model_name")
            or invocation_params.get("model") 
            or kwargs.get("model")
        )
        if model_version == model_name:
            model_version = None
        
        # Build LLM parameters dict, only including non-None values
        llm_params = {
            "temperature": (
                metadata.get("ls_temperature")
                or kwargs.get("temperature") 
                or invocation_params.get("temperature") 
                or 0.7
            )
        }
        
        # Only add optional params if they have actual values
        if kwargs.get("seed") or invocation_params.get("seed"):
            llm_params["seed"] = kwargs.get("seed") or invocation_params.get("seed")
        
        if metadata.get("ls_max_tokens") or kwargs.get("max_tokens") or invocation_params.get("max_tokens"):
            llm_params["max_tokens"] = (
                metadata.get("ls_max_tokens")
                or kwargs.get("max_tokens") 
                or invocation_params.get("max_tokens")
            )
        
        if kwargs.get("top_p") or invocation_params.get("top_p"):
            llm_params["top_p"] = kwargs.get("top_p") or invocation_params.get("top_p")
        
        if kwargs.get("top_k") or invocation_params.get("top_k"):
            llm_params["top_k"] = kwargs.get("top_k") or invocation_params.get("top_k")
        
        if kwargs.get("frequency_penalty") or invocation_params.get("frequency_penalty"):
            llm_params["frequency_penalty"] = kwargs.get("frequency_penalty") or invocation_params.get("frequency_penalty")
        
        if kwargs.get("presence_penalty") or invocation_params.get("presence_penalty"):
            llm_params["presence_penalty"] = kwargs.get("presence_penalty") or invocation_params.get("presence_penalty")
        
        # Build ModelConfig dict, only including non-None values
        model_config_dict = {
            "model_name": model_name,
            "provider": provider,
            "parameters": LLMParameters(**llm_params),
        }
        
        if model_version:
            model_config_dict["model_version"] = model_version
        
        stop_seqs = kwargs.get("stop") or invocation_params.get("stop")
        if stop_seqs:
            model_config_dict["stop_sequences"] = stop_seqs
        
        return ModelConfig(**model_config_dict)

    def _extract_prompt(self, run: dict[str, Any]) -> ResolvedPrompt:
        """Extract prompt from LangSmith run"""
        inputs = run.get("inputs", {})

        # Try to get messages
        messages = inputs.get("messages", [])
        if messages:
            # Chat format
            final_text = "\n".join(
                f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages
            )
            return ResolvedPrompt(
                template="",
                variables={},
                final_text=final_text,
                messages=messages,
            )

        # Try simple prompt
        prompt_text = inputs.get("prompt", "") or inputs.get("input", "")

        return ResolvedPrompt(
            template=prompt_text,
            variables=inputs,
            final_text=prompt_text,
        )

    def _extract_tool_calls(self, run: dict[str, Any]) -> list[ToolCall]:
        """Extract tool calls from LangSmith run"""
        tool_calls = []

        # Get child runs that are tool calls
        for child in run.get("child_runs", []):
            if child.get("run_type") == "tool":
                tool_call = ToolCall(
                    tool_name=child.get("name", "unknown"),
                    inputs=child.get("inputs", {}),
                    outputs=child.get("outputs", {}),
                    cache_key=ToolCall.generate_cache_key(
                        child.get("name", "unknown"), child.get("inputs", {})
                    ),
                    timestamp=datetime.fromisoformat(
                        child.get("start_time", datetime.utcnow().isoformat()).replace(
                            "Z", "+00:00"
                        )
                    ),
                    duration_ms=(
                        int(
                            (
                                datetime.fromisoformat(
                                    child.get("end_time", "").replace("Z", "+00:00")
                                )
                                - datetime.fromisoformat(
                                    child.get("start_time", "").replace("Z", "+00:00")
                                )
                            ).total_seconds()
                            * 1000
                        )
                        if child.get("end_time")
                        else None
                    ),
                    error=child.get("error"),
                )
                tool_calls.append(tool_call)

        return tool_calls

