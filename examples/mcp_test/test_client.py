"""
Test Client for Kurral MCP Proxy

This client sends MCP requests to the Kurral proxy to test record/replay functionality.
"""

import httpx
import json
import time


def call_tool(tool_name: str, arguments: dict, proxy_url: str = "http://localhost:3100"):
    """Call a tool through the MCP proxy."""
    request = {
        "jsonrpc": "2.0",
        "id": str(int(time.time() * 1000)),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    response = httpx.post(proxy_url, json=request, timeout=10.0)
    return response.json()


def list_tools(proxy_url: str = "http://localhost:3100"):
    """List available tools through the MCP proxy."""
    request = {
        "jsonrpc": "2.0",
        "id": "list-tools",
        "method": "tools/list",
        "params": {}
    }

    response = httpx.post(proxy_url, json=request, timeout=10.0)
    return response.json()


def call_tool_sse(tool_name: str, arguments: dict, proxy_url: str = "http://localhost:3100"):
    """Call a tool that returns SSE stream through the MCP proxy."""
    request = {
        "jsonrpc": "2.0",
        "id": str(int(time.time() * 1000)),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    events = []
    with httpx.stream("POST", proxy_url, json=request, timeout=30.0) as response:
        buffer = ""
        for chunk in response.iter_text():
            buffer += chunk

            # Parse SSE events
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)

                event_type = "message"
                data_payload = None

                for line in event_block.split("\n"):
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                    if line.startswith("data: "):
                        try:
                            data_payload = json.loads(line[6:])
                        except json.JSONDecodeError:
                            data_payload = line[6:]

                if data_payload is not None:
                    events.append({"type": event_type, "data": data_payload})

    return events


def main():
    """Run test scenarios."""
    print("=" * 60)
    print("Kurral MCP Proxy Test Client")
    print("=" * 60)

    # Test 1: List tools
    print("\n[Test 1] Listing available tools...")
    try:
        result = list_tools()
        if "result" in result:
            tools = result["result"].get("tools", [])
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Calculator - Add
    print("\n[Test 2] Calculator: 5 + 3")
    try:
        result = call_tool("calculator", {"operation": "add", "a": 5, "b": 3})
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print(f"Result: {content}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Calculator - Multiply
    print("\n[Test 3] Calculator: 7 * 6")
    try:
        result = call_tool("calculator", {"operation": "multiply", "a": 7, "b": 6})
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print(f"Result: {content}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Weather
    print("\n[Test 4] Weather: San Francisco")
    try:
        result = call_tool("weather", {"location": "San Francisco"})
        if "result" in result:
            content = result["result"]["content"][0]["text"]
            print(f"Result: {content}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: SSE Streaming - Image Analysis
    print("\n[Test 5] SSE Stream: Analyze Image")
    try:
        events = call_tool_sse("analyze_image", {"url": "https://example.com/cat.jpg"})
        print(f"Received {len(events)} SSE events:")
        for i, event in enumerate(events, 1):
            print(f"  Event {i} ({event['type']}): {event['data']}")

        # Verify we got the expected events
        if len(events) >= 5:
            last_event = events[-1]
            if last_event['type'] == 'complete' and 'result' in last_event['data']:
                print(f"✓ Analysis complete: {last_event['data']['result']}")
        else:
            print(f"⚠ Expected 5 events, got {len(events)}")
    except Exception as e:
        print(f"Error: {e}")

    # Check proxy stats
    print("\n[Stats] Proxy statistics:")
    try:
        response = httpx.get("http://localhost:3100/stats", timeout=5.0)
        stats = response.json()
        print(f"  Mode: {stats['mode']}")
        print(f"  Captured calls: {stats['captured_calls']}")
    except Exception as e:
        print(f"Error getting stats: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
