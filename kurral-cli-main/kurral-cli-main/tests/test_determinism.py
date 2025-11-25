"""
Tests for determinism scoring
"""

import pytest

from kurral.core.artifact import ArtifactGenerator
from kurral.core.determinism import DeterminismScorer
from kurral.models.kurral import ModelConfig, ReplayLevel, ResolvedPrompt, LLMParameters


def test_determinism_scorer():
    """Test basic determinism scoring"""
    scorer = DeterminismScorer()

    # Highly deterministic config
    model_config = ModelConfig(
        model_name="gpt-4-0613",
        model_version="0613",
        provider="openai",
        parameters=LLMParameters(
            temperature=0.0,
            seed=12345,
        ),
    )

    prompt = ResolvedPrompt(
        template="You are a helpful assistant",
        variables={},
        final_text="You are a helpful assistant",
    )

    # Create a minimal artifact for testing
    generator = ArtifactGenerator()
    artifact = generator.generate(
        run_id="test",
        tenant_id="test",
        inputs={},
        outputs={},
        llm_config=model_config,
        resolved_prompt=prompt,
        duration_ms=100,
    )

    report = scorer.score(llm_config=model_config, prompt=prompt, tool_calls=[], artifact=artifact)

    assert 0.0 <= report.overall_score <= 1.0
    assert report.breakdown
    assert "model_version" in report.breakdown
    assert "random_seed" in report.breakdown


def test_replay_level_assignment():
    """Test replay level assignment based on score"""
    scorer = DeterminismScorer()

    # Level A: score >= 0.90
    assert scorer.assign_replay_level(0.95) == ReplayLevel.A
    assert scorer.assign_replay_level(0.90) == ReplayLevel.A

    # Level B: 0.50 <= score < 0.90
    assert scorer.assign_replay_level(0.75) == ReplayLevel.B
    assert scorer.assign_replay_level(0.50) == ReplayLevel.B

    # Level C: score < 0.50
    assert scorer.assign_replay_level(0.30) == ReplayLevel.C
    assert scorer.assign_replay_level(0.0) == ReplayLevel.C


def test_non_deterministic_config():
    """Test scoring of non-deterministic configuration"""
    scorer = DeterminismScorer()

    # Non-deterministic config
    model_config = ModelConfig(
        model_name="gpt-4",  # No version
        provider="openai",
        parameters=LLMParameters(
            temperature=1.0,  # High temperature
            seed=None,  # No seed!
        ),
    )

    prompt = ResolvedPrompt(
        template="",
        variables={},
        final_text="Test",
    )

    generator = ArtifactGenerator()
    artifact = generator.generate(
        run_id="test",
        tenant_id="test",
        inputs={},
        outputs={},
        llm_config=model_config,
        resolved_prompt=prompt,
        duration_ms=100,
    )

    report = scorer.score(llm_config=model_config, prompt=prompt, tool_calls=[], artifact=artifact)

    # Should have low score
    assert report.overall_score < 0.90

    # Should have warnings about determinism issues
    assert len(report.warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

