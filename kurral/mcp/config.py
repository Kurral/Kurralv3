"""
MCP Proxy Configuration

Configuration loading and validation for the Kurral MCP proxy.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from pathlib import Path
import yaml
import os
import re


class ServerConfig(BaseModel):
    """Configuration for an upstream MCP server."""
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30


class CaptureConfig(BaseModel):
    """Configuration for capture behavior."""
    include_methods: List[str] = Field(default=["tools/call", "resources/read"])
    exclude_tools: List[str] = Field(default_factory=list)


class ReplayConfig(BaseModel):
    """Configuration for replay behavior."""
    semantic_threshold: float = 0.85
    on_cache_miss: Literal["error", "passthrough", "mock"] = "error"
    mock_response: Optional[dict] = None


class ProxyConfig(BaseModel):
    """Configuration for the proxy server itself."""
    host: str = "127.0.0.1"
    port: int = 3100


class MCPConfig(BaseModel):
    """Main MCP proxy configuration."""
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    mode: Literal["record", "replay"] = "record"
    artifact_path: Optional[str] = None
    servers: Dict[str, ServerConfig] = Field(default_factory=dict)
    default_server: Optional[str] = None
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    replay: ReplayConfig = Field(default_factory=ReplayConfig)

    @classmethod
    def load(cls, path: str = "kurral-mcp.yaml") -> "MCPConfig":
        """
        Load config from YAML file with environment variable substitution.

        Args:
            path: Path to the YAML config file

        Returns:
            MCPConfig instance
        """
        if not Path(path).exists():
            return cls()

        with open(path) as f:
            raw = f.read()

        # Substitute environment variables: ${VAR_NAME}
        def replace_env(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        raw = re.sub(r'\$\{(\w+)\}', replace_env, raw)
        data = yaml.safe_load(raw)

        # Normalize server configs (allow shorthand: server_name: "url")
        if "servers" in data:
            for name, server in data["servers"].items():
                if isinstance(server, str):
                    data["servers"][name] = {"url": server}

        return cls(**data)

    def save(self, path: str = "kurral-mcp.yaml"):
        """
        Save config to YAML file.

        Args:
            path: Path to save the YAML config file
        """
        # Convert to dict
        data = self.model_dump(exclude_none=True)

        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
