"""
Change detection logic to determine A vs B replay type
A replay: Everything matches - use artifact directly
B replay: Something changed - re-execute LLM with cached tools
"""

import hashlib
import json
from typing import Any, Optional

from kurral.models.kurral import (
    KurralArtifact,
    ModelConfig,
    ResolvedPrompt,
    GraphVersion,
    ReplayLevel,
)
from kurral.config import get_llm_parameters_from_artifact


class ReplayType:
    """Replay type classification"""
    A = "A"  # Everything matches - use artifact
    B = "B"  # Something changed - re-execute LLM


class ChangeDetectionResult:
    """Result of change detection analysis"""
    
    def __init__(
        self,
        replay_type: str,
        changes: dict[str, Any],
        matches: dict[str, bool]
    ):
        self.replay_type = replay_type
        self.changes = changes  # What changed
        self.matches = matches  # What matches
    
    def __repr__(self) -> str:
        return f"ChangeDetectionResult(replay_type={self.replay_type}, changes={len(self.changes)} items)"


class ReplayDetector:
    """
    Detects changes between artifact and current execution context
    to determine A vs B replay type based on determinism scoring
    """
    
    def __init__(self, determinism_threshold: float = 0.8):
        """
        Initialize replay detector
        
        Args:
            determinism_threshold: Score threshold for A vs B (default 0.8)
                                  Below threshold = A, above = B
        """
        self.determinism_threshold = determinism_threshold
    
    def calculate_determinism_score(
        self,
        artifact: KurralArtifact,
        current_llm_config: Optional[ModelConfig] = None,
    ) -> float:
        """
        Calculate determinism score based on LLM parameters
        
        If current_llm_config is None, assume same config as artifact → score = 1.0
        If current_llm_config is provided, compare parameters and calculate match score.
        
        Args:
            artifact: KurralArtifact with stored parameters
            current_llm_config: Optional current LLM config for comparison
            
        Returns:
            Determinism score (0.0 to 1.0)
        """
        # If no current config provided, we're using the same config as artifact
        # Perfect match → score = 1.0
        if current_llm_config is None:
            return 1.0
        
        # Get parameters from artifact (or defaults)
        artifact_params = get_llm_parameters_from_artifact(artifact.llm_config)
        current_params = current_llm_config.parameters or artifact_params
        
        # Calculate score based on parameter matching
        score_factors = []
        
        # Temperature match: if they match, score = 1.0; otherwise penalize
        artifact_temp = artifact_params.temperature
        current_temp = current_params.temperature if current_params else artifact_temp
        
        if artifact_temp == current_temp:
            # Perfect match
            temp_score = 1.0
        elif artifact_temp is None or current_temp is None:
            # One is unknown
            temp_score = 0.5
        else:
            # Mismatch - calculate penalty based on difference
            temp_diff = abs(artifact_temp - current_temp)
            temp_score = max(0.0, 1.0 - temp_diff)
        
        score_factors.append(temp_score)
        
        # Seed match: if both have seed and they match, score = 1.0
        artifact_seed = artifact_params.seed
        current_seed = current_params.seed if current_params else artifact_seed
        
        if artifact_seed == current_seed:
            seed_score = 1.0
        elif artifact_seed is None and current_seed is None:
            seed_score = 0.5  # Both missing
        elif artifact_seed is None or current_seed is None:
            seed_score = 0.5  # One missing
        else:
            seed_score = 0.0  # Different seeds
        
        score_factors.append(seed_score)
        
        # Model consistency
        if artifact.llm_config.model_name == current_llm_config.model_name:
            model_score = 1.0
        else:
            model_score = 0.0  # Model changed
        
        score_factors.append(model_score)
        
        # Provider consistency
        if artifact.llm_config.provider == current_llm_config.provider:
            provider_score = 1.0
        else:
            provider_score = 0.0  # Provider changed
        
        score_factors.append(provider_score)
        
        # Calculate overall score (average of factors)
        if score_factors:
            overall_score = sum(score_factors) / len(score_factors)
        else:
            overall_score = 0.5
        
        return overall_score
    
    def determine_replay_type(
        self,
        artifact: KurralArtifact,
        current_llm_config: Optional[ModelConfig] = None,
        current_prompt: Optional[ResolvedPrompt] = None,
        current_graph_version: Optional[GraphVersion] = None,
        current_inputs: Optional[dict[str, Any]] = None,
    ) -> ChangeDetectionResult:
        """
        Determine replay type (A or B) based on determinism score and changes
        
        A replay: Determinism score below threshold AND no changes detected
        B replay: Determinism score above threshold OR tools/LLM changed
        
        Args:
            artifact: Stored artifact from previous run
            current_llm_config: Current LLM configuration
            current_prompt: Current prompt
            current_graph_version: Current graph version
            current_inputs: Current inputs
            
        Returns:
            ChangeDetectionResult with replay_type (A or B)
        """
        # Calculate determinism score
        determinism_score = self.calculate_determinism_score(artifact, current_llm_config)
        
        # Detect changes (tools, LLM, prompt, etc.)
        changes = {}
        matches = {}
        
        # Check LLM config
        if current_llm_config:
            llm_match, llm_changes = self._compare_llm_config(
                artifact.llm_config, current_llm_config
            )
            matches["llm_config"] = llm_match
            if not llm_match:
                changes["llm_config"] = llm_changes
        
        # Check prompt
        if current_prompt:
            prompt_match, prompt_changes = self._compare_prompt(
                artifact.resolved_prompt, current_prompt
            )
            matches["prompt"] = prompt_match
            if not prompt_match:
                changes["prompt"] = prompt_changes
        
        # Check graph version (tools)
        if current_graph_version:
            graph_match, graph_changes = self._compare_graph_version(
                artifact.graph_version, current_graph_version
            )
            matches["graph_version"] = graph_match
            if not graph_match:
                changes["graph_version"] = graph_changes
        
        # Check inputs (if provided)
        if current_inputs is not None:
            inputs_match, inputs_changes = self._compare_inputs(
                artifact.inputs, current_inputs
            )
            matches["inputs"] = inputs_match
            if not inputs_match:
                changes["inputs"] = inputs_changes
        
        # Determine replay type:
        # - If tools changed → B (always, tools are critical)
        # - If LLM model/provider changed → B (always, different model = different behavior)
        # - If determinism score < threshold → B (low determinism, things changed)
        # - If determinism score >= threshold → A (high determinism, deterministic enough)
        tools_changed = (
            "graph_version" in changes 
            or "tool_schemas_hash" in changes 
            or any("tool" in str(k).lower() for k in changes.keys())
        )
        
        # Check if LLM model/provider changed (these should always trigger B replay)
        llm_config_changes = changes.get("llm_config", {})
        llm_changed = (
            "llm_config" in changes 
            and (
                "model_name" in llm_config_changes
                or "provider" in llm_config_changes
            )
        )
        
        if tools_changed:
            # Tools changed → B replay (always, even with high determinism score)
            replay_type = ReplayType.B
        elif llm_changed:
            # LLM model/provider changed → B replay (always, different model = different behavior)
            replay_type = ReplayType.B
        elif determinism_score < self.determinism_threshold:
            # Score below threshold (low determinism) → B replay
            replay_type = ReplayType.B
        else:
            # High determinism score (>= threshold) → A replay
            # The determinism score already accounts for temperature/seed differences
            # So if score is high enough and no critical changes, we can safely use A replay
            replay_type = ReplayType.A
        
        # Add determinism score to changes dict for visibility
        changes["determinism_score"] = determinism_score
        changes["determinism_threshold"] = self.determinism_threshold
        
        return ChangeDetectionResult(
            replay_type=replay_type,
            changes=changes,
            matches=matches
        )
    
    def detect_changes(
        self,
        artifact: KurralArtifact,
        current_llm_config: Optional[ModelConfig] = None,
        current_prompt: Optional[ResolvedPrompt] = None,
        current_graph_version: Optional[GraphVersion] = None,
        current_inputs: Optional[dict[str, Any]] = None,
    ) -> ChangeDetectionResult:
        """
        Compare artifact with current execution context to determine replay type
        
        This is a convenience method that calls determine_replay_type().
        Use determine_replay_type() for the full A/B logic with determinism scoring.
        
        Args:
            artifact: Stored artifact from previous run
            current_llm_config: Current LLM configuration
            current_prompt: Current prompt
            current_graph_version: Current graph version
            current_inputs: Current inputs
            
        Returns:
            ChangeDetectionResult with replay_type (A or B) and detected changes
        """
        return self.determine_replay_type(
            artifact=artifact,
            current_llm_config=current_llm_config,
            current_prompt=current_prompt,
            current_graph_version=current_graph_version,
            current_inputs=current_inputs,
        )
    
    def _compare_llm_config(
        self, artifact_config: ModelConfig, current_config: ModelConfig
    ) -> tuple[bool, dict[str, Any]]:
        """
        Compare LLM configurations
        
        Returns:
            (matches, changes_dict)
        """
        changes = {}
        
        # Compare model name
        if artifact_config.model_name != current_config.model_name:
            changes["model_name"] = {
                "artifact": artifact_config.model_name,
                "current": current_config.model_name
            }
        
        # Compare model version
        artifact_version = artifact_config.model_version or ""
        current_version = current_config.model_version or ""
        if artifact_version != current_version:
            changes["model_version"] = {
                "artifact": artifact_version,
                "current": current_version
            }
        
        # Compare provider
        if artifact_config.provider != current_config.provider:
            changes["provider"] = {
                "artifact": artifact_config.provider,
                "current": current_config.provider
            }
        
        # Compare parameters
        artifact_params = artifact_config.parameters
        current_params = current_config.parameters
        
        if artifact_params.temperature != current_params.temperature:
            changes["temperature"] = {
                "artifact": artifact_params.temperature,
                "current": current_params.temperature
            }
        
        if artifact_params.seed != current_params.seed:
            changes["seed"] = {
                "artifact": artifact_params.seed,
                "current": current_params.seed
            }
        
        if artifact_params.top_p != current_params.top_p:
            changes["top_p"] = {
                "artifact": artifact_params.top_p,
                "current": current_params.top_p
            }
        
        if artifact_params.top_k != current_params.top_k:
            changes["top_k"] = {
                "artifact": artifact_params.top_k,
                "current": current_params.top_k
            }
        
        if artifact_params.max_tokens != current_params.max_tokens:
            changes["max_tokens"] = {
                "artifact": artifact_params.max_tokens,
                "current": current_params.max_tokens
            }
        
        if artifact_params.frequency_penalty != current_params.frequency_penalty:
            changes["frequency_penalty"] = {
                "artifact": artifact_params.frequency_penalty,
                "current": current_params.frequency_penalty
            }
        
        if artifact_params.presence_penalty != current_params.presence_penalty:
            changes["presence_penalty"] = {
                "artifact": artifact_params.presence_penalty,
                "current": current_params.presence_penalty
            }
        
        matches = len(changes) == 0
        return matches, changes
    
    def _compare_prompt(
        self, artifact_prompt: ResolvedPrompt, current_prompt: ResolvedPrompt
    ) -> tuple[bool, dict[str, Any]]:
        """
        Compare prompts
        
        Returns:
            (matches, changes_dict)
        """
        changes = {}
        
        # Compare final text hash (most reliable)
        artifact_hash = artifact_prompt.final_text_hash or self._hash_text(artifact_prompt.final_text)
        current_hash = current_prompt.final_text_hash or self._hash_text(current_prompt.final_text)
        
        if artifact_hash != current_hash:
            changes["final_text"] = {
                "artifact_hash": artifact_hash,
                "current_hash": current_hash,
                "artifact_text": artifact_prompt.final_text[:100] + "..." if len(artifact_prompt.final_text) > 100 else artifact_prompt.final_text,
                "current_text": current_prompt.final_text[:100] + "..." if len(current_prompt.final_text) > 100 else current_prompt.final_text,
            }
        
        # Compare template hash
        if artifact_prompt.template_hash and current_prompt.template_hash:
            if artifact_prompt.template_hash != current_prompt.template_hash:
                changes["template"] = {
                    "artifact_hash": artifact_prompt.template_hash,
                    "current_hash": current_prompt.template_hash
                }
        
        # Don't compare variables hash - variables contain user input which changes per run
        # Only template hash matters for change detection
        
        matches = len(changes) == 0
        return matches, changes
    
    def _compare_graph_version(
        self, artifact_graph: Optional[GraphVersion], current_graph: Optional[GraphVersion]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Compare graph versions
        
        Returns:
            (matches, changes_dict)
        """
        changes = {}
        
        # If both are None, they match
        if artifact_graph is None and current_graph is None:
            return True, {}
        
        # If one is None and other isn't, they don't match
        if artifact_graph is None or current_graph is None:
            changes["graph_version"] = {
                "artifact": "None" if artifact_graph is None else "Present",
                "current": "None" if current_graph is None else "Present"
            }
            return False, changes
        
        # Compare graph hash
        if artifact_graph.graph_hash and current_graph.graph_hash:
            if artifact_graph.graph_hash != current_graph.graph_hash:
                changes["graph_hash"] = {
                    "artifact": artifact_graph.graph_hash,
                    "current": current_graph.graph_hash
                }
        
        # Compare tool schemas hash
        if artifact_graph.tool_schemas_hash and current_graph.tool_schemas_hash:
            if artifact_graph.tool_schemas_hash != current_graph.tool_schemas_hash:
                changes["tool_schemas_hash"] = {
                    "artifact": artifact_graph.tool_schemas_hash,
                    "current": current_graph.tool_schemas_hash
                }
        
        # Compare graph checksum
        if artifact_graph.graph_checksum and current_graph.graph_checksum:
            if artifact_graph.graph_checksum != current_graph.graph_checksum:
                changes["graph_checksum"] = {
                    "artifact": artifact_graph.graph_checksum,
                    "current": current_graph.graph_checksum
                }
        
        matches = len(changes) == 0
        return matches, changes
    
    def _compare_inputs(
        self, artifact_inputs: dict[str, Any], current_inputs: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Compare inputs
        
        Returns:
            (matches, changes_dict)
        """
        changes = {}
        
        # Compare by serializing and hashing
        artifact_str = json.dumps(artifact_inputs, sort_keys=True)
        current_str = json.dumps(current_inputs, sort_keys=True)
        
        artifact_hash = hashlib.sha256(artifact_str.encode()).hexdigest()
        current_hash = hashlib.sha256(current_str.encode()).hexdigest()
        
        if artifact_hash != current_hash:
            changes["inputs"] = {
                "artifact_hash": artifact_hash,
                "current_hash": current_hash,
                "artifact_keys": list(artifact_inputs.keys()),
                "current_keys": list(current_inputs.keys())
            }
        
        matches = len(changes) == 0
        return matches, changes
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Hash text string"""
        return hashlib.sha256(text.encode()).hexdigest()

