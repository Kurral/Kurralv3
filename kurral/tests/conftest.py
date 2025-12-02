"""
Pytest configuration and fixtures
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from kurral.models.kurral import (
    KurralArtifact,
    ModelConfig,
    LLMParameters,
    ResolvedPrompt,
    TimeEnvironment,
    DeterminismReport,
    ReplayLevel,
    TokenUsage,
    GraphVersion,
)


@pytest.fixture
def test_artifact():
    """Create a test artifact fixture"""
    return KurralArtifact(
        kurral_id=uuid4(),
        run_id="test_run_123",
        tenant_id="test_tenant",
        semantic_buckets=["test"],
        environment="test",
        deterministic=True,
        replay_level=ReplayLevel.A,
        determinism_report=DeterminismReport(
            overall_score=0.95,
            breakdown={
                "model_version": 1.0,
                "random_seed": 1.0,
                "prompt": 1.0,
                "tool_cache": 1.0,
                "environment": 1.0,
                "parameters": 1.0,
            },
            missing_fields=[],
            warnings=[],
        ),
        inputs={"query": "test query"},
        outputs={"result": "test result"},
        llm_config=ModelConfig(
            model_name="gpt-4-0613",
            model_version="0613",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=12345,
            ),
        ),
        resolved_prompt=ResolvedPrompt(
            template="Test prompt",
            final_text="Test prompt",
        ),
        graph_version=GraphVersion(
            graph_hash="test_graph_hash",
            tool_schemas_hash="test_tool_hash",
        ),
        tool_calls=[],
        time_env=TimeEnvironment(
            timestamp=TimeEnvironment.model_fields["timestamp"].default_factory(),
            wall_clock_time="2024-01-01T00:00:00Z",
        ),
        duration_ms=100,
        token_usage=TokenUsage(),
    )


@pytest.fixture
def temp_storage_path(tmp_path):
    """Create a temporary storage path for tests"""
    return tmp_path / "test_artifacts"

