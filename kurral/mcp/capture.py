"""
MCP Capture Engine

Captures MCP requests and responses for Kurral artifacts.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import time
import logging

from kurral.mcp.models import (
    JSONRPCRequest,
    JSONRPCResponse,
    CapturedMCPCall,
    MCPSession,
    ToolCallParams,
    MCPEvent,
    PerformanceMetrics
)
from kurral.mcp.config import MCPConfig

logger = logging.getLogger("kurral.mcp.capture")


class MCPCaptureEngine:
    """
    Captures MCP requests and responses for Kurral artifacts.
    """

    def __init__(self, config: MCPConfig):
        self.config = config
        self.session = MCPSession()
        self._pending_calls: Dict[str, dict] = {}  # request_id -> start_time, request_data

    def should_capture(self, method: str, tool_name: Optional[str] = None) -> bool:
        """Determine if this call should be captured."""
        # Check method whitelist
        if method not in self.config.capture.include_methods:
            return False

        # Check tool blacklist
        if tool_name and tool_name in self.config.capture.exclude_tools:
            return False

        return True

    def _calculate_metrics(
        self,
        start_time: float,
        events: list,
        duration_ms: int,
        first_event_time: Optional[float] = None
    ) -> PerformanceMetrics:
        """Calculate performance metrics for a captured call."""
        event_count = len(events)

        # Calculate time to first event (for SSE streams)
        time_to_first_event_ms = None
        if first_event_time is not None:
            time_to_first_event_ms = int((first_event_time - start_time) * 1000)

        # Calculate events per second (for SSE streams)
        events_per_second = None
        if event_count > 1 and duration_ms > 0:
            events_per_second = round((event_count / duration_ms) * 1000, 2)

        return PerformanceMetrics(
            total_duration_ms=duration_ms,
            time_to_first_event_ms=time_to_first_event_ms,
            event_count=event_count,
            events_per_second=events_per_second
        )

    def capture_request(
        self,
        request: JSONRPCRequest,
        server: str
    ) -> Optional[str]:
        """
        Capture an incoming MCP request.
        Returns a tracking ID for correlating with response.
        """
        # Extract tool name if this is a tools/call
        tool_name = None
        arguments = {}

        if request.method == "tools/call" and request.params:
            tool_params = ToolCallParams(**request.params)
            tool_name = tool_params.name
            arguments = tool_params.arguments
        elif request.params:
            arguments = request.params

        # Check if we should capture this
        if not self.should_capture(request.method, tool_name):
            logger.debug(f"Skipping capture for {request.method}")
            return None

        # Store pending call
        tracking_id = str(request.id)
        self._pending_calls[tracking_id] = {
            "start_time": time.time(),
            "server": server,
            "method": request.method,
            "tool_name": tool_name,
            "arguments": arguments,
            "request_id": str(request.id)
        }

        logger.debug(f"Capturing request: {request.method} / {tool_name}")
        return tracking_id

    def capture_response(
        self,
        tracking_id: str,
        response: JSONRPCResponse
    ) -> Optional[CapturedMCPCall]:
        """
        Capture the response for a previously tracked request.
        Returns the complete captured call.
        """
        if tracking_id not in self._pending_calls:
            logger.warning(f"No pending call found for tracking_id: {tracking_id}")
            return None

        pending = self._pending_calls.pop(tracking_id)
        duration_ms = int((time.time() - pending["start_time"]) * 1000)

        # Calculate metrics (non-SSE call, no events)
        metrics = self._calculate_metrics(
            start_time=pending["start_time"],
            events=[],
            duration_ms=duration_ms
        )

        # Build captured call
        captured = CapturedMCPCall(
            timestamp=datetime.utcnow(),
            source="mcp",
            server=pending["server"],
            method=pending["method"],
            tool_name=pending["tool_name"],
            arguments=pending["arguments"],
            result=response.result if not response.error else None,
            error=response.error.model_dump() if response.error else None,
            duration_ms=duration_ms,
            request_id=pending["request_id"],
            metrics=metrics
        )

        # Add to session
        self.session.add_call(captured)

        logger.info(
            f"Captured MCP call: {captured.tool_name or captured.method} "
            f"({duration_ms}ms) -> {'error' if captured.error else 'success'}"
        )

        return captured

    def capture_event(
        self,
        tracking_id: str,
        event_data: Any,
        event_type: str = "message"
    ) -> None:
        """
        Capture a single SSE event for a pending call.
        Used for streaming responses.

        Args:
            tracking_id: The tracking ID from capture_request
            event_data: The parsed event data (JSON or raw string)
            event_type: The SSE event type (default: "message")
        """
        if tracking_id not in self._pending_calls:
            logger.warning(f"No pending call found for tracking_id: {tracking_id}")
            return

        pending = self._pending_calls[tracking_id]

        # Initialize events list if not exists
        if "events" not in pending:
            pending["events"] = []
            pending["was_sse"] = True
            # Capture time to first event
            pending["first_event_time"] = time.time()

        # Check event count limit (v0.3.1)
        current_count = len(pending["events"])
        if current_count >= self.config.capture.max_events_per_call:
            logger.error(
                f"Event limit exceeded for {pending.get('tool_name', pending['method'])} "
                f"({current_count}/{self.config.capture.max_events_per_call}), dropping event"
            )
            return

        # Check event size limit (v0.3.1)
        import json
        event_size_kb = len(json.dumps(event_data).encode()) / 1024
        if event_size_kb > self.config.capture.max_event_size_kb:
            logger.warning(
                f"Event too large for {pending.get('tool_name', pending['method'])} "
                f"({event_size_kb:.1f}KB > {self.config.capture.max_event_size_kb}KB), truncating"
            )
            event_data = {
                "truncated": True,
                "original_size_kb": round(event_size_kb, 1),
                "reason": "Event exceeded max_event_size_kb limit"
            }

        # Warn if approaching limit
        if current_count == self.config.capture.warn_threshold:
            logger.warning(
                f"Event count warning for {pending.get('tool_name', pending['method'])}: "
                f"{current_count} events captured (limit: {self.config.capture.max_events_per_call})"
            )

        # Append this event
        event = MCPEvent(
            event_type=event_type,
            data=event_data,
            timestamp=datetime.utcnow()
        )
        pending["events"].append(event)

        logger.debug(f"Captured SSE event ({event_type}) for {pending.get('tool_name', pending['method'])}")

    def finalize_capture(self, tracking_id: str) -> Optional[CapturedMCPCall]:
        """
        Finalize capture for a streaming SSE call.
        Should be called after the SSE stream completes.

        Args:
            tracking_id: The tracking ID from capture_request

        Returns:
            The complete captured call
        """
        if tracking_id not in self._pending_calls:
            logger.warning(f"No pending call found for tracking_id: {tracking_id}")
            return None

        pending = self._pending_calls.pop(tracking_id)
        duration_ms = int((time.time() - pending["start_time"]) * 1000)

        # Extract final result from last event (if SSE)
        result = None
        error = None
        events = pending.get("events", [])

        if events:
            # Use last event's data as final result
            last_event = events[-1]
            if isinstance(last_event.data, dict):
                # Check if it's a JSON-RPC response
                if "result" in last_event.data:
                    result = last_event.data["result"]
                elif "error" in last_event.data:
                    error = last_event.data["error"]
                else:
                    result = last_event.data
            else:
                result = last_event.data

        # Calculate metrics (SSE call with events)
        metrics = self._calculate_metrics(
            start_time=pending["start_time"],
            events=events,
            duration_ms=duration_ms,
            first_event_time=pending.get("first_event_time")
        )

        # Build captured call
        captured = CapturedMCPCall(
            timestamp=datetime.utcnow(),
            source="mcp",
            server=pending["server"],
            method=pending["method"],
            tool_name=pending["tool_name"],
            arguments=pending["arguments"],
            result=result,
            error=error,
            was_sse=pending.get("was_sse", False),
            events=events,
            duration_ms=duration_ms,
            request_id=pending["request_id"],
            metrics=metrics
        )

        # Add to session
        self.session.add_call(captured)

        logger.info(
            f"Finalized MCP call: {captured.tool_name or captured.method} "
            f"({duration_ms}ms, {len(events)} events) -> {'error' if captured.error else 'success'}"
        )

        return captured

    def get_session(self) -> MCPSession:
        """Get the current capture session."""
        return self.session

    def export_to_kurral(self) -> Dict[str, Any]:
        """Export captured calls in .kurral format."""
        self.session.ended_at = datetime.utcnow()
        return self.session.to_kurral_format()

    def reset(self):
        """Reset for a new capture session."""
        self.session = MCPSession()
        self._pending_calls.clear()
