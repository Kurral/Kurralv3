"""
Tests for replay engine
"""

import asyncio
from unittest import mock

import pytest

from kurral.core.artifact import ArtifactGenerator
from kurral.core.replay import ReplayEngine
from kurral.models.kurral import LLMParameters, ModelConfig, ResolvedPrompt, ToolCall
from kurral.storage.cache import MemoryCache


@pytest.mark.asyncio
async def test_basic_replay():
    """Test basic replay functionality"""
    # Create test artifact
    with mock.patch("kurral.storage.r2.boto3", create=True), mock.patch(
        "kurral.storage.postgres.sqlalchemy", create=True
    ):
        generator = ArtifactGenerator()

        model_config = ModelConfig(
            model_name="gpt-4",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=42,
            ),
        )

        prompt = ResolvedPrompt(
            template="Test",
            variables={},
            final_text="Test",
        )

        artifact = generator.generate(
            run_id="replay_test",
            tenant_id="test",
            inputs={"query": "test"},
            outputs={"response": "test response"},
            llm_config=model_config,
            resolved_prompt=prompt,
            duration_ms=100,
        )

    # Replay
    engine = ReplayEngine()
    result = await engine.replay(artifact)

    assert result.kurral_id == artifact.kurral_id
    assert result.outputs == artifact.outputs
    assert result.match is True
    assert result.llm_state is not None
    assert result.llm_state.model_name == artifact.llm_config.model_name
    assert result.llm_state.temperature == pytest.approx(0.0)
    assert result.llm_state.seed == 42
    assert result.validation is not None
    assert result.validation.hash_match is True
    assert result.validation.structural_match is True
    assert result.replay_metadata is not None
    assert result.replay_metadata.replay_level == artifact.replay_level
    assert result.replay_metadata.record_ref == artifact.run_id


@pytest.mark.asyncio
async def test_replay_with_tool_calls():
    """Test replay with cached tool calls"""
    cache = MemoryCache()

    # Create artifact with tool calls
    with mock.patch("kurral.storage.r2.boto3", create=True), mock.patch(
        "kurral.storage.postgres.sqlalchemy", create=True
    ):
        generator = ArtifactGenerator()

        model_config = ModelConfig(
            model_name="gpt-4",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=42,
            ),
        )

        prompt = ResolvedPrompt(
            template="Test",
            variables={},
            final_text="Test",
        )

        tool_calls = [
            ToolCall(
                tool_name="get_data",
                inputs={"id": "123"},
                outputs={"data": "result"},
                cache_key=ToolCall.generate_cache_key("get_data", {"id": "123"}),
            )
        ]

        artifact = generator.generate(
            run_id="replay_with_tools",
            tenant_id="test",
            inputs={"query": "get data"},
            outputs={"response": "result"},
            llm_config=model_config,
            resolved_prompt=prompt,
            tool_calls=tool_calls,
            duration_ms=200,
        )

    # Replay
    engine = ReplayEngine(cache_backend=cache)
    result = await engine.replay(artifact)

    assert result.cache_hits > 0
    assert result.tool_calls[0].stubbed_in_replay is True
    assert result.validation.hash_match is True
    assert result.validation.structural_match is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

