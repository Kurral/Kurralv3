"""
Replay engine for deterministic execution
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from kurral.models.kurral import (
    KurralArtifact,
    ReplayLLMState,
    ReplayMetadata,
    ReplayOverrides,
    ReplayResult,
    ReplayValidation,
    ToolCall,
)
from kurral.storage.cache import CacheBackend, MemoryCache


class ReplayEngine:
    """
    Engine for replaying .kurral artifacts deterministically

    Replays freeze time, stub side-effects, and use cached tool responses.
    
    ⚠️  IMPORTANT: Replay execution does NOT depend on replay_level (ABC).
    All artifacts are replayed the same way - tool calls are stubbed and
    outputs are cached regardless of determinism score.
    
    For comparing agent versions (e.g., model migration, prompt changes),
    use the ABTestEngine from kurral.core.ab_test instead.
    """

    def __init__(self, cache_backend: Optional[CacheBackend] = None):
        """
        Initialize replay engine

        Args:
            cache_backend: Cache backend for tool responses (defaults to in-memory)
        """
        self.cache = cache_backend or MemoryCache()

    async def replay(
        self,
        artifact: KurralArtifact,
        overrides: Optional[ReplayOverrides] = None,
    ) -> ReplayResult:
        """
        Execute replay of artifact

        This is a simplified replay that:
        1. Primes cache with tool responses
        2. Optionally applies overrides
        3. Returns cached outputs

        In a full implementation, you would:
        - Re-execute the LLM with same config
        - Stub all tool calls with cached responses
        - Freeze time to artifact.time_env.timestamp
        - Compare outputs

        Args:
            artifact: KurralArtifact to replay
            overrides: Optional overrides for testing

        Returns:
            ReplayResult with outputs and comparison
        """
        start_time = datetime.utcnow()

        # Prime cache with all tool calls and capture stubbed copies
        cache_hits = 0
        cache_misses = 0
        stubbed_tool_calls: list[ToolCall] = []

        for tool_call in artifact.tool_calls:
            stub_payload = self._build_tool_stub_payload(tool_call)
            if stub_payload is None:
                cache_misses += 1
                stubbed_tool_calls.append(tool_call)
                continue

            self.cache.prime(tool_call.cache_key, stub_payload)
            cache_hits += 1

            stubbed_tool_calls.append(
                tool_call.model_copy(update={"stubbed_in_replay": True})
            )

        # Apply overrides
        if overrides:
            # In full implementation: re-execute with overrides
            # For now, we just return modified version
            outputs = artifact.outputs.copy()

            if overrides.inputs:
                # Would re-execute with new inputs
                pass

            if overrides.prompt:
                # Would re-execute with new prompt
                pass

        else:
            # No overrides - outputs should match exactly
            outputs = artifact.outputs

        # Calculate match
        match = self._compare_outputs(artifact.outputs, outputs)

        # Calculate diff if not matching
        diff = None if match else self._calculate_diff(artifact.outputs, outputs)

        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        stream_data = self._reconstruct_output_stream(artifact.outputs)
        validation = self._compute_validation(artifact.outputs, outputs, diff)
        llm_state = self._build_llm_state(artifact)
        replay_metadata = ReplayMetadata(
            replay_id=str(uuid4()),
            record_ref=artifact.run_id,
            replay_level=artifact.replay_level,
            assertion_results=[],
        )

        return ReplayResult(
            kurral_id=artifact.kurral_id,
            replay_timestamp=start_time,
            outputs=outputs,
            match=match,
            diff=diff,
            tool_calls=stubbed_tool_calls or artifact.tool_calls,
            duration_ms=duration_ms,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            stream=stream_data,
            graph_version=artifact.graph_version,
            llm_state=llm_state,
            validation=validation,
            replay_metadata=replay_metadata,
        )

    def stub_side_effects(self, tool_calls: list[ToolCall]) -> dict[str, Any]:
        """
        Replace write/delete operations with cache lookups

        This prevents actual side effects during replay

        Args:
            tool_calls: List of tool calls to stub

        Returns:
            Mapping of cache_key -> cached response
        """
        stubbed = {}

        for tool_call in tool_calls:
            # Check if this is a side-effect operation
            if self._is_side_effect(tool_call.tool_name):
                # Use cached response instead of executing
                cached = self.cache.get(tool_call.cache_key)
                if cached:
                    stubbed[tool_call.cache_key] = cached

        return stubbed

    @staticmethod
    def _is_side_effect(tool_name: str) -> bool:
        """
        Determine if a tool call has side effects

        Side effects include: HTTP POST/PUT/DELETE, DB writes, file writes, etc.
        """
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

    @staticmethod
    def _compare_outputs(original: dict[str, Any], replayed: dict[str, Any]) -> bool:
        """
        Compare original and replayed outputs

        Returns True if they match
        """
        # Deep equality check
        return json.dumps(original, sort_keys=True) == json.dumps(replayed, sort_keys=True)

    @staticmethod
    def _calculate_diff(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate diff between outputs

        Returns a structured diff
        """
        diff: dict[str, Any] = {
            "added": {},
            "removed": {},
            "modified": {},
        }

        # Keys in replayed but not original
        for key in replayed:
            if key not in original:
                diff["added"][key] = replayed[key]
            elif original[key] != replayed[key]:
                diff["modified"][key] = {
                    "original": original[key],
                    "replayed": replayed[key],
                }

        # Keys in original but not replayed
        for key in original:
            if key not in replayed:
                diff["removed"][key] = original[key]

        return diff

    async def replay_with_overrides(
        self,
        artifact: KurralArtifact,
        prompt_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        model_override: Optional[str] = None,
    ) -> ReplayResult:
        """
        Replay with specific overrides

        Convenience method for common override scenarios

        Args:
            artifact: Artifact to replay
            prompt_override: New prompt text
            temperature_override: New temperature
            model_override: New model name

        Returns:
            ReplayResult
        """
        overrides = ReplayOverrides(
            prompt=prompt_override,
            temperature=temperature_override,
            model_name=model_override,
        )

        return await self.replay(artifact, overrides)

    def prime_cache_from_artifact(self, artifact: KurralArtifact) -> None:
        """
        Prime cache with all tool calls from artifact

        Useful for pre-loading before replay

        Args:
            artifact: Artifact with tool calls
        """
        for tool_call in artifact.tool_calls:
            stub_payload = self._build_tool_stub_payload(tool_call)
            if stub_payload:
                self.cache.prime(tool_call.cache_key, stub_payload)

    def _build_tool_stub_payload(self, tool_call: ToolCall) -> Optional[dict[str, Any]]:
        """Construct cache payload for a tool call using recorded metadata"""

        output_payload = tool_call.output or tool_call.outputs
        input_payload = tool_call.input or tool_call.inputs

        if not tool_call.cache_key:
            return None

        if output_payload is None and input_payload is None:
            return None

        status_value = tool_call.status.value if tool_call.status else None
        effect_type_value = (
            tool_call.effect_type.value if tool_call.effect_type else None
        )

        stub_payload: dict[str, Any] = {
            "tool_name": tool_call.tool_name,
            "input": input_payload,
            "output": output_payload,
            "status": status_value,
            "latency_ms": tool_call.latency_ms,
            "cache_key": tool_call.cache_key,
            "output_hash": tool_call.output_hash,
        }

        if tool_call.summary:
            stub_payload["summary"] = tool_call.summary
        if tool_call.error_text:
            stub_payload["error_text"] = tool_call.error_text
        if effect_type_value:
            stub_payload["effect_type"] = effect_type_value

        return stub_payload

    @staticmethod
    def _build_llm_state(artifact: KurralArtifact) -> ReplayLLMState:
        """Hydrate LLM sampling state from artifact"""

        params = artifact.llm_config.parameters
        return ReplayLLMState(
            model_name=artifact.llm_config.model_name,
            provider=artifact.llm_config.provider,
            model_version=artifact.llm_config.model_version,
            temperature=params.temperature,
            top_p=params.top_p,
            top_k=params.top_k,
            max_tokens=params.max_tokens,
            frequency_penalty=params.frequency_penalty,
            presence_penalty=params.presence_penalty,
            seed=params.seed,
        )

    def _compute_validation(
        self,
        original: dict[str, Any],
        replayed: dict[str, Any],
        diff: Optional[dict[str, Any]],
    ) -> ReplayValidation:
        """Compute hash based and structural validation for replay outputs"""

        original_hash = self._hash_payload(original)
        replay_hash = self._hash_payload(replayed)
        structural_match = self._structural_match(original, replayed)

        return ReplayValidation(
            original_hash=original_hash,
            replay_hash=replay_hash,
            hash_match=original_hash == replay_hash,
            structural_match=structural_match,
            diff=diff if diff else None,
        )

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        """Generate deterministic hash from payload"""

        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _structural_match(self, original: Any, replayed: Any) -> bool:
        """Check structural equivalence between original and replay outputs"""

        if isinstance(original, dict) and isinstance(replayed, dict):
            if set(original.keys()) != set(replayed.keys()):
                return False
            return all(
                self._structural_match(original[key], replayed[key]) for key in original.keys()
            )

        if isinstance(original, list) and isinstance(replayed, list):
            if len(original) != len(replayed):
                return False
            return all(self._structural_match(o, r) for o, r in zip(original, replayed))

        if original is None or replayed is None:
            return original is None and replayed is None

        return isinstance(replayed, type(original))

    @staticmethod
    def _reconstruct_output_stream(outputs: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Rebuild output stream representation from stored artifact data"""

        if not isinstance(outputs, dict):
            return None

        items = outputs.get("items")
        full_text = outputs.get("full_text")
        stream_map = outputs.get("stream_map")

        if items is None and isinstance(full_text, str):
            # Fall back to chunking the full text into a single fragment
            items = [full_text]

        if full_text is None and isinstance(items, list):
            full_text = "".join(items)

        if stream_map is None and isinstance(items, list):
            # Synthesize stream map preserving offsets
            stream_map = []
            offset = 0
            for index, fragment in enumerate(items):
                fragment_str = fragment or ""
                length = len(fragment_str)
                entry = {
                    "fragment": fragment_str,
                    "offset": offset,
                    "length": length,
                    "index": index,
                    "timestamp_ms": None,
                }
                stream_map.append(entry)
                offset += length

        if items is None and full_text is None:
            return None

        return {
            "items": items,
            "full_text": full_text,
            "stream_map": stream_map,
        }


class BatchReplayEngine:
    """Engine for replaying multiple artifacts in batch"""

    def __init__(self, cache_backend: Optional[CacheBackend] = None):
        """Initialize batch replay engine"""
        self.engine = ReplayEngine(cache_backend)

    async def replay_batch(
        self,
        artifacts: list[KurralArtifact],
        overrides: Optional[ReplayOverrides] = None,
        max_concurrent: int = 5,
    ) -> list[ReplayResult]:
        """
        Replay multiple artifacts concurrently

        Args:
            artifacts: List of artifacts to replay
            overrides: Optional overrides to apply to all
            max_concurrent: Maximum concurrent replays

        Returns:
            List of ReplayResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def replay_with_limit(artifact: KurralArtifact) -> ReplayResult:
            async with semaphore:
                return await self.engine.replay(artifact, overrides)

        tasks = [replay_with_limit(artifact) for artifact in artifacts]
        return await asyncio.gather(*tasks)

    async def replay_with_sampling(
        self,
        artifact: KurralArtifact,
        num_samples: int = 5,
        overrides: Optional[ReplayOverrides] = None,
    ) -> list[ReplayResult]:
        """
        Replay the same artifact multiple times

        Useful for measuring variance in non-deterministic scenarios

        Args:
            artifact: Artifact to replay
            num_samples: Number of replay samples
            overrides: Optional overrides

        Returns:
            List of ReplayResults
        """
        tasks = [self.engine.replay(artifact, overrides) for _ in range(num_samples)]
        return await asyncio.gather(*tasks)

