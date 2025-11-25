"""
Determinism scoring engine
"""

from typing import Any

from kurral.models.kurral import (
    DeterminismReport,
    KurralArtifact,
    ModelConfig,
    ReplayLevel,
    ResolvedPrompt,
    ToolCall,
)


class DeterminismScorer:
    """
    Calculate determinism score based on various factors
    """

    # Weights for different factors (must sum to 1.0)
    WEIGHTS = {
        "model_version": 0.25,  # Has specific model version
        "random_seed": 0.20,  # Has random seed set
        "prompt": 0.20,  # Prompt is fully resolved
        "tool_cache": 0.15,  # Tool calls can be cached
        "environment": 0.10,  # Environment is captured
        "parameters": 0.10,  # Temperature and other params are deterministic
    }

    def __init__(self):
        """Initialize scorer with default weights"""
        # Validate weights sum to 1.0
        total = sum(self.WEIGHTS.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def score_model_version(self, config: ModelConfig) -> float:
        """Score based on model version specificity"""
        if config.model_version:
            return 1.0
        if config.model_name and "-" in config.model_name:
            # e.g., "gpt-4-0613" has version embedded
            return 0.8
        if config.model_name:
            # Generic name like "gpt-4" is less deterministic
            return 0.3
        return 0.0

    def score_random_seed(self, config: ModelConfig) -> float:
        """Score based on random seed presence"""
        if config.parameters.seed is not None:
            return 1.0
        return 0.0

    def score_prompt(self, prompt: ResolvedPrompt) -> float:
        """Score based on prompt completeness"""
        score = 0.0

        # Has template
        if prompt.template:
            score += 0.3

        # All variables resolved
        if prompt.variables and prompt.final_text:
            score += 0.4

        # Has final text
        if prompt.final_text:
            score += 0.3

        return min(score, 1.0)

    def score_tool_cache(self, tool_calls: list[ToolCall]) -> float:
        """Score based on tool call cacheability"""
        if not tool_calls:
            return 1.0  # No tools = fully deterministic

        cacheable = sum(1 for tc in tool_calls if tc.cache_key and not tc.error)
        return cacheable / len(tool_calls) if tool_calls else 1.0

    def score_environment(self, artifact: "KurralArtifact") -> float:
        """Score based on environment capture"""
        score = 0.0

        # Handle case where artifact is None (during artifact generation)
        if artifact is None:
            return 0.5  # Default neutral score
        
        if artifact.time_env:
            score += 0.5

        if artifact.environment:
            score += 0.3

        if artifact.time_env and artifact.time_env.environment_vars:
            score += 0.2

        return min(score, 1.0)

    def score_parameters(self, config: ModelConfig) -> float:
        """Score based on deterministic parameters"""
        score = 0.0

        # Temperature = 0 is most deterministic
        if config.parameters.temperature == 0.0:
            score += 0.5
        elif config.parameters.temperature < 0.3:
            score += 0.3
        elif config.parameters.temperature < 0.7:
            score += 0.1

        # top_p = 1 or None is deterministic
        if config.parameters.top_p is None or config.parameters.top_p == 1.0:
            score += 0.3
        elif config.parameters.top_p > 0.9:
            score += 0.2

        # Presence/frequency penalties at 0 is deterministic
        if config.parameters.presence_penalty == 0.0 or config.parameters.presence_penalty is None:
            score += 0.1
        if config.parameters.frequency_penalty == 0.0 or config.parameters.frequency_penalty is None:
            score += 0.1

        return min(score, 1.0)

    def score(
        self,
        llm_config: ModelConfig,
        prompt: ResolvedPrompt,
        tool_calls: list[ToolCall],
        artifact: "KurralArtifact",
    ) -> DeterminismReport:
        """
        Calculate overall determinism score

        Returns DeterminismReport with:
        - overall_score: weighted average (0.0-1.0)
        - breakdown: individual scores
        - missing_fields: what's missing
        - warnings: potential issues
        """
        breakdown = {
            "model_version": self.score_model_version(llm_config),
            "random_seed": self.score_random_seed(llm_config),
            "prompt": self.score_prompt(prompt),
            "tool_cache": self.score_tool_cache(tool_calls),
            "environment": self.score_environment(artifact),
            "parameters": self.score_parameters(llm_config),
        }

        # Calculate weighted average
        overall = sum(score * self.WEIGHTS[key] for key, score in breakdown.items())

        # Identify issues
        missing_fields = []
        warnings = []

        if breakdown["model_version"] < 0.8:
            missing_fields.append("model_version")

        if breakdown["random_seed"] == 0.0:
            missing_fields.append("random_seed")
            warnings.append("No random seed set - outputs may vary")

        if breakdown["parameters"] < 0.5:
            warnings.append("Temperature > 0 reduces determinism")

        if breakdown["tool_cache"] < 1.0:
            failed_tools = sum(1 for tc in tool_calls if tc.error)
            if failed_tools > 0:
                warnings.append(f"{failed_tools} tool calls failed")

        if breakdown["environment"] < 0.5:
            warnings.append("Environment not fully captured")

        return DeterminismReport(
            overall_score=overall,
            breakdown=breakdown,
            missing_fields=missing_fields,
            warnings=warnings,
        )

    @staticmethod
    def assign_replay_level(score: float) -> ReplayLevel:
        """
        Assign replay level based on determinism score
        
        ⚠️  IMPORTANT: Replay levels are METADATA ONLY, not decision points.
        
        The ABC classification indicates expected reproducibility confidence,
        but Kurral's replay engine stubs all tool calls and uses cached outputs
        regardless of level. Do NOT use replay_level to gate replay execution.
        
        Replay Level Definitions (for metadata/analytics only):
        
        A (score >= 0.90): High reproducibility confidence
           - Frozen model (exact version + seed)
           - Deterministic parameters (temperature=0, seed set)
           - Complete environment capture
           - Note: With Kurral's direct capture, most traces will be Level A
        
        B (0.50 <= score < 0.90): Medium reproducibility confidence
           - Partial determinism (some parameters missing)
           - Model version may vary
           - Tool I/O is cached (stubs available)
        
        C (score < 0.50): Low reproducibility confidence
           - High temperature, no seed
           - Incomplete environment capture
           - Tool I/O still cached (stubs available)
        
        Use cases for ABC metadata:
        - Optional filter flag in A/B tests (e.g., only test Level A artifacts)
        - Analytics and reporting
        - Quality metrics for captured traces
        
        For version comparison and A/B testing, use the ab_test module instead.
        """
        if score >= 0.90:
            return ReplayLevel.A
        elif score >= 0.50:
            return ReplayLevel.B
        else:
            return ReplayLevel.C

