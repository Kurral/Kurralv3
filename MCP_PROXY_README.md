# Kurral MCP Proxy

**HTTP/SSE Proxy for Model Context Protocol** - Capture, replay, and observe all MCP tool calls with full streaming support.

---

## 🎯 Overview

The Kurral MCP Proxy sits transparently between AI agents and MCP servers, providing complete observability and deterministic replay capabilities. It captures every tool call with full request/response data, including Server-Sent Events (SSE) streams.

### Key Features

- ✅ **Record Mode** - Capture all MCP traffic to `.kurral` artifacts
- ✅ **Replay Mode** - Return cached responses for deterministic testing
- ✅ **SSE Streaming** - Full event-by-event capture and replay
- ✅ **Performance Metrics** - Duration, event rates, time-to-first-event
- ✅ **Multi-Server Routing** - Route different tools to different servers
- ✅ **Semantic Matching** - Fuzzy argument matching for flexible replay
- ✅ **Zero Latency** - Async streaming passthrough with no overhead

---

## 📦 Installation

### Install MCP Dependencies

The MCP proxy requires optional dependencies (not included in core Kurral):

```bash
# Install Kurral with MCP support
pip install kurral[mcp]

# Or install manually
pip install fastapi uvicorn httpx sse-starlette
```

### Verify Installation

```bash
kurral mcp --help
```

---

## 🚀 Quick Start

### 1. Initialize Configuration

```bash
kurral mcp init
```

This creates `kurral-mcp.yaml`:

```yaml
servers:
  - name: main_server
    url: http://localhost:8000/mcp
    tools: ["*"]  # All tools

proxy:
  host: 0.0.0.0
  port: 3100

replay:
  semantic_threshold: 0.8
  on_cache_miss: error
```

### 2. Record a Session

```bash
# Start proxy in record mode
kurral mcp start --config kurral-mcp.yaml --mode record

# Configure your AI agent to use the proxy
# Agent URL: http://localhost:3100

# Agent makes calls → Proxy captures → Forwards to server
```

### 3. Export Captured Calls

```bash
# Export to .kurral artifact
kurral mcp export --host localhost --port 3100 -o session.json

# Preview the artifact
cat session.json | python -m json.tool | head -50
```

### 4. Replay from Artifact

```bash
# Start proxy in replay mode
kurral mcp start --mode replay --artifact session.json

# Agent makes same calls → Proxy returns cached responses
# No need for live MCP server!
```

---

## 📖 Use Cases

### Development & Debugging

```bash
# Record during development
kurral mcp start --mode record &
# Run your agent
python agent.py
# Export session
kurral mcp export -o dev-session.json

# Share artifact with team for debugging
```

### Testing & CI/CD

```bash
# Record golden path once
kurral mcp start --mode record
# Run test suite (hits real APIs)
pytest tests/
kurral mcp export -o golden.json

# All future tests use replay (fast, deterministic)
kurral mcp start --mode replay --artifact golden.json
pytest tests/  # No external dependencies!
```

### Production Debugging

```bash
# Customer reports issue
# They share their .kurral artifact

# Replay exact session locally
kurral mcp start --mode replay --artifact customer-issue.json

# See exactly what they saw, including SSE events
```

---

## 🔧 Configuration

### Multi-Server Setup

```yaml
servers:
  - name: search_server
    url: http://search.example.com/mcp
    tools: ["web_search", "image_search"]
    timeout: 30.0

  - name: compute_server
    url: http://compute.example.com/mcp
    tools: ["calculate", "analyze"]
    timeout: 60.0

  - name: fallback
    url: http://fallback.example.com/mcp
    tools: ["*"]  # Catch-all
```

### Environment Variables

```yaml
servers:
  - name: production
    url: ${MCP_SERVER_URL}  # Reads from env
    headers:
      Authorization: "Bearer ${API_KEY}"
```

### Replay Configuration

```yaml
replay:
  semantic_threshold: 0.8  # 80% similarity for fuzzy matching
  on_cache_miss: passthrough  # Options: error | passthrough

  # passthrough: Forward to live server if no cache
  # error: Return error if no cache (strict mode)
```

---

## 📊 Artifact Format

### Structure

```json
{
  "mcp_session_id": "uuid",
  "mcp_servers_used": ["server1", "server2"],
  "mcp_tool_calls": [
    {
      "id": "call-uuid",
      "timestamp": "2025-12-15T10:00:00",
      "server": "main_server",
      "method": "tools/call",
      "tool_name": "analyze_image",
      "arguments": {"url": "image.jpg"},
      "result": {"objects": ["cat", "dog"]},
      "was_sse": true,
      "events": [
        {
          "event_type": "start",
          "data": {"status": "started"},
          "timestamp": "2025-12-15T10:00:00.100"
        },
        {
          "event_type": "progress",
          "data": {"percent": 50},
          "timestamp": "2025-12-15T10:00:01.200"
        },
        {
          "event_type": "complete",
          "data": {"result": {"objects": ["cat", "dog"]}},
          "timestamp": "2025-12-15T10:00:02.300"
        }
      ],
      "metrics": {
        "total_duration_ms": 2300,
        "time_to_first_event_ms": 100,
        "event_count": 3,
        "events_per_second": 1.30
      }
    }
  ]
}
```

### Performance Metrics

Every captured call includes performance metrics:

- **`total_duration_ms`** - Total execution time
- **`event_count`** - Number of SSE events (0 for non-SSE)
- **`time_to_first_event_ms`** - Time until first SSE event
- **`events_per_second`** - Event rate for SSE streams

---

## 🌊 SSE (Server-Sent Events) Support

### How SSE Capture Works

```
Agent → Proxy → MCP Server (SSE stream)
         ↓
    Captures EVERY event
         ↓
    Forwards to agent in real-time
         ↓
    .kurral artifact
```

**Key Points:**
- Captures ALL events (not just first/last)
- Forwards events in real-time (zero latency)
- Stores event type, data, and timestamp
- Replay reconstructs identical stream

### Example SSE Stream

**Recording:**
```
event: progress
data: {"status": "downloading", "percent": 25}

event: progress
data: {"status": "processing", "percent": 50}

event: complete
data: {"result": {"data": "final"}}
```

**Replay:**
```
# Same events, same order, same timing
event: progress
data: {"status": "downloading", "percent": 25}
...
```

---

## 🔍 API Reference

### CLI Commands

#### `kurral mcp init`

Generate configuration template.

```bash
kurral mcp init [--output kurral-mcp.yaml]
```

#### `kurral mcp start`

Start the proxy server.

```bash
kurral mcp start [OPTIONS]

Options:
  --config PATH      Config file (default: kurral-mcp.yaml)
  --mode MODE        record | replay (default: record)
  --artifact PATH    Artifact for replay mode
  --host HOST        Override proxy host
  --port PORT        Override proxy port
  --verbose          Enable debug logging
```

#### `kurral mcp export`

Export captured calls.

```bash
kurral mcp export [OPTIONS]

Options:
  --host HOST        Proxy host (default: 127.0.0.1)
  --port PORT        Proxy port (default: 3100)
  -o, --output PATH  Output file (default: stdout)
```

### HTTP Endpoints

When proxy is running:

- **`POST /mcp`** - Main MCP endpoint (handles all traffic)
- **`GET /health`** - Health check
- **`GET /stats`** - Proxy statistics (mode, captured calls)
- **`POST /export`** - Export captured calls (same as CLI export)

---

## 🧪 Testing

### Unit Tests

```bash
# Run manual tests (no pytest required)
python test_sse_manual.py

# Or use pytest
pytest kurral/tests/mcp/
```

### Integration Tests

```bash
# Full integration test (mock server + record + replay)
cd examples/mcp_test
./run_integration_test.sh
```

---

## 🛠️ Advanced Usage

### Semantic Matching

Fuzzy matching allows replay even with slightly different arguments:

```yaml
replay:
  semantic_threshold: 0.8  # 80% similarity
```

**Example:**
```python
# Recorded call:
{"location": "San Francisco, CA"}

# Replay request:
{"location": "San Francisco"}

# Similarity: 85% → Match!
```

### Cache Miss Handling

**Error mode (strict):**
```yaml
replay:
  on_cache_miss: error
```
Returns error if no cached response found.

**Passthrough mode (flexible):**
```yaml
replay:
  on_cache_miss: passthrough
```
Forwards to live server if no cache (hybrid mode).

### Custom Headers

```yaml
servers:
  - name: authenticated_server
    url: https://api.example.com/mcp
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      X-Custom-Header: "value"
```

---

## 🐛 Troubleshooting

### Proxy won't start

```bash
# Check if dependencies installed
python -c "import fastapi, uvicorn, httpx"

# Install if missing
pip install kurral[mcp]
```

### Agent can't connect

```bash
# Verify proxy is running
curl http://localhost:3100/health

# Expected: {"status": "healthy", "mode": "record"}
```

### No calls captured

```bash
# Check capture settings in config
capture:
  include_methods: ["tools/call", "tools/list"]
  exclude_tools: []  # Don't exclude anything

# Verify agent is using proxy URL
# Agent should point to: http://localhost:3100
```

### SSE events not captured

```bash
# Check proxy logs
kurral mcp start --verbose

# Look for: "Captured SSE event (progress) for analyze_image"
```

---

## 📚 Additional Resources

- **[SSE Implementation Guide](kurral/mcp/SSE_IMPLEMENTATION.md)** - Deep dive into SSE architecture
- **[MCP Specification](https://modelcontextprotocol.io/docs)** - Official MCP protocol docs
- **[Integration Examples](examples/mcp_test/)** - Mock server and test client

---

## 🤝 Contributing

Found a bug or want a feature? [Open an issue](https://github.com/Kurral/Kurralv3/issues).

### Development Setup

```bash
# Clone repo
git clone https://github.com/Kurral/Kurralv3
cd Kurralv3

# Install in dev mode
pip install -e ".[mcp]"

# Run tests
python test_sse_manual.py
./examples/mcp_test/run_integration_test.sh
```

---

## 📝 License

Same as Kurral core (see root LICENSE).

---

## 🎉 What's Next?

Future enhancements planned:

- **Cost Tracking** - Plugin architecture for provider-specific cost calculation
- **Context Metadata** - User ID, session ID, environment tagging
- **Enhanced Error Details** - Retry tracking, stack traces
- **WebSocket Support** - Beyond SSE streaming
- **Replay Timing** - Preserve original event timing in replay

---

**Built with ❤️ for the MCP community**
