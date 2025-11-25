"""
Tests for artifact generation
"""

import pytest
from datetime import datetime

from kurral.core.artifact import ArtifactGenerator
from kurral.models.kurral import ModelConfig, ResolvedPrompt, ToolCall, LLMParameters


def test_artifact_generation():
    """Test basic artifact generation"""
    generator = ArtifactGenerator()

    model_config = ModelConfig(
        model_name="gpt-4-0613",
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

    artifact = generator.generate(
        run_id="test_run_123",
        tenant_id="test_tenant",
        inputs={"query": "hello"},
        outputs={"response": "hi there"},
        llm_config=model_config,
        resolved_prompt=prompt,
        duration_ms=1000,
    )

    assert artifact.run_id == "test_run_123"
    assert artifact.tenant_id == "test_tenant"
    assert artifact.deterministic is True  # Should be deterministic with seed
    assert artifact.replay_level.value in ["A", "B", "C"]


def test_artifact_with_tool_calls():
    """Test artifact generation with tool calls"""
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
        template="Test prompt",
        variables={},
        final_text="Test prompt",
    )

    tool_calls = [
        ToolCall(
            tool_name="get_weather",
            inputs={"location": "NYC"},
            outputs={"temperature": 72, "condition": "sunny"},
            cache_key=ToolCall.generate_cache_key("get_weather", {"location": "NYC"}),
        )
    ]

    artifact = generator.generate(
        run_id="test_run_with_tools",
        tenant_id="test_tenant",
        inputs={"query": "weather in NYC?"},
        outputs={"response": "It's 72 and sunny"},
        llm_config=model_config,
        resolved_prompt=prompt,
        tool_calls=tool_calls,
        duration_ms=2000,
    )

    assert len(artifact.tool_calls) == 1
    assert artifact.tool_calls[0].tool_name == "get_weather"


def test_artifact_serialization():
    """Test artifact can be serialized and deserialized"""
    generator = ArtifactGenerator()

    model_config = ModelConfig(
        model_name="gpt-4",
        provider="openai",
        parameters=LLMParameters(
            temperature=0.0,
        ),
    )

    prompt = ResolvedPrompt(
        template="Test",
        variables={},
        final_text="Test",
    )

    artifact = generator.generate(
        run_id="test_serialization",
        tenant_id="test",
        inputs={},
        outputs={},
        llm_config=model_config,
        resolved_prompt=prompt,
        duration_ms=100,
    )

    # Serialize to JSON
    json_str = artifact.to_json()
    assert json_str

    # Deserialize
    loaded = artifact.from_json(json_str)
    assert loaded.run_id == artifact.run_id
    assert loaded.kurral_id == artifact.kurral_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

