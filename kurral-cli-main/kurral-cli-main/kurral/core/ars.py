"""
Agent Regression Score (ARS) calculator
"""

import difflib
import json
from typing import Any

from kurral.models.kurral import KurralArtifact


class ARSCalculator:
    """
    Calculate Agent Regression Score

    ARS measures how much a new agent version differs from baseline
    """

    # Weights for different comparison factors
    WEIGHTS = {
        "output_similarity": 0.40,  # How similar are the outputs?
        "tool_match_rate": 0.30,  # Do tool calls match?
        "side_effect_divergence": 0.20,  # Are side effects different?
        "error_delta": 0.10,  # Error status changes?
    }

    def calculate(
        self,
        baseline: KurralArtifact,
        candidate: KurralArtifact,
    ) -> float:
        """
        Calculate ARS between baseline and candidate

        Args:
            baseline: Original/baseline artifact
            candidate: New/candidate artifact

        Returns:
            ARS score (0.0-1.0, higher is better)
            1.0 = perfect match
            0.0 = complete divergence
        """
        scores = {
            "output_similarity": self._output_similarity(baseline, candidate),
            "tool_match_rate": self._tool_match_rate(baseline, candidate),
            "side_effect_divergence": self._side_effect_divergence(baseline, candidate),
            "error_delta": self._error_delta(baseline, candidate),
        }

        # Calculate weighted average
        ars = sum(score * self.WEIGHTS[key] for key, score in scores.items())

        return ars

    def _output_similarity(
        self, baseline: KurralArtifact, candidate: KurralArtifact
    ) -> float:
        """
        Calculate output similarity using text similarity

        Returns score 0.0-1.0
        """
        baseline_text = json.dumps(baseline.outputs, sort_keys=True)
        candidate_text = json.dumps(candidate.outputs, sort_keys=True)

        if baseline_text == candidate_text:
            return 1.0

        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, baseline_text, candidate_text)
        return matcher.ratio()

    def _tool_match_rate(self, baseline: KurralArtifact, candidate: KurralArtifact) -> float:
        """
        Calculate tool call match rate

        Compares:
        - Number of tool calls
        - Tool names
        - Tool inputs
        - Tool outputs

        Returns score 0.0-1.0
        """
        if not baseline.tool_calls and not candidate.tool_calls:
            return 1.0

        if not baseline.tool_calls or not candidate.tool_calls:
            return 0.0

        # Compare tool call sequences
        baseline_calls = [
            (tc.tool_name, json.dumps(tc.inputs, sort_keys=True)) for tc in baseline.tool_calls
        ]
        candidate_calls = [
            (tc.tool_name, json.dumps(tc.inputs, sort_keys=True)) for tc in candidate.tool_calls
        ]

        if baseline_calls == candidate_calls:
            return 1.0

        # Calculate overlap
        baseline_set = set(baseline_calls)
        candidate_set = set(candidate_calls)

        if not baseline_set or not candidate_set:
            return 0.0

        intersection = len(baseline_set & candidate_set)
        union = len(baseline_set | candidate_set)

        return intersection / union if union > 0 else 0.0

    def _side_effect_divergence(
        self, baseline: KurralArtifact, candidate: KurralArtifact
    ) -> float:
        """
        Calculate side effect divergence

        Side effects include writes, updates, deletes, etc.

        Returns score 0.0-1.0 (higher = less divergence)
        """
        baseline_effects = self._extract_side_effects(baseline)
        candidate_effects = self._extract_side_effects(candidate)

        if baseline_effects == candidate_effects:
            return 1.0

        if not baseline_effects and not candidate_effects:
            return 1.0

        # Compare side effects
        if not baseline_effects or not candidate_effects:
            return 0.0

        # Convert to comparable format
        baseline_json = json.dumps(baseline_effects, sort_keys=True)
        candidate_json = json.dumps(candidate_effects, sort_keys=True)

        matcher = difflib.SequenceMatcher(None, baseline_json, candidate_json)
        return matcher.ratio()

    def _extract_side_effects(self, artifact: KurralArtifact) -> list[dict[str, Any]]:
        """
        Extract side-effect operations from tool calls

        Returns list of side effect operations
        """
        side_effects = []

        for tool_call in artifact.tool_calls:
            if self._is_side_effect_tool(tool_call.tool_name):
                side_effects.append(
                    {
                        "tool": tool_call.tool_name,
                        "inputs": tool_call.inputs,
                        "outputs": tool_call.outputs,
                    }
                )

        return side_effects

    @staticmethod
    def _is_side_effect_tool(tool_name: str) -> bool:
        """Check if tool has side effects"""
        side_effect_patterns = [
            "write",
            "delete",
            "update",
            "create",
            "send",
            "post",
            "put",
            "patch",
        ]

        tool_lower = tool_name.lower()
        return any(pattern in tool_lower for pattern in side_effect_patterns)

    def _error_delta(self, baseline: KurralArtifact, candidate: KurralArtifact) -> float:
        """
        Calculate error status delta

        Penalizes:
        - New errors
        - Different error messages

        Returns score 0.0-1.0
        """
        baseline_error = baseline.error
        candidate_error = candidate.error

        # Both successful
        if not baseline_error and not candidate_error:
            return 1.0

        # Both failed with same error
        if baseline_error == candidate_error:
            return 1.0

        # One failed, one succeeded
        if bool(baseline_error) != bool(candidate_error):
            return 0.0

        # Both failed with different errors
        if baseline_error and candidate_error:
            matcher = difflib.SequenceMatcher(None, baseline_error, candidate_error)
            return matcher.ratio() * 0.5  # Penalize different errors

        return 0.0

    def calculate_with_breakdown(
        self, baseline: KurralArtifact, candidate: KurralArtifact
    ) -> dict[str, Any]:
        """
        Calculate ARS with detailed breakdown

        Returns dict with overall score and component scores
        """
        scores = {
            "output_similarity": self._output_similarity(baseline, candidate),
            "tool_match_rate": self._tool_match_rate(baseline, candidate),
            "side_effect_divergence": self._side_effect_divergence(baseline, candidate),
            "error_delta": self._error_delta(baseline, candidate),
        }

        ars = sum(score * self.WEIGHTS[key] for key, score in scores.items())

        return {
            "ars_score": ars,
            "breakdown": scores,
            "weights": self.WEIGHTS,
            "passed": ars >= 0.90,  # Default threshold
        }


class BatchARSCalculator:
    """Calculate ARS across multiple artifact pairs"""

    def __init__(self):
        """Initialize batch calculator"""
        self.calculator = ARSCalculator()

    def calculate_batch(
        self,
        baseline_artifacts: list[KurralArtifact],
        candidate_artifacts: list[KurralArtifact],
    ) -> dict[str, Any]:
        """
        Calculate ARS for multiple artifact pairs

        Args:
            baseline_artifacts: List of baseline artifacts
            candidate_artifacts: List of candidate artifacts (must match length)

        Returns:
            Aggregate results with average ARS
        """
        if len(baseline_artifacts) != len(candidate_artifacts):
            raise ValueError("Baseline and candidate lists must have same length")

        results = []
        for baseline, candidate in zip(baseline_artifacts, candidate_artifacts):
            score = self.calculator.calculate(baseline, candidate)
            breakdown = self.calculator.calculate_with_breakdown(baseline, candidate)
            results.append(
                {
                    "baseline_id": str(baseline.kurral_id),
                    "candidate_id": str(candidate.kurral_id),
                    "ars_score": score,
                    "breakdown": breakdown,
                }
            )

        # Calculate aggregate
        avg_ars = sum(r["ars_score"] for r in results) / len(results) if results else 0.0

        # Count failures
        failures = [r for r in results if r["ars_score"] < 0.90]

        return {
            "total_pairs": len(results),
            "average_ars": avg_ars,
            "min_ars": min(r["ars_score"] for r in results) if results else 0.0,
            "max_ars": max(r["ars_score"] for r in results) if results else 0.0,
            "failures": len(failures),
            "passed": avg_ars >= 0.90,
            "results": results,
        }

