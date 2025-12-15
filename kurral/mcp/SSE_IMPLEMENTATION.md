# SSE (Server-Sent Events) Implementation

## Overview

The Kurral MCP Proxy now fully supports Server-Sent Events (SSE) streaming for both **record** and **replay** modes.

---

## Architecture

### Record Mode: Full Stream Capture

```
Agent → Proxy → MCP Server (SSE stream)
         ↓
    Captures ALL events
         ↓
    .kurral artifact
```

**How it works:**
1. Agent sends request to proxy
2. Proxy forwards to real MCP server
3. MCP server responds with SSE stream
4. Proxy captures **each event** as it streams
5. Proxy forwards events to agent in real-time
6. After stream ends, finalizes capture with all events

### Replay Mode: Stream Reconstruction

```
Agent → Proxy (replay)
         ↓
    Reads cached events
         ↓
    Streams back to agent (SSE format)
```

**How it works:**
1. Agent sends request to proxy
2. Proxy finds cached call in artifact
3. If `was_sse == true`, returns SSE stream
4. Replays all captured events in order
5. Agent receives identical stream as original

---

## Key Components

### 1. **MCPEvent Model** (`models.py`)

```python
class MCPEvent(BaseModel):
    event_type: str = "message"  # SSE event type
    data: Any  # Event payload (JSON or raw string)
    timestamp: datetime
```

Represents a single SSE event.

### 2. **CapturedMCPCall Updates** (`models.py`)

```python
class CapturedMCPCall(BaseModel):
    # ... existing fields ...

    # SSE-specific fields
    was_sse: bool = False  # Indicates this was SSE
    events: List[MCPEvent] = []  # All captured events

    # Legacy fields (still populated from last event)
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
```

**Backward compatibility:** Non-SSE calls work exactly as before.

### 3. **Capture Engine Methods** (`capture.py`)

#### `capture_event(tracking_id, event_data, event_type)`

Called for **each SSE event** as it streams:

```python
self.capture_engine.capture_event(
    tracking_id="123",
    event_data={"status": "processing"},
    event_type="progress"
)
```

- Appends event to pending call's event list
- Marks call as `was_sse = True`
- Logs each event

#### `finalize_capture(tracking_id)`

Called **after SSE stream completes**:

```python
self.capture_engine.finalize_capture(tracking_id="123")
```

- Calculates total duration
- Extracts final result from last event
- Creates `CapturedMCPCall` with all events
- Adds to session

### 4. **Proxy SSE Handler** (`proxy.py`)

```python
async def _handle_sse_response(
    self, upstream_response, request, tracking_id
) -> StreamingResponse:
    async def event_generator():
        buffer = ""

        try:
            # Stream from upstream
            async for chunk in upstream_response.aiter_text():
                buffer += chunk

                # Parse SSE events
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)

                    # Extract event type and data
                    data_payload = parse_event(event_block)

                    # CAPTURE each event
                    if tracking_id:
                        self.capture_engine.capture_event(
                            tracking_id, data_payload, event_type
                        )

                    # FORWARD to client
                    yield f"{event_block}\n\n"

        finally:
            # FINALIZE after stream ends
            if tracking_id:
                self.capture_engine.finalize_capture(tracking_id)

    return StreamingResponse(event_generator(), ...)
```

**Key features:**
- ✅ Captures ALL events (not just first/last)
- ✅ Parses both `event:` and `data:` lines
- ✅ Handles JSON and raw text data
- ✅ Error handling with try/finally
- ✅ Forwards stream in real-time

### 5. **Replay Engine** (`replay.py`)

#### `build_sse_generator(cached_call)`

Reconstructs SSE stream for replay:

```python
async def replay_events():
    for event in cached.events:
        event_type = event.event_type
        data_str = json.dumps(event.data)

        if event_type != "message":
            yield f"event: {event_type}\n"
        yield f"data: {data_str}\n\n"
```

#### Proxy Replay Handler

```python
if cached_call.was_sse and cached_call.events:
    # Return SSE stream
    return StreamingResponse(
        self.replay_engine.build_sse_generator(cached_call),
        media_type="text/event-stream"
    )
else:
    # Return regular JSON
    return Response(cached_response, ...)
```

---

## Example SSE Flow

### Recording Session

**Agent sends:**
```json
{"jsonrpc": "2.0", "id": "1", "method": "tools/call",
 "params": {"name": "analyze_image", "arguments": {"url": "..."}}}
```

**MCP Server streams:**
```
event: progress
data: {"status": "downloading", "percent": 0}

event: progress
data: {"status": "processing", "percent": 50}

event: complete
data: {"result": {"objects": ["cat", "dog"]}}
```

**Captured in artifact:**
```json
{
  "id": "...",
  "method": "tools/call",
  "tool_name": "analyze_image",
  "was_sse": true,
  "events": [
    {
      "event_type": "progress",
      "data": {"status": "downloading", "percent": 0},
      "timestamp": "2025-01-15T10:00:00"
    },
    {
      "event_type": "progress",
      "data": {"status": "processing", "percent": 50},
      "timestamp": "2025-01-15T10:00:05"
    },
    {
      "event_type": "complete",
      "data": {"result": {"objects": ["cat", "dog"]}},
      "timestamp": "2025-01-15T10:00:10"
    }
  ],
  "result": {"result": {"objects": ["cat", "dog"]}},
  "duration_ms": 10000
}
```

### Replay Session

**Agent sends same request**

**Proxy replays SSE stream:**
```
event: progress
data: {"status": "downloading", "percent": 0}

event: progress
data: {"status": "processing", "percent": 50}

event: complete
data: {"result": {"objects": ["cat", "dog"]}}
```

**Agent receives identical stream!**

---

## Benefits

### ✅ Complete Observability
- Every intermediate event is captured
- Full timeline of streaming responses
- Debug multi-step tool executions

### ✅ Perfect Replay Fidelity
- Replays exactly as recorded
- Maintains event order and types
- Agent experiences identical stream

### ✅ Progress Tracking
- Capture progress updates
- Monitor long-running operations
- Analyze performance over time

### ✅ Backward Compatible
- Non-SSE calls work as before
- Existing artifacts still load
- `result` field populated from last event

---

## Testing SSE

### Manual Test with Mock Server

1. **Start mock MCP server that returns SSE:**
```python
# mock_sse_server.py
@app.post("/mcp")
async def handle():
    async def generate():
        yield "event: start\ndata: {\"status\": \"started\"}\n\n"
        await asyncio.sleep(1)
        yield "event: progress\ndata: {\"percent\": 50}\n\n"
        await asyncio.sleep(1)
        yield "event: complete\ndata: {\"result\": \"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

2. **Start proxy in record mode:**
```bash
kurral mcp start --mode record
```

3. **Send request through proxy**

4. **Export and inspect:**
```bash
kurral mcp export -o captured.json
cat captured.json | jq '.mcp_tool_calls[0].events'
```

5. **Test replay:**
```bash
kurral mcp start --mode replay --artifact captured.json
```

---

## Limitations & Future Work

### Current Limitations
- No support for SSE `id:` field (for resumable streams)
- No support for SSE `retry:` field
- Comment lines (`:`) are forwarded but not captured

### Potential Enhancements
- Add timing delays in replay (match original timing)
- Support SSE reconnection
- Capture SSE comments
- Add event filtering (only capture certain event types)

---

## Implementation Credits

This SSE implementation was collaboratively designed to ensure:
- Full stream capture (not just first/last event)
- Proper event type handling
- Try/finally finalization pattern
- Seamless replay with format preservation

The architecture supports both simple single-response tools and complex streaming operations with multiple intermediate events.
