"""
Unit tests for SSE (Server-Sent Events) functionality
"""

import pytest
from datetime import datetime
from kurral.mcp.models import MCPEvent, CapturedMCPCall, MCPSession, JSONRPCRequest
from kurral.mcp.capture import MCPCaptureEngine
from kurral.mcp.replay import MCPReplayEngine
from kurral.mcp.config import MCPConfig


class TestMCPEvent:
    """Test MCPEvent model."""

    def test_event_creation(self):
        """Test creating an MCPEvent."""
        event = MCPEvent(
            event_type="progress",
            data={"status": "processing", "percent": 50}
        )
        assert event.event_type == "progress"
        assert event.data["status"] == "processing"
        assert event.data["percent"] == 50
        assert isinstance(event.timestamp, datetime)

    def test_event_default_type(self):
        """Test default event type is 'message'."""
        event = MCPEvent(data="test")
        assert event.event_type == "message"

    def test_event_raw_text_data(self):
        """Test event with raw text data."""
        event = MCPEvent(data="plain text message")
        assert event.data == "plain text message"


class TestCapturedMCPCallSSE:
    """Test CapturedMCPCall with SSE events."""

    def test_sse_flag(self):
        """Test was_sse flag."""
        call = CapturedMCPCall(
            server="test",
            method="tools/call",
            tool_name="test",
            was_sse=True
        )
        assert call.was_sse is True

    def test_events_list(self):
        """Test events list."""
        event1 = MCPEvent(event_type="start", data={"status": "started"})
        event2 = MCPEvent(event_type="progress", data={"percent": 50})
        event3 = MCPEvent(event_type="complete", data={"result": "done"})

        call = CapturedMCPCall(
            server="test",
            method="tools/call",
            tool_name="analyze",
            was_sse=True,
            events=[event1, event2, event3]
        )

        assert len(call.events) == 3
        assert call.events[0].event_type == "start"
        assert call.events[1].data["percent"] == 50
        assert call.events[2].data["result"] == "done"

    def test_backward_compatibility(self):
        """Test that non-SSE calls still work."""
        call = CapturedMCPCall(
            server="test",
            method="tools/call",
            tool_name="test",
            result={"value": 42}
        )
        assert call.was_sse is False
        assert len(call.events) == 0
        assert call.result == {"value": 42}


class TestSSECapture:
    """Test SSE capture functionality."""

    def test_capture_event(self):
        """Test capturing individual SSE events."""
        config = MCPConfig()
        engine = MCPCaptureEngine(config)

        # Capture request first
        request = JSONRPCRequest(
            id="123",
            method="tools/call",
            params={"name": "stream_tool", "arguments": {}}
        )
        tracking_id = engine.capture_request(request, "test-server")

        # Capture events
        engine.capture_event(tracking_id, {"status": "started"}, "start")
        engine.capture_event(tracking_id, {"percent": 25}, "progress")
        engine.capture_event(tracking_id, {"percent": 50}, "progress")
        engine.capture_event(tracking_id, {"result": "done"}, "complete")

        # Finalize
        captured = engine.finalize_capture(tracking_id)

        assert captured is not None
        assert captured.was_sse is True
        assert len(captured.events) == 4
        assert captured.events[0].event_type == "start"
        assert captured.events[1].data["percent"] == 25
        assert captured.events[-1].event_type == "complete"

    def test_finalize_extracts_final_result(self):
        """Test that finalize extracts result from last event."""
        config = MCPConfig()
        engine = MCPCaptureEngine(config)

        request = JSONRPCRequest(
            id="123",
            method="tools/call",
            params={"name": "test", "arguments": {}}
        )
        tracking_id = engine.capture_request(request, "test")

        # Add events
        engine.capture_event(tracking_id, {"status": "processing"}, "progress")
        engine.capture_event(
            tracking_id,
            {"result": {"data": "final result"}},
            "complete"
        )

        captured = engine.finalize_capture(tracking_id)

        # Should extract result from last event
        assert captured.result == {"result": {"data": "final result"}}

    def test_capture_event_invalid_tracking_id(self):
        """Test capturing event with invalid tracking ID."""
        config = MCPConfig()
        engine = MCPCaptureEngine(config)

        # Should not crash, just log warning
        engine.capture_event("invalid-id", {"data": "test"}, "test")
        # No exception = pass

    def test_finalize_invalid_tracking_id(self):
        """Test finalizing with invalid tracking ID."""
        config = MCPConfig()
        engine = MCPCaptureEngine(config)

        result = engine.finalize_capture("invalid-id")
        assert result is None


class TestSSEReplay:
    """Test SSE replay functionality."""

    def test_replay_sse_events(self):
        """Test replaying SSE events."""
        config = MCPConfig()

        # Create artifact with SSE call
        events = [
            MCPEvent(event_type="start", data={"status": "started"}),
            MCPEvent(event_type="progress", data={"percent": 50}),
            MCPEvent(event_type="complete", data={"result": "done"})
        ]

        artifact_data = {
            "mcp_tool_calls": [
                {
                    "server": "test",
                    "method": "tools/call",
                    "tool_name": "stream_tool",
                    "arguments": {},
                    "result": {"result": "done"},
                    "was_sse": True,
                    "events": [e.model_dump() for e in events]
                }
            ]
        }

        engine = MCPReplayEngine(config, artifact_data)

        # Verify loaded correctly
        assert len(engine.cached_calls) == 1
        cached = engine.cached_calls[0]
        assert cached.was_sse is True
        assert len(cached.events) == 3

    def test_build_sse_generator(self):
        """Test building SSE generator for replay."""
        config = MCPConfig()
        events = [
            MCPEvent(event_type="progress", data={"percent": 50}),
            MCPEvent(event_type="complete", data={"result": "done"})
        ]

        cached_call = CapturedMCPCall(
            server="test",
            method="tools/call",
            tool_name="test",
            was_sse=True,
            events=events,
            result={"result": "done"}
        )

        engine = MCPReplayEngine(config, {"mcp_tool_calls": []})
        generator = engine.build_sse_generator(cached_call)

        # This returns an async generator
        import asyncio

        async def collect_events():
            results = []
            async for event_str in generator:
                results.append(event_str)
            return results

        results = asyncio.run(collect_events())

        # Should have 2 events
        assert len(results) == 2
        assert "event: progress" in results[0]
        assert '{"percent": 50}' in results[0]
        assert "event: complete" in results[1]

    def test_replay_fallback_no_events(self):
        """Test replay fallback when no events recorded."""
        config = MCPConfig()
        cached_call = CapturedMCPCall(
            server="test",
            method="tools/call",
            tool_name="test",
            was_sse=False,
            result={"value": 42}
        )

        engine = MCPReplayEngine(config, {"mcp_tool_calls": []})
        generator = engine.build_sse_generator(cached_call)

        import asyncio

        async def collect_events():
            results = []
            async for event_str in generator:
                results.append(event_str)
            return results

        results = asyncio.run(collect_events())

        # Should have 1 fallback event with result
        assert len(results) == 1
        assert '{"value": 42}' in results[0]


class TestSSEIntegration:
    """Integration tests for SSE workflow."""

    def test_full_sse_workflow(self):
        """Test complete SSE capture and replay workflow."""
        config = MCPConfig()

        # === RECORD MODE ===
        capture = MCPCaptureEngine(config)

        # Simulate SSE stream
        request = JSONRPCRequest(
            id="stream-123",
            method="tools/call",
            params={"name": "analyze_image", "arguments": {"url": "test.jpg"}}
        )

        tracking_id = capture.capture_request(request, "image-server")

        # Simulate streaming events
        capture.capture_event(tracking_id, {"status": "downloading"}, "progress")
        capture.capture_event(tracking_id, {"status": "analyzing"}, "progress")
        capture.capture_event(
            tracking_id,
            {"result": {"objects": ["cat", "dog"]}},
            "complete"
        )

        # Finalize
        captured = capture.finalize_capture(tracking_id)

        # Export
        artifact = capture.export_to_kurral()

        # === REPLAY MODE ===
        replay = MCPReplayEngine(config, artifact)

        # Same request
        replay_request = JSONRPCRequest(
            id="replay-456",
            method="tools/call",
            params={"name": "analyze_image", "arguments": {"url": "test.jpg"}}
        )

        # Find cached
        response = replay.find_cached_response(replay_request)

        # Verify
        assert response is not None
        assert response.id == "replay-456"
        assert response.result == {"result": {"objects": ["cat", "dog"]}}

        # Get cached call for SSE replay
        cache_key = replay._compute_cache_key(
            "tools/call",
            "analyze_image",
            {"url": "test.jpg"}
        )
        cached_call = replay._cache_index[cache_key]

        assert cached_call.was_sse is True
        assert len(cached_call.events) == 3
        assert cached_call.events[0].data["status"] == "downloading"
        assert cached_call.events[2].data["result"]["objects"] == ["cat", "dog"]

        print("✅ Full SSE workflow test passed!")


if __name__ == "__main__":
    # Run tests
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
