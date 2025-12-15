"""
Mock MCP Server for Testing

A simple FastAPI server that implements the MCP protocol for testing the Kurral MCP proxy.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import asyncio
import json

app = FastAPI(title="Mock MCP Server")

# Mock tool registry
MOCK_TOOLS = [
    {
        "name": "calculator",
        "description": "Perform basic arithmetic operations",
        "parameters": {
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
            "a": {"type": "number"},
            "b": {"type": "number"}
        }
    },
    {
        "name": "weather",
        "description": "Get weather information for a location",
        "parameters": {
            "location": {"type": "string"}
        }
    },
    {
        "name": "analyze_image",
        "description": "Analyze an image and detect objects (streams results via SSE)",
        "parameters": {
            "url": {"type": "string", "description": "URL of the image to analyze"}
        },
        "streaming": True
    }
]


@app.post("/mcp")
@app.post("/")
async def handle_mcp(request: Request):
    """Handle MCP JSON-RPC requests."""
    body = await request.json()

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    # Handle tools/list
    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": MOCK_TOOLS
            }
        })

    # Handle tools/call
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "calculator":
            operation = arguments.get("operation")
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)

            result_value = 0
            if operation == "add":
                result_value = a + b
            elif operation == "subtract":
                result_value = a - b
            elif operation == "multiply":
                result_value = a * b
            elif operation == "divide":
                result_value = a / b if b != 0 else "Error: Division by zero"

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Result: {result_value}"
                        }
                    ]
                }
            })

        elif tool_name == "weather":
            location = arguments.get("location", "unknown")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"The weather in {location} is sunny and 72°F"
                        }
                    ]
                }
            })

        elif tool_name == "analyze_image":
            # Return SSE stream for image analysis
            image_url = arguments.get("url", "unknown.jpg")

            async def generate_analysis_events():
                """Generate SSE events simulating image analysis progress."""
                # Event 1: Start
                yield "event: start\n"
                yield f"data: {json.dumps({'status': 'started', 'url': image_url})}\n\n"
                await asyncio.sleep(0.5)

                # Event 2: Downloading
                yield "event: progress\n"
                yield f"data: {json.dumps({'status': 'downloading', 'percent': 25})}\n\n"
                await asyncio.sleep(0.5)

                # Event 3: Processing
                yield "event: progress\n"
                yield f"data: {json.dumps({'status': 'processing', 'percent': 50})}\n\n"
                await asyncio.sleep(0.5)

                # Event 4: Analyzing
                yield "event: progress\n"
                yield f"data: {json.dumps({'status': 'analyzing', 'percent': 75})}\n\n"
                await asyncio.sleep(0.5)

                # Event 5: Complete with results
                yield "event: complete\n"
                yield f"data: {json.dumps({'result': {'objects': ['cat', 'dog', 'tree'], 'confidence': 0.95}})}\n\n"

            return StreamingResponse(
                generate_analysis_events(),
                media_type="text/event-stream"
            )

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            })

    # Unknown method
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        })


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    print("Starting Mock MCP Server on http://localhost:3000")
    uvicorn.run(app, host="127.0.0.1", port=3000)
