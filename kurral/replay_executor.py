"""
Replay executor for A and B replay types
A replay: Everything matches - return artifact outputs directly
B replay: Something changed - re-execute LLM with cached tool calls
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from kurral.models.kurral import (
    KurralArtifact,
    ModelConfig,
    ResolvedPrompt,
    ReplayResult,
    ReplayLLMState,
    ReplayValidation,
    ReplayMetadata,
    ReplayLevel,
    ToolCall,
    AssertionResult,
)
from kurral.replay_detector import ReplayType, ChangeDetectionResult
from kurral.cache import CacheBackend, MemoryCache


class ReplayExecutor:
    """
    Executes A or B replay based on change detection
    """
    
    def __init__(self, cache_backend: Optional[CacheBackend] = None):
        """
        Initialize replay executor
        
        Args:
            cache_backend: Cache backend for tool responses (defaults to MemoryCache)
        """
        self.cache = cache_backend or MemoryCache()
        # Track which artifact tool calls were used during replay
        self._used_tool_call_keys: set[str] = set()
        # Track new tool calls (not in artifact)
        self._new_tool_calls: list[ToolCall] = []
    
    async def execute_replay(
        self,
        artifact: KurralArtifact,
        detection_result: ChangeDetectionResult,
        llm_client: Optional[Any] = None,  # LLM client for B replay
    ) -> ReplayResult:
        """
        Execute replay based on detection result
        
        Args:
            artifact: KurralArtifact to replay
            detection_result: ChangeDetectionResult from ReplayDetector
            llm_client: Optional LLM client for B replay (e.g., OpenAI client)
            
        Returns:
            ReplayResult with outputs and metadata
        """
        start_time = datetime.utcnow()
        
        # Prime cache with tool calls from artifact
        self._prime_cache_from_artifact(artifact)
        
        if detection_result.replay_type == ReplayType.A:
            # A replay: Everything matches - return artifact outputs directly
            return await self._execute_a_replay(artifact, start_time)
        else:
            # B replay: Re-execute LLM with cached tool calls
            if llm_client is None:
                raise ValueError("LLM client required for B replay")
            return await self._execute_b_replay(artifact, llm_client, start_time)
    
    async def _execute_a_replay(
        self, artifact: KurralArtifact, start_time: datetime
    ) -> ReplayResult:
        """
        Execute A replay: return artifact outputs directly
        
        Args:
            artifact: KurralArtifact to replay
            start_time: Replay start time
            
        Returns:
            ReplayResult
        """
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Outputs match exactly (we're returning artifact outputs)
        match = True
        diff = None
        
        # Compute validation (should match exactly)
        validation = self._compute_validation(artifact.outputs, artifact.outputs, diff)
        
        # Build LLM state from artifact
        llm_state = self._build_llm_state(artifact)
        
        # Build replay metadata
        replay_metadata = ReplayMetadata(
            replay_id=str(uuid4()),
            record_ref=artifact.run_id,
            replay_level=ReplayLevel.A,  # A replay
            assertion_results=[],
        )
        
        # Mark all tool calls as stubbed
        stubbed_tool_calls = [
            tc.model_copy(update={"stubbed_in_replay": True})
            for tc in artifact.tool_calls
        ]
        
        # All artifact tool calls were used (A replay uses all of them)
        self._used_tool_call_keys = {tc.cache_key for tc in artifact.tool_calls}
        unused_tool_calls = []  # None unused in A replay
        
        return ReplayResult(
            kurral_id=artifact.kurral_id,
            replay_timestamp=start_time,
            outputs=artifact.outputs,
            match=match,
            diff=diff,
            tool_calls=stubbed_tool_calls,
            duration_ms=duration_ms,
            cache_hits=len(artifact.tool_calls),
            cache_misses=0,
            new_tool_calls=self._new_tool_calls,
            unused_tool_calls=unused_tool_calls,
            stream=self._reconstruct_output_stream(artifact.outputs),
            graph_version=artifact.graph_version,
            llm_state=llm_state,
            validation=validation,
            replay_metadata=replay_metadata,
        )
    
    async def _execute_b_replay(
        self,
        artifact: KurralArtifact,
        llm_client: Any,
        start_time: datetime,
    ) -> ReplayResult:
        """
        Execute B replay: re-execute LLM with cached tool calls
        
        Args:
            artifact: KurralArtifact to replay
            llm_client: LLM client (e.g., OpenAI client)
            start_time: Replay start time
            
        Returns:
            ReplayResult
        """
        # Re-execute LLM with same inputs and prompt
        # Use cached tool responses when LLM calls tools
        
        # Extract prompt text
        prompt_text = artifact.resolved_prompt.final_text
        
        # Extract messages if available
        messages = artifact.resolved_prompt.messages
        if messages:
            # Use messages format
            llm_messages = messages
        else:
            # Use simple prompt format
            from langchain_core.messages import HumanMessage
            llm_messages = [HumanMessage(content=prompt_text)]
        
        # Call LLM using LangChain interface
        try:
            # Check if it's a LangChain LLM (has invoke/ainvoke methods)
            if hasattr(llm_client, "ainvoke") or hasattr(llm_client, "invoke"):
                # Use LangChain async interface
                if hasattr(llm_client, "ainvoke"):
                    response = await llm_client.ainvoke(llm_messages)
                else:
                    # Sync version - run in executor
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, lambda: llm_client.invoke(llm_messages)
                    )
                
                # Extract content from LangChain response
                if hasattr(response, "content"):
                    output_text = response.content
                elif isinstance(response, str):
                    output_text = response
                else:
                    output_text = str(response)
                
                outputs = {"result": output_text, "full_text": output_text}
            
            # Fallback: Try OpenAI-style client
            elif hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                # Build LLM parameters from artifact
                params = artifact.llm_config.parameters
                
                # Prepare LLM call parameters
                llm_params = {
                    "model": artifact.llm_config.model_name,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": params.temperature,
                }
                
                # Add optional parameters
                if params.seed is not None:
                    llm_params["seed"] = params.seed
                if params.top_p is not None:
                    llm_params["top_p"] = params.top_p
                if params.max_tokens is not None:
                    llm_params["max_tokens"] = params.max_tokens
                if params.frequency_penalty is not None:
                    llm_params["frequency_penalty"] = params.frequency_penalty
                if params.presence_penalty is not None:
                    llm_params["presence_penalty"] = params.presence_penalty
                
                response = await self._call_openai_llm(llm_client, llm_params)
                
                # Extract outputs from response
                if hasattr(response, "choices") and response.choices:
                    output_text = response.choices[0].message.content
                    outputs = {"result": output_text, "full_text": output_text}
                elif isinstance(response, dict):
                    outputs = response
                else:
                    outputs = {"result": str(response)}
            
            else:
                # Generic callable - try to call with messages
                if asyncio.iscoroutinefunction(llm_client):
                    response = await llm_client(llm_messages)
                else:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, lambda: llm_client(llm_messages)
                    )
                
                if isinstance(response, dict):
                    outputs = response
                else:
                    outputs = {"result": str(response)}
            
        except Exception as e:
            # On error, return artifact outputs but mark as error
            outputs = artifact.outputs
            error = str(e)
        else:
            error = None
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Compare outputs
        match = self._compare_outputs(artifact.outputs, outputs)
        diff = None if match else self._calculate_diff(artifact.outputs, outputs)
        
        # Compute validation
        validation = self._compute_validation(artifact.outputs, outputs, diff)
        
        # Build LLM state
        llm_state = self._build_llm_state(artifact)
        
        # Build replay metadata
        replay_metadata = ReplayMetadata(
            replay_id=str(uuid4()),
            record_ref=artifact.run_id,
            replay_level=ReplayLevel.B,  # B replay
            assertion_results=[],
        )
        
        # Mark tool calls as stubbed (they should use cache)
        # Note: In actual agent execution, we'd track which ones were used
        # For now, we assume all artifact tool calls were available but may not all be used
        stubbed_tool_calls = [
            tc.model_copy(update={"stubbed_in_replay": True})
            for tc in artifact.tool_calls
        ]
        
        # Identify unused tool calls (from artifact but not used)
        # In a real implementation, we'd track cache hits to know which were used
        # For now, we'll mark all as potentially used (this will be enhanced when we
        # actually intercept tool calls during agent execution)
        artifact_tool_keys = {tc.cache_key for tc in artifact.tool_calls}
        unused_tool_calls = [
            tc for tc in artifact.tool_calls
            if tc.cache_key not in self._used_tool_call_keys
        ]
        
        return ReplayResult(
            kurral_id=artifact.kurral_id,
            replay_timestamp=start_time,
            outputs=outputs,
            match=match,
            diff=diff,
            tool_calls=stubbed_tool_calls,
            error=error,
            duration_ms=duration_ms,
            cache_hits=len(self._used_tool_call_keys),
            cache_misses=len(self._new_tool_calls),
            new_tool_calls=self._new_tool_calls,
            unused_tool_calls=unused_tool_calls,
            stream=self._reconstruct_output_stream(outputs),
            graph_version=artifact.graph_version,
            llm_state=llm_state,
            validation=validation,
            replay_metadata=replay_metadata,
        )
    
    async def _call_openai_llm(self, client: Any, params: dict[str, Any]) -> Any:
        """Call OpenAI LLM (async)"""
        # Check if client is async
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            create_method = client.chat.completions.create
            # Try async first
            try:
                if asyncio.iscoroutinefunction(create_method):
                    return await create_method(**params)
                else:
                    # Sync version - run in executor
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: create_method(**params))
            except Exception:
                # Fallback to sync
                return create_method(**params)
        else:
            # Generic callable
            if asyncio.iscoroutinefunction(client):
                return await client(**params)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: client(**params))
    
    def _prime_cache_from_artifact(self, artifact: KurralArtifact) -> None:
        """Prime cache with all tool calls from artifact"""
        self._used_tool_call_keys.clear()
        self._new_tool_calls.clear()
        for tool_call in artifact.tool_calls:
            stub_payload = self._build_tool_stub_payload(tool_call)
            if stub_payload:
                self.cache.prime(tool_call.cache_key, stub_payload)
    
    def _build_tool_stub_payload(self, tool_call: ToolCall) -> Optional[dict[str, Any]]:
        """Construct cache payload for a tool call"""
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
    def _compare_outputs(original: dict[str, Any], replayed: dict[str, Any]) -> bool:
        """Compare original and replayed outputs"""
        return json.dumps(original, sort_keys=True) == json.dumps(replayed, sort_keys=True)
    
    @staticmethod
    def _calculate_diff(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
        """Calculate diff between outputs"""
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
    
    @staticmethod
    def _reconstruct_output_stream(outputs: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Rebuild output stream representation from stored artifact data"""
        if not isinstance(outputs, dict):
            return None
        
        items = outputs.get("items")
        full_text = outputs.get("full_text")
        stream_map = outputs.get("stream_map")
        
        if items is None and isinstance(full_text, str):
            items = [full_text]
        
        if full_text is None and isinstance(items, list):
            full_text = "".join(items)
        
        if stream_map is None and isinstance(items, list):
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

