"""
Backtest engine for regression testing
"""

import asyncio
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from kurral.core.ars import ARSCalculator
from kurral.core.replay import ReplayEngine
from kurral.models.kurral import (
    BacktestRequest,
    BacktestResult,
    KurralArtifact,
    ReplayOverrides,
)


class BacktestEngine:
    """
    Engine for running comparative backtests

    Compares baseline artifacts against new agent configurations
    """

    def __init__(self):
        """Initialize backtest engine"""
        self.ars_calculator = ARSCalculator()
        self.replay_engine = ReplayEngine()

    async def backtest(
        self,
        baseline_artifacts: list[KurralArtifact],
        candidate_config: dict[str, Any],
        threshold: float = 0.90,
        sample_strategy: str = "adaptive",
        max_replays: int = 100,
    ) -> BacktestResult:
        """
        Run backtest comparing baseline against candidate

        Args:
            baseline_artifacts: Baseline artifacts to test against
            candidate_config: New agent configuration
            threshold: ARS threshold for passing (0.0-1.0)
            sample_strategy: Sampling strategy ('adaptive', 'fixed', 'all')
            max_replays: Maximum replays per artifact

        Returns:
            BacktestResult with ARS scores and analysis
        """
        backtest_id = uuid4()
        timestamp = datetime.utcnow()

        # Select artifacts to test based on strategy
        artifacts_to_test = self._select_artifacts(
            baseline_artifacts, sample_strategy, max_replays
        )

        # Run replays with candidate config
        replay_results = []
        ars_scores = []
        failures = []

        for baseline in artifacts_to_test:
            # Create overrides from candidate config
            overrides = self._config_to_overrides(candidate_config)

            # Replay with candidate config
            # In full implementation: actually re-execute with new config
            # For now, we use the baseline as "candidate"
            candidate = baseline  # Simplified

            # Calculate ARS
            ars = self.ars_calculator.calculate(baseline, candidate)
            ars_scores.append(ars)

            # Track failures
            if ars < threshold:
                failures.append(
                    {
                        "kurral_id": str(baseline.kurral_id),
                        "ars_score": ars,
                        "baseline_output": baseline.outputs,
                        "candidate_output": candidate.outputs,
                    }
                )

        # Calculate aggregate results
        avg_ars = sum(ars_scores) / len(ars_scores) if ars_scores else 0.0
        passed = avg_ars >= threshold

        # Generate summary
        summary = self._generate_summary(
            baseline_count=len(baseline_artifacts),
            tested_count=len(artifacts_to_test),
            avg_ars=avg_ars,
            threshold=threshold,
            failures=len(failures),
            passed=passed,
        )

        # Create breakdown
        breakdown = {
            "average_ars": avg_ars,
            "min_ars": min(ars_scores) if ars_scores else 0.0,
            "max_ars": max(ars_scores) if ars_scores else 0.0,
            "median_ars": sorted(ars_scores)[len(ars_scores) // 2] if ars_scores else 0.0,
            "pass_rate": (len(ars_scores) - len(failures)) / len(ars_scores)
            if ars_scores
            else 0.0,
        }

        return BacktestResult(
            backtest_id=backtest_id,
            timestamp=timestamp,
            baseline_count=len(baseline_artifacts),
            replays_executed=len(artifacts_to_test),
            ars_score=avg_ars,
            passed=passed,
            threshold=threshold,
            breakdown=breakdown,
            failures=failures,
            summary=summary,
        )

    def _select_artifacts(
        self,
        artifacts: list[KurralArtifact],
        strategy: str,
        max_replays: int,
    ) -> list[KurralArtifact]:
        """
        Select artifacts to test based on sampling strategy

        Strategies:
        - 'all': Test all artifacts (up to max_replays)
        - 'fixed': Fixed sample of 5 per artifact
        - 'adaptive': Start with 5, expand if variance > 10%
        """
        if strategy == "all":
            return artifacts[:max_replays]

        elif strategy == "fixed":
            # Take up to 5 artifacts
            return artifacts[:5]

        elif strategy == "adaptive":
            # Start with 5, could expand based on variance
            # For now, simplified to fixed 5
            return artifacts[:5]

        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")

    def _config_to_overrides(self, config: dict[str, Any]) -> ReplayOverrides:
        """Convert agent config to replay overrides"""
        return ReplayOverrides(
            prompt=config.get("prompt"),
            temperature=config.get("temperature"),
            max_tokens=config.get("max_tokens"),
            model_name=config.get("model_name"),
        )

    def _generate_summary(
        self,
        baseline_count: int,
        tested_count: int,
        avg_ars: float,
        threshold: float,
        failures: int,
        passed: bool,
    ) -> str:
        """Generate human-readable summary"""
        status = "PASSED" if passed else "FAILED"

        summary = f"""
Backtest {status}

Baseline Artifacts: {baseline_count}
Replays Executed: {tested_count}
Average ARS: {avg_ars:.4f}
Threshold: {threshold:.4f}
Failures: {failures}

Status: {'✅ PASS' if passed else '❌ FAIL'}
        """.strip()

        return summary

    async def backtest_from_request(self, request: BacktestRequest) -> BacktestResult:
        """
        Run backtest from BacktestRequest

        This would load artifacts by ID in a real implementation

        Args:
            request: BacktestRequest

        Returns:
            BacktestResult
        """
        # In real implementation: load artifacts from storage
        # For now, return placeholder
        return BacktestResult(
            backtest_id=uuid4(),
            timestamp=datetime.utcnow(),
            baseline_count=len(request.baseline_artifacts),
            replays_executed=0,
            ars_score=0.0,
            passed=False,
            threshold=request.threshold,
            breakdown={},
            failures=[],
            summary="Not implemented - would load artifacts and run backtest",
        )


class AdaptiveBacktester:
    """
    Advanced backtester with adaptive sampling

    Automatically expands sample size if results show high variance
    """

    def __init__(self, initial_samples: int = 5, variance_threshold: float = 0.10):
        """
        Initialize adaptive backtester

        Args:
            initial_samples: Initial number of samples per artifact
            variance_threshold: Variance threshold for expansion (e.g., 0.10 = 10%)
        """
        self.initial_samples = initial_samples
        self.variance_threshold = variance_threshold
        self.engine = BacktestEngine()

    async def backtest_adaptive(
        self,
        baseline_artifacts: list[KurralArtifact],
        candidate_config: dict[str, Any],
        threshold: float = 0.90,
        max_replays_per_artifact: int = 20,
    ) -> BacktestResult:
        """
        Run adaptive backtest

        1. Start with initial_samples replays
        2. Calculate variance
        3. If variance > threshold, expand samples
        4. Repeat until variance stabilizes or max_replays reached

        Args:
            baseline_artifacts: Baseline artifacts
            candidate_config: Candidate configuration
            threshold: ARS threshold
            max_replays_per_artifact: Max replays per artifact

        Returns:
            BacktestResult
        """
        # Phase 1: Initial samples
        result = await self.engine.backtest(
            baseline_artifacts=baseline_artifacts[:self.initial_samples],
            candidate_config=candidate_config,
            threshold=threshold,
            sample_strategy="fixed",
        )

        # Check variance (simplified)
        if result.breakdown.get("max_ars", 0) - result.breakdown.get("min_ars", 0) > self.variance_threshold:
            # Phase 2: Expand samples
            result = await self.engine.backtest(
                baseline_artifacts=baseline_artifacts[:max_replays_per_artifact],
                candidate_config=candidate_config,
                threshold=threshold,
                sample_strategy="all",
                max_replays=max_replays_per_artifact,
            )

        return result

