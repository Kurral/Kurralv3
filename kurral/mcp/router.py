"""
MCP Router

Routes MCP requests to the correct upstream server.
"""

from typing import Optional, Dict, List
import logging

from kurral.mcp.config import MCPConfig, ServerConfig
from kurral.mcp.models import JSONRPCRequest

logger = logging.getLogger("kurral.mcp.router")


class MCPRouter:
    """
    Routes MCP requests to the correct upstream server.
    """

    def __init__(self, config: MCPConfig):
        self.config = config
        self._tool_to_server: Dict[str, str] = {}  # Cache: tool_name -> server_name

    async def discover_tools(self):
        """
        Discover available tools from all configured servers.
        Builds the tool -> server routing table.
        """
        import httpx

        for server_name, server_config in self.config.servers.items():
            try:
                # Call tools/list on each server
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        server_config.url,
                        json={
                            "jsonrpc": "2.0",
                            "id": "discovery",
                            "method": "tools/list",
                            "params": {}
                        },
                        headers=server_config.headers,
                        timeout=server_config.timeout
                    )

                    data = response.json()
                    if "result" in data and "tools" in data["result"]:
                        tools = data["result"]["tools"]
                        for tool in tools:
                            tool_name = tool.get("name")
                            if tool_name:
                                self._tool_to_server[tool_name] = server_name

                logger.info(f"Discovered {len(self._tool_to_server)} tools from {server_name}")

            except Exception as e:
                logger.warning(f"Failed to discover tools from {server_name}: {e}")

    def route(self, request: JSONRPCRequest) -> Optional[ServerConfig]:
        """
        Determine which upstream server should handle this request.
        Returns None if no server can be found.
        """
        # For tools/call, route based on tool name
        if request.method == "tools/call" and request.params:
            tool_name = request.params.get("name")
            if tool_name and tool_name in self._tool_to_server:
                server_name = self._tool_to_server[tool_name]
                return self.config.servers.get(server_name)

        # For other methods, use default server
        if self.config.default_server:
            return self.config.servers.get(self.config.default_server)

        # If only one server configured, use it
        if len(self.config.servers) == 1:
            return list(self.config.servers.values())[0]

        return None

    def get_server_name(self, request: JSONRPCRequest) -> Optional[str]:
        """Get the server name for a request (for capture logging)."""
        if request.method == "tools/call" and request.params:
            tool_name = request.params.get("name")
            if tool_name and tool_name in self._tool_to_server:
                return self._tool_to_server[tool_name]

        if self.config.default_server:
            return self.config.default_server

        if len(self.config.servers) == 1:
            return list(self.config.servers.keys())[0]

        return "unknown"

    def add_tool_route(self, tool_name: str, server_name: str):
        """Manually add a tool -> server route."""
        self._tool_to_server[tool_name] = server_name
