"""
Tests for replay detection logic
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from kurral.models.kurral import ModelConfig, LLMParameters, ResolvedPrompt, GraphVersion
from kurral.replay_detector import ReplayDetector


class TestReplayDetector:
    """Test suite for ReplayDetector"""

    def test_a_replay_detection(self, test_artifact):
        """Test A replay detection (everything matches)"""
        detector = ReplayDetector()
        
        # Create identical current config
        current_llm_config = ModelConfig(
            model_name="gpt-4-0613",
            model_version="0613",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=12345,
            ),
        )
        
        current_prompt = ResolvedPrompt(
            template="Test prompt",
            final_text="Test prompt",
        )
        
        current_graph = GraphVersion(
            graph_hash="test_graph_hash",
            tool_schemas_hash="test_tool_hash",
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_llm_config=current_llm_config,
            current_prompt=current_prompt,
            current_graph_version=current_graph,
        )
        
        assert result.replay_type == "A", f"Expected A replay, got {result.replay_type}"
        assert len(result.changes) == 0, f"Expected no changes, got {result.changes}"

    def test_b_replay_detection_model_change(self, test_artifact):
        """Test B replay detection (model changed)"""
        detector = ReplayDetector()
        
        # Create different model config
        current_llm_config = ModelConfig(
            model_name="gpt-4-turbo",  # Different model
            model_version="turbo",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=12345,
            ),
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_llm_config=current_llm_config,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "llm_config" in result.changes, "Expected llm_config in changes"

    def test_b_replay_detection_temperature_change(self, test_artifact):
        """Test B replay detection (temperature changed)"""
        detector = ReplayDetector()
        
        # Create config with different temperature
        current_llm_config = ModelConfig(
            model_name="gpt-4-0613",
            model_version="0613",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.7,  # Different temperature
                seed=12345,
            ),
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_llm_config=current_llm_config,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "llm_config" in result.changes, "Expected llm_config in changes"
        assert "temperature" in result.changes["llm_config"], "Expected temperature in changes"

    def test_b_replay_detection_prompt_change(self, test_artifact):
        """Test B replay detection (prompt changed)"""
        detector = ReplayDetector()
        
        # Create different prompt
        current_prompt = ResolvedPrompt(
            template="Different prompt",
            final_text="Different prompt",
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_prompt=current_prompt,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "prompt" in result.changes, "Expected prompt in changes"

    def test_b_replay_detection_graph_change(self, test_artifact):
        """Test B replay detection (graph changed)"""
        detector = ReplayDetector()
        
        # Create different graph version
        current_graph = GraphVersion(
            graph_hash="different_graph_hash",  # Different hash
            tool_schemas_hash="test_tool_hash",
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_graph_version=current_graph,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "graph_version" in result.changes, "Expected graph_version in changes"

    def test_b_replay_detection_tool_schemas_change(self, test_artifact):
        """Test B replay detection (tool schemas changed)"""
        detector = ReplayDetector()
        
        # Create graph with different tool schemas hash
        current_graph = GraphVersion(
            graph_hash="test_graph_hash",
            tool_schemas_hash="different_tool_hash",  # Different hash
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_graph_version=current_graph,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "graph_version" in result.changes, "Expected graph_version in changes"

    def test_b_replay_detection_seed_change(self, test_artifact):
        """Test B replay detection (seed changed)"""
        detector = ReplayDetector()
        
        # Create config with different seed
        current_llm_config = ModelConfig(
            model_name="gpt-4-0613",
            model_version="0613",
            provider="openai",
            parameters=LLMParameters(
                temperature=0.0,
                seed=99999,  # Different seed
            ),
        )
        
        result = detector.detect_changes(
            artifact=test_artifact,
            current_llm_config=current_llm_config,
        )
        
        assert result.replay_type == "B", f"Expected B replay, got {result.replay_type}"
        assert "llm_config" in result.changes, "Expected llm_config in changes"
        assert "seed" in result.changes["llm_config"], "Expected seed in changes"

