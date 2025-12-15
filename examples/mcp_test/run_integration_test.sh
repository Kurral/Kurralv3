#!/bin/bash
# Integration test for Kurral MCP Proxy
# Tests record mode, export, and replay mode

set -e  # Exit on error

echo "=================================================="
echo "Kurral MCP Proxy Integration Test"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "examples/mcp_test/kurral-mcp.yaml" ]; then
    echo -e "${RED}Error: Must run from kurralv3 root directory${NC}"
    exit 1
fi

cd examples/mcp_test

echo -e "\n${YELLOW}Step 1: Checking dependencies...${NC}"
python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: MCP dependencies not installed${NC}"
    echo "Run: pip install fastapi uvicorn httpx sse-starlette"
    exit 1
fi
echo -e "${GREEN}✓ Dependencies OK${NC}"

echo -e "\n${YELLOW}Step 2: Starting mock MCP server (port 3000)...${NC}"
python3 mock_mcp_server.py > /tmp/mock_server.log 2>&1 &
MOCK_PID=$!
sleep 2

# Check if server started
if ! ps -p $MOCK_PID > /dev/null; then
    echo -e "${RED}✗ Failed to start mock server${NC}"
    cat /tmp/mock_server.log
    exit 1
fi
echo -e "${GREEN}✓ Mock server running (PID: $MOCK_PID)${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    kill $MOCK_PID 2>/dev/null || true
    kill $PROXY_PID 2>/dev/null || true
    rm -f /tmp/mock_server.log /tmp/proxy_record.log /tmp/proxy_replay.log
    echo -e "${GREEN}✓ Cleanup done${NC}"
}

trap cleanup EXIT

echo -e "\n${YELLOW}Step 3: Starting proxy in RECORD mode (port 3100)...${NC}"
cd ../..
kurral mcp start --config examples/mcp_test/kurral-mcp.yaml --mode record --verbose > /tmp/proxy_record.log 2>&1 &
PROXY_PID=$!
sleep 3

# Check if proxy started
if ! ps -p $PROXY_PID > /dev/null; then
    echo -e "${RED}✗ Failed to start proxy${NC}"
    cat /tmp/proxy_record.log
    exit 1
fi
echo -e "${GREEN}✓ Proxy running in RECORD mode (PID: $PROXY_PID)${NC}"

echo -e "\n${YELLOW}Step 4: Running test client...${NC}"
cd examples/mcp_test
python3 test_client.py > /tmp/test_output.log 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Test client completed${NC}"
    cat /tmp/test_output.log
else
    echo -e "${RED}✗ Test client failed${NC}"
    cat /tmp/test_output.log
    exit 1
fi

echo -e "\n${YELLOW}Step 5: Exporting captured calls...${NC}"
cd ../..
kurral mcp export --host 127.0.0.1 --port 3100 --output /tmp/captured_calls.json 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Exported captured calls${NC}"
    echo "Preview:"
    cat /tmp/captured_calls.json | python3 -m json.tool | head -30
else
    echo -e "${RED}✗ Export failed${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 6: Stopping record mode proxy...${NC}"
kill $PROXY_PID
wait $PROXY_PID 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Proxy stopped${NC}"

echo -e "\n${YELLOW}Step 7: Starting proxy in REPLAY mode...${NC}"
kurral mcp start --config examples/mcp_test/kurral-mcp.yaml --mode replay --artifact /tmp/captured_calls.json --verbose > /tmp/proxy_replay.log 2>&1 &
PROXY_PID=$!
sleep 3

if ! ps -p $PROXY_PID > /dev/null; then
    echo -e "${RED}✗ Failed to start replay proxy${NC}"
    cat /tmp/proxy_replay.log
    exit 1
fi
echo -e "${GREEN}✓ Proxy running in REPLAY mode (PID: $PROXY_PID)${NC}"

echo -e "\n${YELLOW}Step 8: Testing replay (mock server can be offline)...${NC}"
cd examples/mcp_test
python3 test_client.py > /tmp/replay_output.log 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Replay test completed${NC}"
    cat /tmp/replay_output.log
else
    echo -e "${RED}✗ Replay test failed${NC}"
    cat /tmp/replay_output.log
    exit 1
fi

echo -e "\n=================================================="
echo -e "${GREEN}✅ ALL INTEGRATION TESTS PASSED!${NC}"
echo -e "=================================================="
echo ""
echo "Summary:"
echo "  - Mock MCP server: ✓"
echo "  - Record mode: ✓"
echo "  - Test client: ✓"
echo "  - Export: ✓"
echo "  - Replay mode: ✓"
echo ""
