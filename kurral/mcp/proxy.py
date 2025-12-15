"""
Kurral MCP Proxy Server

Main proxy server that intercepts all MCP traffic, captures for artifacts, and enables replay.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from fastapi import Response
    from fastapi.responses import StreamingResponse
    import httpx

try:
    import httpx
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import StreamingResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Define placeholder types for when FastAPI is not installed
    Response = None  # type: ignore
    StreamingResponse = None  # type: ignore

from kurral.mcp.config import MCPConfig
from kurral.mcp.models import JSONRPCRequest, JSONRPCResponse, JSONRPCError
from kurral.mcp.capture import MCPCaptureEngine
from kurral.mcp.router import MCPRouter
from kurral.mcp.replay import MCPReplayEngine

logger = logging.getLogger("kurral.mcp.proxy")


class KurralMCPProxy:
    """
    Main MCP proxy server.
    Intercepts all MCP traffic, captures for artifacts, enables replay.
    """

    def __init__(self, config: MCPConfig):
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI dependencies not installed. "
                "Install with: pip install kurral[mcp]"
            )

        self.config = config
        self.app = FastAPI(title="Kurral MCP Proxy")

        # Initialize concurrency control (v0.3.1)
        self._semaphore = asyncio.Semaphore(config.proxy.max_concurrent_requests)

        # Initialize components
        self.router = MCPRouter(config)
        self.capture_engine = MCPCaptureEngine(config)
        self.replay_engine: Optional[MCPReplayEngine] = None

        # Load replay artifact if in replay mode
        if config.mode == "replay" and config.artifact_path:
            self._load_replay_artifact(config.artifact_path)

        # Setup routes
        self._setup_routes()

    def _load_replay_artifact(self, artifact_path: str):
        """Load artifact for replay mode."""
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        with open(path) as f:
            artifact_data = json.load(f)

        self.replay_engine = MCPReplayEngine(self.config, artifact_data)
        logger.info(f"Loaded replay artifact: {artifact_path}")

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.post("/mcp")
        @self.app.post("/sse")
        @self.app.post("/")
        async def handle_mcp_request(request: Request):
            """Main MCP endpoint - handles all MCP traffic."""
            # Apply concurrency limit (v0.3.1)
            async with self._semaphore:
                try:
                    # Apply request timeout (v0.3.1)
                    async with asyncio.timeout(self.config.proxy.request_timeout_seconds):
                        return await self._process_request(request)
                except asyncio.TimeoutError:
                    return Response(
                        content=json.dumps({
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32000,
                                "message": f"Request timeout after {self.config.proxy.request_timeout_seconds}s"
                            }
                        }),
                        media_type="application/json"
                    )

        async def _process_request(self, request: Request):
            """Process a single MCP request (extracted for timeout handling)."""
            try:
                body = await request.json()
            except json.JSONDecodeError as e:
                return Response(
                    content=json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": str(e)
                        }
                    }),
                    media_type="application/json"
                )

            # Parse JSON-RPC request
            try:
                rpc_request = JSONRPCRequest(**body)
            except Exception as e:
                return Response(
                    content=json.dumps({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                            "data": str(e)
                        }
                    }),
                    media_type="application/json"
                )

            # Handle based on mode
            if self.config.mode == "replay":
                return await self._handle_replay(rpc_request)
            else:
                return await self._handle_record(rpc_request)

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "mode": self.config.mode}

        @self.app.get("/stats")
        async def get_stats():
            stats = {
                "mode": self.config.mode,
                "captured_calls": len(self.capture_engine.session.calls)
            }
            if self.replay_engine:
                stats["replay_stats"] = self.replay_engine.get_stats()
            return stats

        @self.app.post("/export")
        async def export_artifact():
            """Export captured calls as .kurral format."""
            return self.capture_engine.export_to_kurral()

    async def _handle_record(self, request: JSONRPCRequest) -> Response:
        """Handle request in record mode: forward and capture."""

        # Route to correct upstream server
        server_config = self.router.route(request)
        server_name = self.router.get_server_name(request)

        if not server_config:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32001,
                        "message": f"No upstream server found for request"
                    }
                }),
                media_type="application/json"
            )

        # Capture request
        tracking_id = self.capture_engine.capture_request(request, server_name)

        try:
            # Forward to upstream
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    server_config.url,
                    json=request.model_dump(),
                    headers=server_config.headers,
                    timeout=server_config.timeout
                )

                # Check if SSE response
                content_type = response.headers.get("content-type", "")

                if "text/event-stream" in content_type:
                    # Handle SSE streaming response
                    return await self._handle_sse_response(
                        response, request, tracking_id
                    )
                else:
                    # Handle regular JSON response
                    response_data = response.json()
                    rpc_response = JSONRPCResponse(**response_data)

                    # Capture response
                    if tracking_id:
                        self.capture_engine.capture_response(tracking_id, rpc_response)

                    return Response(
                        content=json.dumps(response_data),
                        media_type="application/json"
                    )

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            error_response = JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(code=-32603, message=str(e), data=None)
            )
            if tracking_id:
                self.capture_engine.capture_response(tracking_id, error_response)
            return Response(
                content=error_response.model_dump_json(),
                media_type="application/json"
            )

    async def _handle_sse_response(
        self,
        upstream_response: 'httpx.Response',
        request: JSONRPCRequest,
        tracking_id: Optional[str]
    ) -> StreamingResponse:
        """Handle Server-Sent Events response from upstream, capturing the full stream."""

        async def event_generator():
            buffer = ""

            # Use a try/finally to ensure the capture is closed when the stream ends
            try:
                # Iterate over the upstream text stream
                async for chunk in upstream_response.aiter_text():
                    buffer += chunk

                    # Process all complete SSE blocks in the buffer
                    while "\n\n" in buffer:
                        event_block, buffer = buffer.split("\n\n", 1)

                        data_payload = None
                        event_type = "message"

                        # Parse the block to identify data and type
                        for line in event_block.split("\n"):
                            if line.startswith("event: "):
                                event_type = line[7:].strip()
                            if line.startswith("data: "):
                                # Attempt to parse as JSON for the capture engine
                                try:
                                    data_payload = json.loads(line[6:])
                                except json.JSONDecodeError:
                                    # Fallback for raw text data events
                                    data_payload = line[6:]

                        # --- 1. CAPTURE LOGIC (Inside the loop) ---
                        if tracking_id and data_payload is not None:
                            # CAPTURE: Send this individual event to the engine
                            self.capture_engine.capture_event(
                                tracking_id,
                                event_data=data_payload,
                                event_type=event_type
                            )

                        # --- 2. FORWARDING LOGIC ---
                        # Forward the full event block exactly as received
                        yield f"{event_block}\n\n"

            except Exception as e:
                # Log the error and potentially send an error event to the client
                logger.error(f"Stream error encountered: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': -32000})}\n\n"

            finally:
                # --- 3. FINALIZATION LOGIC (After the loop) ---
                # Finalize the capture session (calculates duration, saves to session)
                if tracking_id:
                    self.capture_engine.finalize_capture(tracking_id)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

    async def _handle_replay(self, request: JSONRPCRequest) -> Response:
        """Handle request in replay mode: return cached response."""

        if not self.replay_engine:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32002,
                        "message": "Replay mode but no artifact loaded"
                    }
                }),
                media_type="application/json"
            )

        # Try to find cached call
        # First, compute cache key to find the cached call
        tool_name = None
        arguments = {}
        if request.method == "tools/call" and request.params:
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
        elif request.params:
            arguments = request.params

        cache_key = self.replay_engine._compute_cache_key(request.method, tool_name, arguments)
        cached_call = self.replay_engine._cache_index.get(cache_key)

        # If not exact match, try semantic
        if not cached_call and self.replay_engine.replay_config.semantic_threshold < 1.0:
            cached_call = self.replay_engine._find_semantic_match(request.method, tool_name, arguments)

        if cached_call:
            # Check if this was an SSE stream
            if cached_call.was_sse and cached_call.events:
                # Return SSE stream
                return StreamingResponse(
                    self.replay_engine.build_sse_generator(cached_call),
                    media_type="text/event-stream"
                )
            else:
                # Return regular JSON response
                cached_response = self.replay_engine._build_response(request.id, cached_call)
                return Response(
                    content=cached_response.model_dump_json(),
                    media_type="application/json"
                )

        # Handle cache miss with passthrough if configured
        if self.config.replay.on_cache_miss == "passthrough":
            return await self._handle_record(request)

        # Return error for cache miss
        return Response(
            content=json.dumps({
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32000,
                    "message": "No cached response found for replay"
                }
            }),
            media_type="application/json"
        )

    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """Run the proxy server."""
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "uvicorn not installed. "
                "Install with: pip install kurral[mcp]"
            )

        host = host or self.config.proxy.host
        port = port or self.config.proxy.port

        # Security warning for 0.0.0.0 binding (v0.3.1)
        if host == "0.0.0.0":
            logger.warning(
                "⚠️  SECURITY WARNING: Proxy listening on all interfaces (0.0.0.0)! "
                "This exposes your MCP server URLs and API keys to your network. "
                "Use 127.0.0.1 for local development."
            )

        logger.info(f"Starting Kurral MCP Proxy on {host}:{port} (mode: {self.config.mode})")
        uvicorn.run(self.app, host=host, port=port)


def create_proxy(config_path: str = "kurral-mcp.yaml") -> KurralMCPProxy:
    """Factory function to create a proxy from config file."""
    config = MCPConfig.load(config_path)
    return KurralMCPProxy(config)
