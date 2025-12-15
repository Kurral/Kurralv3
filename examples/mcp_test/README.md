# Kurral MCP Proxy Test Example

This example demonstrates how to use the Kurral MCP Proxy to capture and replay MCP tool calls.

## Setup

1. **Install Kurral with MCP dependencies:**
   ```bash
   cd /tmp/kurralv3
   pip install -e ".[mcp]"
   ```

2. **Verify installation:**
   ```bash
   kurral mcp --help
   ```

## Running the Test

This test involves three components that run in separate terminals:

### Terminal 1: Start Mock MCP Server

```bash
cd examples/mcp_test
python mock_mcp_server.py
```

This starts a mock MCP server on `http://localhost:3000` with two tools:
- `calculator`: Performs arithmetic operations
- `weather`: Returns mock weather data

### Terminal 2: Start Kurral MCP Proxy (Record Mode)

```bash
cd examples/mcp_test
kurral mcp start --config kurral-mcp.yaml --mode record --verbose
```

This starts the Kurral proxy on `http://localhost:3100` in record mode.

### Terminal 3: Run Test Client

```bash
cd examples/mcp_test
python test_client.py
```

This sends several test requests through the proxy:
1. List available tools
2. Calculator: 5 + 3
3. Calculator: 7 * 6
4. Weather: San Francisco

## Verify Recording

After running the test client, export the captured calls:

```bash
# In a new terminal
kurral mcp export --host 127.0.0.1 --port 3100 --output captured_calls.json
cat captured_calls.json
```

You should see all the captured MCP calls in JSON format.

## Testing Replay Mode

1. **Stop the proxy** (Ctrl+C in Terminal 2)

2. **Start proxy in replay mode:**
   ```bash
   # First, create a mock artifact with the captured calls
   # (In production, this would be a real .kurral artifact)

   # Restart proxy in replay mode
   kurral mcp start --config kurral-mcp.yaml --mode replay --artifact captured_calls.json --verbose
   ```

3. **Run the test client again:**
   ```bash
   python test_client.py
   ```

   The proxy should return cached responses without calling the mock MCP server!

4. **Verify:** You can stop the mock MCP server (Terminal 1) and the test client should still work because it's using cached responses.

## Expected Output

### Record Mode
```
[Kurral MCP] INFO: Starting Kurral MCP Proxy on 127.0.0.1:3100 (mode: record)
[Kurral MCP] INFO: Captured MCP call: calculator (15ms) -> success
[Kurral MCP] INFO: Captured MCP call: calculator (12ms) -> success
[Kurral MCP] INFO: Captured MCP call: weather (10ms) -> success
```

### Replay Mode
```
[Kurral MCP] INFO: Loaded 3 cached MCP calls for replay
[Kurral MCP] INFO: Starting Kurral MCP Proxy on 127.0.0.1:3100 (mode: replay)
[Kurral MCP] INFO: Cache HIT (exact): calculator
[Kurral MCP] INFO: Cache HIT (exact): calculator
[Kurral MCP] INFO: Cache HIT (exact): weather
```

## Configuration

Edit `kurral-mcp.yaml` to:
- Change proxy host/port
- Add more upstream MCP servers
- Configure capture/replay behavior
- Adjust semantic matching threshold

## Troubleshooting

**Port already in use:**
```bash
# Change port in kurral-mcp.yaml
proxy:
  port: 3101
```

**Dependencies not installed:**
```bash
pip install fastapi uvicorn httpx sse-starlette
# Or:
pip install kurral[mcp]
```

**Connection refused:**
- Make sure the mock MCP server is running (Terminal 1)
- Make sure the proxy is running (Terminal 2)
- Check that ports 3000 and 3100 are not blocked

## Next Steps

- Try modifying the test client to send different requests
- Experiment with semantic matching by slightly changing arguments
- Test cache miss behavior by configuring `on_cache_miss` in the config
- Integrate with a real MCP server instead of the mock
