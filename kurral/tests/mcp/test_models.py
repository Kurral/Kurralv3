"""
Unit tests for MCP models
"""

import pytest
from datetime import datetime
from kurral.mcp.models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    ToolCallParams,
    CapturedMCPCall,
    MCPSession
)


def test_jsonrpc_request():
    """Test JSONRPCRequest model."""
    request = JSONRPCRequest(
        id="123",
        method="tools/call",
        params={"name": "test", "arguments": {}}
    )
    assert request.jsonrpc == "2.0"
    assert request.id == "123"
    assert request.method == "tools/call"


def test_jsonrpc_response_success():
    """Test JSONRPCResponse with successful result."""
    response = JSONRPCResponse(
        id="123",
        result={"content": [{"type": "text", "text": "success"}]}
    )
    assert response.jsonrpc == "2.0"
    assert response.id == "123"
    assert response.result is not None
    assert response.error is None


def test_jsonrpc_response_error():
    """Test JSONRPCResponse with error."""
    error = JSONRPCError(code=-32000, message="Test error")
    response = JSONRPCResponse(
        id="123",
        error=error
    )
    assert response.error is not None
    assert response.error.code == -32000
    assert response.result is None


def test_tool_call_params():
    """Test ToolCallParams model."""
    params = ToolCallParams(
        name="calculator",
        arguments={"a": 5, "b": 3}
    )
    assert params.name == "calculator"
    assert params.arguments == {"a": 5, "b": 3}


def test_captured_mcp_call():
    """Test CapturedMCPCall model."""
    call = CapturedMCPCall(
        server="test-server",
        method="tools/call",
        tool_name="calculator",
        arguments={"a": 5, "b": 3},
        result={"value": 8}
    )
    assert call.source == "mcp"
    assert call.server == "test-server"
    assert call.tool_name == "calculator"
    assert call.result == {"value": 8}
    assert call.error is None


def test_captured_mcp_call_cache_key():
    """Test cache key generation."""
    call1 = CapturedMCPCall(
        server="test",
        method="tools/call",
        tool_name="calculator",
        arguments={"a": 5, "b": 3}
    )
    call2 = CapturedMCPCall(
        server="test",
        method="tools/call",
        tool_name="calculator",
        arguments={"a": 5, "b": 3}
    )
    # Same arguments should generate same cache key
    assert call1.to_cache_key() == call2.to_cache_key()

    call3 = CapturedMCPCall(
        server="test",
        method="tools/call",
        tool_name="calculator",
        arguments={"a": 10, "b": 3}
    )
    # Different arguments should generate different cache key
    assert call1.to_cache_key() != call3.to_cache_key()


def test_mcp_session():
    """Test MCPSession model."""
    session = MCPSession()
    assert len(session.calls) == 0
    assert len(session.servers_used) == 0

    # Add a call
    call = CapturedMCPCall(
        server="server1",
        method="tools/call",
        tool_name="test"
    )
    session.add_call(call)

    assert len(session.calls) == 1
    assert "server1" in session.servers_used


def test_mcp_session_to_kurral_format():
    """Test MCPSession export to .kurral format."""
    session = MCPSession()
    call = CapturedMCPCall(
        server="test-server",
        method="tools/call",
        tool_name="calculator",
        arguments={"a": 5},
        result={"value": 5}
    )
    session.add_call(call)

    export = session.to_kurral_format()
    assert "mcp_session_id" in export
    assert "mcp_servers_used" in export
    assert "mcp_tool_calls" in export
    assert len(export["mcp_tool_calls"]) == 1
    assert export["mcp_servers_used"] == ["test-server"]
