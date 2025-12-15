# Kurral MCP Proxy

HTTP/SSE proxy for intercepting MCP (Model Context Protocol) tool calls, capturing them for Kurral artifacts, and enabling deterministic replay.

## Overview

The Kurral MCP Proxy sits between AI agents and MCP servers, transparently capturing all tool calls for later replay. This enables:

- **Complete observability** of MCP tool usage
- **Deterministic replay** for testing and debugging
- **A/B testing** between different agent versions
- **Regression detection** when tools or models change

## Architecture

```
┌──────────┐         ┌─────────────────┐         ┌──────────────────┐
│          │  HTTP   │                 │  HTTP   │                  │
│  Agent   │────────▶│  Kurral MCP     │────────▶│  Real MCP        │
│          │         │  Proxy          │         │  Server          │
│          │◀────────│                 │◀────────│                  │
└──────────┘   SSE   │  (captures all) │   SSE   └──────────────────┘
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ .kurral artifact│
                     │ (tool_calls)    │
                     └─────────────────┘
```

## Quick Start

### Installation

```bash
pip install kurral[mcp]
```

### 1. Initialize Configuration

```bash
kurral mcp init
```

This creates `kurral-mcp.yaml`:

```yaml
proxy:
  host: "127.0.0.1"
  port: 3100

mode: "record"  # or "replay"

servers:
  # Add your MCP servers here
  github:
    url: "https://mcp.github.com/sse"
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"
```

### 2. Start the Proxy

**Record Mode:**
```bash
kurral mcp start --mode record
```

**Replay Mode:**
```bash
kurral mcp start --mode replay --artifact artifacts/my-capture.kurral
```

### 3. Point Your Agent to the Proxy

Configure your agent to use `http://localhost:3100` as its MCP server instead of the real MCP server.

### 4. Export Captured Calls

```bash
kurral mcp export --output captured.json
```

## Components

### Models (`models.py`)
Pydantic models for MCP JSON-RPC messages and captured data:
- `JSONRPCRequest` / `JSONRPCResponse`
- `CapturedMCPCall` - Single captured tool call
- `MCPSession` - Complete capture session

### Configuration (`config.py`)
YAML-based configuration with environment variable substitution:
- Server configurations
- Capture filters
- Replay settings

### Capture Engine (`capture.py`)
Records MCP requests/responses:
- Method filtering
- Tool blacklisting
- Session management

### Router (`router.py`)
Routes requests to correct upstream servers:
- Tool discovery
- Multi-server support
- Automatic routing

### Replay Engine (`replay.py`)
Returns cached responses:
- Exact matching
- Semantic fuzzy matching
- Cache miss handling

### Proxy Server (`proxy.py`)
Main FastAPI server:
- HTTP/SSE handling
- Request forwarding
- Response capture
- Stream processing

## Configuration Options

### Proxy Settings

```yaml
proxy:
  host: "127.0.0.1"  # Bind address
  port: 3100          # Port number
```

### Mode

```yaml
mode: "record"  # "record" or "replay"
artifact_path: "path/to/artifact.kurral"  # For replay mode
```

### Server Configuration

```yaml
servers:
  # Simple format
  server1: "http://localhost:3000/mcp"

  # Full format
  server2:
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${API_KEY}"
    timeout: 30
```

### Capture Settings

```yaml
capture:
  include_methods:
    - "tools/call"
    - "resources/read"
  exclude_tools:
    - "internal_debug_tool"
```

### Replay Settings

```yaml
replay:
  semantic_threshold: 0.85  # Fuzzy match threshold (0.0-1.0)
  on_cache_miss: "error"    # "error" | "passthrough" | "mock"
  mock_response: null        # Default mock response
```

## CLI Commands

### Start Proxy

```bash
kurral mcp start [OPTIONS]

Options:
  --config, -c TEXT           Config file path (default: kurral-mcp.yaml)
  --host, -h TEXT             Override host
  --port, -p INTEGER          Override port
  --mode, -m [record|replay]  Override mode
  --artifact, -a TEXT         Artifact path for replay mode
  --verbose, -v               Verbose logging
```

### Initialize Config

```bash
kurral mcp init [OPTIONS]

Options:
  --output, -o TEXT  Output config path (default: kurral-mcp.yaml)
```

### Export Captured Calls

```bash
kurral mcp export [OPTIONS]

Options:
  --host TEXT        Proxy host (default: 127.0.0.1)
  --port INTEGER     Proxy port (default: 3100)
  --output, -o TEXT  Output file path
```

## Programmatic Usage

```python
from kurral.mcp import create_proxy, MCPConfig

# Create from config file
proxy = create_proxy("kurral-mcp.yaml")
proxy.run()

# Create programmatically
config = MCPConfig(
    mode="record",
    servers={
        "my_server": {"url": "http://localhost:3000"}
    }
)
proxy = KurralMCPProxy(config)
proxy.run()
```

## Testing

See `examples/mcp_test/` for a complete test setup with:
- Mock MCP server
- Sample configuration
- Test client
- Step-by-step instructions

## Integration with Kurral Artifacts

MCP calls are captured in a format compatible with `.kurral` artifacts:

```json
{
  "mcp_session_id": "uuid",
  "mcp_servers_used": ["server1", "server2"],
  "mcp_tool_calls": [
    {
      "id": "uuid",
      "timestamp": "2025-01-15T10:30:00",
      "source": "mcp",
      "server": "server1",
      "method": "tools/call",
      "tool_name": "calculator",
      "arguments": {"a": 5, "b": 3},
      "result": {"value": 8},
      "duration_ms": 42
    }
  ]
}
```

## Advanced Features

### Semantic Matching

The replay engine can fuzzy-match tool calls with slightly different arguments:

```yaml
replay:
  semantic_threshold: 0.85  # 85% similarity required
```

This uses Kurral's existing semantic similarity scoring.

### Cache Miss Handling

Configure what happens when no cached response is found:

- `error` (default): Return JSON-RPC error
- `passthrough`: Forward to real server
- `mock`: Return predefined mock response

### Multi-Server Routing

The proxy can route different tools to different servers:

```yaml
servers:
  github:
    url: "https://mcp.github.com/sse"
  slack:
    url: "https://mcp.slack.com/sse"

default_server: "github"  # Fallback server
```

Tool discovery automatically builds the routing table.

## Troubleshooting

**Dependencies not installed:**
```bash
pip install kurral[mcp]
```

**Port already in use:**
```bash
# Change port in config
kurral mcp start --port 3101
```

**Connection refused:**
- Ensure proxy is running
- Check firewall settings
- Verify server URLs in config

**Replay cache misses:**
- Check semantic threshold setting
- Verify artifact contains MCP calls
- Enable verbose logging: `--verbose`

## Contributing

The MCP proxy is part of the Kurral project. See the main repository for contribution guidelines.

## License

Apache 2.0 - See LICENSE file in repository root.
