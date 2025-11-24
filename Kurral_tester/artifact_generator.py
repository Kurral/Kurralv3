"""
Artifact generator for Kurral
"""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from Kurral_tester.models.kurral import (
    KurralArtifact,
    ModelConfig,
    LLMParameters,
    ResolvedPrompt,
    TimeEnvironment,
    TokenUsage,
    ToolCall,
    DeterminismReport,
)


class ArtifactGenerator:
    """Generate .kurral artifacts from agent runs
    
    During initial run, just stores the run data without calculating
    determinism scores or assigning replay levels. Those are determined
    during replay based on parameter comparison.
    """
    
    def generate(
        self,
        run_id: str,
        tenant_id: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        llm_config: ModelConfig,
        resolved_prompt: ResolvedPrompt,
        tool_calls: Optional[list[ToolCall]] = None,
        duration_ms: int = 0,
        error: Optional[str] = None,
        token_usage: Optional[TokenUsage] = None,
    ) -> KurralArtifact:
        """Generate a .kurral artifact"""
        kurral_id = uuid4()
        now = datetime.utcnow()
        
        time_env = TimeEnvironment(
            timestamp=now,
            timezone="UTC",
            wall_clock_time=now.isoformat(),
            environment_vars={},
        )
        
        tool_calls_list = tool_calls or []
        
        # During initial run, we don't calculate determinism score or assign replay_level
        # Those are determined during replay based on parameter comparison
        # Create empty determinism report (will be calculated during replay)
        determinism_report = DeterminismReport(
            overall_score=0.0,
            breakdown={},
            missing_fields=[],
            warnings=[],
        )
        
        artifact = KurralArtifact(
            kurral_id=kurral_id,
            run_id=run_id,
            tenant_id=tenant_id,
            semantic_buckets=[],
            environment="production",
            schema_version="1.0.0",
            created_at=now,
            created_by=None,
            deterministic=False,  # Will be determined during replay
            replay_level=None,  # Will be determined during replay (A or B)
            determinism_report=determinism_report,
            inputs=inputs,
            outputs=outputs,
            error=error,
            llm_config=llm_config,
            resolved_prompt=resolved_prompt,
            graph_version=None,
            tool_calls=tool_calls_list,
            time_env=time_env,
            duration_ms=duration_ms,
            cost_usd=None,
            token_usage=token_usage or TokenUsage(),
            tags={},
        )
        
        return artifact

