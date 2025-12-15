#!/usr/bin/env python3
"""
Manual SSE test runner (doesn't require pytest)
"""

import sys
sys.path.insert(0, '/tmp/kurralv3')

from kurral.mcp.models import MCPEvent, CapturedMCPCall, JSONRPCRequest
from kurral.mcp.capture import MCPCaptureEngine
from kurral.mcp.replay import MCPReplayEngine
from kurral.mcp.config import MCPConfig
from datetime import datetime


def test_mcp_event():
    """Test MCPEvent model."""
    event = MCPEvent(
        event_type="progress",
        data={"status": "processing", "percent": 50}
    )
    assert event.event_type == "progress"
    assert event.data["status"] == "processing"
    assert isinstance(event.timestamp, datetime)
    print("✓ test_mcp_event")


def test_captured_call_sse():
    """Test CapturedMCPCall with SSE."""
    event1 = MCPEvent(event_type="start", data={"status": "started"})
    event2 = MCPEvent(event_type="complete", data={"result": "done"})

    call = CapturedMCPCall(
        server="test",
        method="tools/call",
        tool_name="analyze",
        was_sse=True,
        events=[event1, event2]
    )

    assert call.was_sse is True
    assert len(call.events) == 2
    assert call.events[0].event_type == "start"
    print("✓ test_captured_call_sse")


def test_capture_events():
    """Test capturing SSE events."""
    config = MCPConfig()
    engine = MCPCaptureEngine(config)

    request = JSONRPCRequest(
        id="123",
        method="tools/call",
        params={"name": "stream_tool", "arguments": {}}
    )
    tracking_id = engine.capture_request(request, "test-server")

    # Capture events
    engine.capture_event(tracking_id, {"status": "started"}, "start")
    engine.capture_event(tracking_id, {"percent": 50}, "progress")
    engine.capture_event(tracking_id, {"result": "done"}, "complete")

    # Finalize
    captured = engine.finalize_capture(tracking_id)

    assert captured is not None
    assert captured.was_sse is True
    assert len(captured.events) == 3
    assert captured.events[0].event_type == "start"
    print("✓ test_capture_events")


def test_replay_sse():
    """Test replaying SSE events."""
    config = MCPConfig()

    events = [
        MCPEvent(event_type="start", data={"status": "started"}),
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

    assert len(engine.cached_calls) == 1
    cached = engine.cached_calls[0]
    assert cached.was_sse is True
    assert len(cached.events) == 2
    print("✓ test_replay_sse")


def test_full_workflow():
    """Test complete SSE workflow."""
    config = MCPConfig()

    # RECORD
    capture = MCPCaptureEngine(config)
    request = JSONRPCRequest(
        id="stream-123",
        method="tools/call",
        params={"name": "analyze_image", "arguments": {"url": "test.jpg"}}
    )

    tracking_id = capture.capture_request(request, "image-server")
    capture.capture_event(tracking_id, {"status": "downloading"}, "progress")
    capture.capture_event(tracking_id, {"status": "analyzing"}, "progress")
    capture.capture_event(
        tracking_id,
        {"result": {"objects": ["cat", "dog"]}},
        "complete"
    )

    captured = capture.finalize_capture(tracking_id)
    artifact = capture.export_to_kurral()

    # REPLAY
    replay = MCPReplayEngine(config, artifact)
    replay_request = JSONRPCRequest(
        id="replay-456",
        method="tools/call",
        params={"name": "analyze_image", "arguments": {"url": "test.jpg"}}
    )

    response = replay.find_cached_response(replay_request)

    assert response is not None
    assert response.id == "replay-456"
    # Result is extracted from last event's "result" field
    assert response.result == {"objects": ["cat", "dog"]}

    print("✓ test_full_workflow")


if __name__ == "__main__":
    print("Running SSE Unit Tests...\n")

    try:
        test_mcp_event()
        test_captured_call_sse()
        test_capture_events()
        test_replay_sse()
        test_full_workflow()

        print("\n" + "="*50)
        print("✅ ALL SSE TESTS PASSED! (5/5)")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
