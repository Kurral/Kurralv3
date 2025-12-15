"""
MCP Replay Engine

Handles replay mode: returns cached responses instead of calling real servers.
"""

from typing import Optional, Dict, Any, List
import logging
import json

from kurral.mcp.models import JSONRPCRequest, JSONRPCResponse, CapturedMCPCall, JSONRPCError
from kurral.mcp.config import MCPConfig, ReplayConfig

logger = logging.getLogger("kurral.mcp.replay")


class MCPReplayEngine:
    """
    Handles replay mode: returns cached responses instead of calling real servers.
    """

    def __init__(self, config: MCPConfig, artifact_data: Dict[str, Any]):
        self.config = config
        self.replay_config = config.replay

        # Load captured calls from artifact
        self.cached_calls: List[CapturedMCPCall] = []
        self._load_artifact(artifact_data)

        # Build lookup index
        self._cache_index: Dict[str, CapturedMCPCall] = {}
        self._build_index()

        # Track replay stats
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_matches": 0
        }

    def _load_artifact(self, artifact_data: Dict[str, Any]):
        """Load MCP calls from artifact data."""
        # Handle both old format (tool_calls with source="mcp")
        # and new format (mcp_tool_calls)

        if "mcp_tool_calls" in artifact_data:
            for call_data in artifact_data["mcp_tool_calls"]:
                self.cached_calls.append(CapturedMCPCall(**call_data))

        elif "tool_calls" in artifact_data:
            for call_data in artifact_data["tool_calls"]:
                if call_data.get("source") == "mcp":
                    self.cached_calls.append(CapturedMCPCall(**call_data))

        logger.info(f"Loaded {len(self.cached_calls)} cached MCP calls for replay")

    def _build_index(self):
        """Build cache key index for fast lookups."""
        for call in self.cached_calls:
            key = call.to_cache_key()
            self._cache_index[key] = call

    def find_cached_response(
        self,
        request: JSONRPCRequest
    ) -> Optional[JSONRPCResponse]:
        """
        Find a cached response for the given request.
        Uses exact matching first, then semantic matching.
        """
        # Build a temporary CapturedMCPCall for matching
        tool_name = None
        arguments = {}

        if request.method == "tools/call" and request.params:
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
        elif request.params:
            arguments = request.params

        # Try exact match first
        cache_key = self._compute_cache_key(request.method, tool_name, arguments)

        if cache_key in self._cache_index:
            cached = self._cache_index[cache_key]
            self.stats["cache_hits"] += 1
            logger.info(f"Cache HIT (exact): {tool_name or request.method}")
            return self._build_response(request.id, cached)

        # Try semantic matching
        if self.replay_config.semantic_threshold < 1.0:
            semantic_match = self._find_semantic_match(
                request.method, tool_name, arguments
            )
            if semantic_match:
                self.stats["semantic_matches"] += 1
                logger.info(f"Cache HIT (semantic): {tool_name or request.method}")
                return self._build_response(request.id, semantic_match)

        # Cache miss
        self.stats["cache_misses"] += 1
        logger.warning(f"Cache MISS: {tool_name or request.method}")
        return self._handle_cache_miss(request)

    def _compute_cache_key(
        self,
        method: str,
        tool_name: Optional[str],
        arguments: Dict
    ) -> str:
        """Compute cache key for a request."""
        import hashlib
        key_data = {
            "method": method,
            "tool_name": tool_name,
            "arguments": arguments
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _find_semantic_match(
        self,
        method: str,
        tool_name: Optional[str],
        arguments: Dict
    ) -> Optional[CapturedMCPCall]:
        """
        Find a semantically similar cached call.
        Uses existing Kurral semantic similarity logic.
        """
        try:
            from kurral.ars_scorer import compute_similarity  # Reuse existing
        except ImportError:
            logger.warning("Cannot import compute_similarity, semantic matching disabled")
            return None

        best_match = None
        best_score = 0.0

        for cached in self.cached_calls:
            # Must match method
            if cached.method != method:
                continue

            # Must match tool name if present
            if tool_name and cached.tool_name != tool_name:
                continue

            # Compute argument similarity
            score = compute_similarity(
                json.dumps(arguments, sort_keys=True),
                json.dumps(cached.arguments, sort_keys=True)
            )

            if score >= self.replay_config.semantic_threshold and score > best_score:
                best_match = cached
                best_score = score

        return best_match

    def _build_response(
        self,
        request_id: Any,
        cached: CapturedMCPCall
    ) -> JSONRPCResponse:
        """Build a JSON-RPC response from cached data."""
        if cached.error:
            return JSONRPCResponse(
                id=request_id,
                error=JSONRPCError(**cached.error)
            )
        return JSONRPCResponse(
            id=request_id,
            result=cached.result
        )

    def _handle_cache_miss(self, request: JSONRPCRequest) -> Optional[JSONRPCResponse]:
        """Handle a cache miss based on configuration."""
        if self.replay_config.on_cache_miss == "error":
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=-32000,
                    message="Replay cache miss: No cached response found",
                    data={
                        "method": request.method,
                        "params": request.params
                    }
                )
            )
        elif self.replay_config.on_cache_miss == "mock":
            return JSONRPCResponse(
                id=request.id,
                result=self.replay_config.mock_response or {"mocked": True}
            )
        elif self.replay_config.on_cache_miss == "passthrough":
            # Return None to signal proxy should forward to real server
            return None

        return None

    def build_sse_generator(self, cached: 'CapturedMCPCall'):
        """
        Build an async generator for replaying SSE events.

        Args:
            cached: The captured call with SSE events

        Yields:
            SSE-formatted event strings
        """
        async def replay_events():
            """Generate SSE events from cached data."""
            if cached.events:
                # Replay all captured events
                for event in cached.events:
                    event_type = event.event_type

                    # Serialize data
                    if isinstance(event.data, (dict, list)):
                        data_str = json.dumps(event.data)
                    else:
                        data_str = str(event.data)

                    # Format as SSE
                    if event_type != "message":
                        yield f"event: {event_type}\n"
                    yield f"data: {data_str}\n\n"
            else:
                # Fallback: single event with result
                if cached.result:
                    data_str = json.dumps(cached.result) if isinstance(cached.result, (dict, list)) else str(cached.result)
                    yield f"data: {data_str}\n\n"

        return replay_events()

    def get_stats(self) -> Dict[str, int]:
        """Get replay statistics."""
        return self.stats.copy()
