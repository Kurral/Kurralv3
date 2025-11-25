"""
A/B Testing engine for agent version comparison

This module enables developers to compare two versions of an agent (baseline vs candidate)
to validate changes before deployment. Uses ARS (Agent Regression Score) to quantify
behavioral differences.

Example use cases:
- Model migration (GPT-4 → GPT-4-turbo)
- Prompt changes
- Tool additions/removals
- Configuration changes
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from kurral.core.ars import ARSCalculator
from kurral.core.replay import ReplayEngine
from kurral.models.kurral import KurralArtifact, ReplayOverrides, ReplayResult


@dataclass
class VersionConfig:
    """Configuration for a specific agent version"""
    
    name: str  # Version identifier (e.g., "baseline", "candidate", "v1.2.0")
    model_name: Optional[str] = None
    prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ABTestResult:
    """Result of A/B test comparing two agent versions"""
    
    test_id: UUID
    timestamp: datetime
    version_a: VersionConfig
    version_b: VersionConfig
    
    # Test metrics
    test_suite_size: int
    replays_executed: int
    
    # ARS scores
    a_mean_ars: float
    b_mean_ars: float
    a_min_ars: float
    b_min_ars: float
    a_max_ars: float
    b_max_ars: float
    
    # Comparison
    b_improvement: float  # How much B improved over A (positive = better)
    recommendation: str  # "deploy", "reject", "needs_review"
    
    # Details
    per_artifact_scores: List[Dict[str, Any]]
    failures: List[Dict[str, Any]]
    summary: str
    
    # Statistics
    confidence_interval: Optional[Dict[str, float]] = None
    statistical_significance: Optional[bool] = None


class ABTestEngine:
    """
    Engine for running A/B tests between agent versions
    
    Usage:
        engine = ABTestEngine()
        
        # Define versions
        version_a = VersionConfig(name="gpt-4", model_name="gpt-4")
        version_b = VersionConfig(name="gpt-4-turbo", model_name="gpt-4-turbo")
        
        # Run test
        result = await engine.run_ab_test(
            test_suite=baseline_artifacts,
            version_a=version_a,
            version_b=version_b,
            threshold=0.90
        )
        
        # Decision
        if result.recommendation == "deploy":
            print("✅ Safe to deploy version B")
    """
    
    def __init__(self):
        """Initialize A/B test engine"""
        self.ars_calculator = ARSCalculator()
        self.replay_engine = ReplayEngine()
    
    async def run_ab_test(
        self,
        test_suite: List[KurralArtifact],
        version_a: VersionConfig,
        version_b: VersionConfig,
        threshold: float = 0.90,
        min_samples: int = 5,
        max_samples: Optional[int] = None,
        parallel_execution: bool = True,
    ) -> ABTestResult:
        """
        Run A/B test comparing two agent versions
        
        Args:
            test_suite: List of baseline artifacts to test against
            version_a: Baseline version configuration
            version_b: Candidate version configuration
            threshold: Minimum ARS score to pass (0.0-1.0)
            min_samples: Minimum test cases to run
            max_samples: Maximum test cases to run (None = all)
            parallel_execution: Whether to run replays in parallel
        
        Returns:
            ABTestResult with comparison metrics and recommendation
        """
        test_id = uuid4()
        timestamp = datetime.utcnow()
        
        # Select test suite
        selected_suite = self._select_test_suite(test_suite, min_samples, max_samples)
        
        # Run replays for both versions
        if parallel_execution:
            a_results, b_results = await asyncio.gather(
                self._run_version_replays(selected_suite, version_a),
                self._run_version_replays(selected_suite, version_b),
            )
        else:
            a_results = await self._run_version_replays(selected_suite, version_a)
            b_results = await self._run_version_replays(selected_suite, version_b)
        
        # Calculate ARS scores for each artifact
        per_artifact_scores = []
        a_ars_scores = []
        b_ars_scores = []
        failures = []
        
        for i, baseline in enumerate(selected_suite):
            # Version A comparison (baseline vs version A replay)
            a_artifact = self._result_to_artifact(a_results[i], baseline)
            a_ars = self.ars_calculator.calculate(baseline, a_artifact)
            a_ars_scores.append(a_ars)
            
            # Version B comparison (baseline vs version B replay)
            b_artifact = self._result_to_artifact(b_results[i], baseline)
            b_ars = self.ars_calculator.calculate(baseline, b_artifact)
            b_ars_scores.append(b_ars)
            
            # Record per-artifact results
            per_artifact_scores.append({
                "artifact_id": str(baseline.kurral_id),
                "semantic_bucket": baseline.semantic_buckets,
                "a_ars": a_ars,
                "b_ars": b_ars,
                "b_improvement": b_ars - a_ars,
            })
            
            # Track failures (B regressed compared to A)
            if b_ars < a_ars and b_ars < threshold:
                failures.append({
                    "artifact_id": str(baseline.kurral_id),
                    "a_ars": a_ars,
                    "b_ars": b_ars,
                    "regression": a_ars - b_ars,
                    "baseline_output": baseline.outputs.get("full_text", ""),
                    "version_b_output": b_artifact.outputs.get("full_text", ""),
                })
        
        # Calculate aggregate metrics
        a_mean_ars = sum(a_ars_scores) / len(a_ars_scores)
        b_mean_ars = sum(b_ars_scores) / len(b_ars_scores)
        b_improvement = b_mean_ars - a_mean_ars
        
        # Make recommendation
        recommendation = self._make_recommendation(
            b_mean_ars=b_mean_ars,
            b_improvement=b_improvement,
            failures=len(failures),
            threshold=threshold,
        )
        
        # Generate summary
        summary = self._generate_summary(
            version_a=version_a,
            version_b=version_b,
            a_mean_ars=a_mean_ars,
            b_mean_ars=b_mean_ars,
            b_improvement=b_improvement,
            failures=len(failures),
            recommendation=recommendation,
            threshold=threshold,
        )
        
        return ABTestResult(
            test_id=test_id,
            timestamp=timestamp,
            version_a=version_a,
            version_b=version_b,
            test_suite_size=len(test_suite),
            replays_executed=len(selected_suite) * 2,  # Both versions
            a_mean_ars=a_mean_ars,
            b_mean_ars=b_mean_ars,
            a_min_ars=min(a_ars_scores),
            b_min_ars=min(b_ars_scores),
            a_max_ars=max(a_ars_scores),
            b_max_ars=max(b_ars_scores),
            b_improvement=b_improvement,
            recommendation=recommendation,
            per_artifact_scores=per_artifact_scores,
            failures=failures,
            summary=summary,
        )
    
    async def _run_version_replays(
        self,
        artifacts: List[KurralArtifact],
        version: VersionConfig,
    ) -> List[ReplayResult]:
        """Run replays with specific version configuration"""
        overrides = self._version_to_overrides(version)
        
        results = []
        for artifact in artifacts:
            result = await self.replay_engine.replay(artifact, overrides)
            results.append(result)
        
        return results
    
    def _version_to_overrides(self, version: VersionConfig) -> Optional[ReplayOverrides]:
        """Convert version config to replay overrides"""
        return ReplayOverrides(
            model_name=version.model_name,
            prompt=version.prompt,
            temperature=version.temperature,
            max_tokens=version.max_tokens,
        )
    
    def _result_to_artifact(
        self,
        result: ReplayResult,
        baseline: KurralArtifact,
    ) -> KurralArtifact:
        """Convert ReplayResult back to artifact for ARS comparison"""
        # Create a new artifact with replayed outputs but same metadata
        return baseline.model_copy(update={"outputs": result.outputs})
    
    def _select_test_suite(
        self,
        artifacts: List[KurralArtifact],
        min_samples: int,
        max_samples: Optional[int],
    ) -> List[KurralArtifact]:
        """Select test suite based on sampling strategy"""
        if max_samples is None:
            return artifacts
        
        selected_count = max(min_samples, min(max_samples, len(artifacts)))
        return artifacts[:selected_count]
    
    def _make_recommendation(
        self,
        b_mean_ars: float,
        b_improvement: float,
        failures: int,
        threshold: float,
    ) -> str:
        """
        Make deployment recommendation based on results
        
        Logic:
        - deploy: B meets threshold AND shows improvement with no regressions
        - reject: B fails threshold OR shows significant regressions
        - needs_review: Mixed results, manual review required
        """
        if b_mean_ars >= threshold and b_improvement >= 0 and failures == 0:
            return "deploy"
        elif b_mean_ars < threshold or b_improvement < -0.05:
            return "reject"
        else:
            return "needs_review"
    
    def _generate_summary(
        self,
        version_a: VersionConfig,
        version_b: VersionConfig,
        a_mean_ars: float,
        b_mean_ars: float,
        b_improvement: float,
        failures: int,
        recommendation: str,
        threshold: float,
    ) -> str:
        """Generate human-readable summary"""
        
        status_emoji = {
            "deploy": "✅",
            "reject": "❌",
            "needs_review": "⚠️",
        }
        
        improvement_pct = b_improvement * 100
        improvement_direction = "improvement" if b_improvement >= 0 else "regression"
        
        summary = f"""
A/B Test Results: {status_emoji.get(recommendation, '❓')} {recommendation.upper()}

Version A (Baseline): {version_a.name}
  Model: {version_a.model_name or 'N/A'}
  Mean ARS: {a_mean_ars:.4f}

Version B (Candidate): {version_b.name}
  Model: {version_b.model_name or 'N/A'}
  Mean ARS: {b_mean_ars:.4f}

Comparison:
  Improvement: {improvement_pct:+.2f}% ({improvement_direction})
  Threshold: {threshold:.4f}
  Regressions: {failures}

Recommendation: {recommendation.upper()}
        """.strip()
        
        if recommendation == "deploy":
            summary += "\n\n✅ Safe to deploy Version B - no regressions detected"
        elif recommendation == "reject":
            summary += f"\n\n❌ Do not deploy Version B - {failures} regression(s) detected"
        else:
            summary += "\n\n⚠️  Manual review required - mixed results"
        
        return summary


class ComparativeABTest:
    """
    Helper for common A/B test scenarios
    
    Provides convenient methods for typical comparisons:
    - Model migration
    - Prompt optimization
    - Temperature tuning
    """
    
    def __init__(self):
        self.engine = ABTestEngine()
    
    async def test_model_migration(
        self,
        baseline_artifacts: List[KurralArtifact],
        from_model: str,
        to_model: str,
        threshold: float = 0.90,
    ) -> ABTestResult:
        """
        Test migration from one model to another
        
        Example:
            result = await test_model_migration(
                baseline_artifacts=prod_traces,
                from_model="gpt-4",
                to_model="gpt-4-turbo",
                threshold=0.90
            )
        """
        version_a = VersionConfig(name=f"baseline-{from_model}", model_name=from_model)
        version_b = VersionConfig(name=f"candidate-{to_model}", model_name=to_model)
        
        return await self.engine.run_ab_test(
            test_suite=baseline_artifacts,
            version_a=version_a,
            version_b=version_b,
            threshold=threshold,
        )
    
    async def test_prompt_change(
        self,
        baseline_artifacts: List[KurralArtifact],
        current_prompt: str,
        new_prompt: str,
        threshold: float = 0.90,
    ) -> ABTestResult:
        """Test impact of prompt changes"""
        version_a = VersionConfig(name="current-prompt", prompt=current_prompt)
        version_b = VersionConfig(name="new-prompt", prompt=new_prompt)
        
        return await self.engine.run_ab_test(
            test_suite=baseline_artifacts,
            version_a=version_a,
            version_b=version_b,
            threshold=threshold,
        )
    
    async def test_temperature_tuning(
        self,
        baseline_artifacts: List[KurralArtifact],
        current_temp: float,
        new_temp: float,
        threshold: float = 0.90,
    ) -> ABTestResult:
        """Test impact of temperature changes"""
        version_a = VersionConfig(name=f"temp-{current_temp}", temperature=current_temp)
        version_b = VersionConfig(name=f"temp-{new_temp}", temperature=new_temp)
        
        return await self.engine.run_ab_test(
            test_suite=baseline_artifacts,
            version_a=version_a,
            version_b=version_b,
            threshold=threshold,
        )

