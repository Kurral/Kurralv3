"""
MCP Protocol Models

Pydantic models for MCP JSON-RPC messages and captured data.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid
import hashlib
import json


class JSONRPCRequest(BaseModel):
    """Incoming MCP request."""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC error object."""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """Outgoing MCP response."""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


class ToolCallParams(BaseModel):
    """Parameters for tools/call method."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPEvent(BaseModel):
    """A single SSE event from an MCP server."""
    event_type: str = "message"  # SSE event type
    data: Any  # Event payload (parsed JSON or raw string)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PerformanceMetrics(BaseModel):
    """Performance metrics for tool execution."""
    total_duration_ms: int  # Total time from request to response
    time_to_first_event_ms: Optional[int] = None  # Time until first SSE event (SSE only)
    event_count: int = 0  # Number of SSE events (0 for non-SSE)
    events_per_second: Optional[float] = None  # Event rate for SSE streams


class CapturedMCPCall(BaseModel):
    """
    A single captured MCP tool call.
    This is what gets stored in the .kurral artifact.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Source identification
    source: str = "mcp"
    server: str  # Which MCP server handled this

    # Request details
    method: str  # e.g., "tools/call"
    tool_name: Optional[str] = None  # For tools/call, the actual tool
    arguments: Dict[str, Any] = Field(default_factory=dict)

    # Response details (single response - non-SSE or final SSE result)
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    # SSE streaming details
    was_sse: bool = False  # True if this was a streaming SSE response
    events: List[MCPEvent] = Field(default_factory=list)  # All SSE events captured

    # Metadata
    duration_ms: Optional[int] = None
    request_id: Optional[str] = None  # Original JSON-RPC request ID
    metrics: Optional[PerformanceMetrics] = None  # Performance metrics

    def to_cache_key(self) -> str:
        """Generate a cache key for replay matching."""
        key_data = {
            "method": self.method,
            "tool_name": self.tool_name,
            "arguments": self.arguments
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]


class MCPSession(BaseModel):
    """
    A complete MCP capture session.
    Contains all captured calls for one agent run.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    # All captured calls
    calls: List[CapturedMCPCall] = Field(default_factory=list)

    # Server discovery
    servers_used: List[str] = Field(default_factory=list)
    tools_discovered: Dict[str, List[str]] = Field(default_factory=dict)  # server -> [tools]

    def add_call(self, call: CapturedMCPCall):
        """Add a captured call to the session."""
        self.calls.append(call)
        if call.server not in self.servers_used:
            self.servers_used.append(call.server)

    def to_kurral_format(self) -> Dict[str, Any]:
        """
        Export in format compatible with existing .kurral artifacts.
        This gets merged into the main artifact's tool_calls array.
        """
        return {
            "mcp_session_id": self.session_id,
            "mcp_servers_used": self.servers_used,
            "mcp_tool_calls": [call.model_dump() for call in self.calls]
        }
