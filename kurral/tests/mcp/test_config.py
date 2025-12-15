"""
Unit tests for MCP configuration
"""

import pytest
import tempfile
import os
from pathlib import Path
from kurral.mcp.config import (
    ServerConfig,
    CaptureConfig,
    ReplayConfig,
    ProxyConfig,
    MCPConfig
)


def test_server_config_defaults():
    """Test ServerConfig with default values."""
    config = ServerConfig(url="http://localhost:3000")
    assert config.url == "http://localhost:3000"
    assert config.headers == {}
    assert config.timeout == 30


def test_capture_config_defaults():
    """Test CaptureConfig with default values."""
    config = CaptureConfig()
    assert "tools/call" in config.include_methods
    assert "resources/read" in config.include_methods
    assert config.exclude_tools == []


def test_replay_config_defaults():
    """Test ReplayConfig with default values."""
    config = ReplayConfig()
    assert config.semantic_threshold == 0.85
    assert config.on_cache_miss == "error"
    assert config.mock_response is None


def test_proxy_config_defaults():
    """Test ProxyConfig with default values."""
    config = ProxyConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 3100


def test_mcp_config_defaults():
    """Test MCPConfig with default values."""
    config = MCPConfig()
    assert config.mode == "record"
    assert config.artifact_path is None
    assert config.servers == {}
    assert config.default_server is None


def test_mcp_config_load_nonexistent():
    """Test loading config from nonexistent file returns defaults."""
    config = MCPConfig.load("nonexistent.yaml")
    assert config.mode == "record"


def test_mcp_config_load_yaml():
    """Test loading config from YAML file."""
    yaml_content = """
proxy:
  host: "0.0.0.0"
  port: 8080

mode: "replay"

servers:
  test_server:
    url: "http://localhost:3000"
    timeout: 60
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = MCPConfig.load(temp_path)
        assert config.proxy.host == "0.0.0.0"
        assert config.proxy.port == 8080
        assert config.mode == "replay"
        assert "test_server" in config.servers
        assert config.servers["test_server"].url == "http://localhost:3000"
        assert config.servers["test_server"].timeout == 60
    finally:
        os.unlink(temp_path)


def test_mcp_config_load_yaml_with_env_vars():
    """Test loading config with environment variable substitution."""
    os.environ["TEST_API_KEY"] = "secret123"

    yaml_content = """
servers:
  test:
    url: "http://localhost:3000"
    headers:
      Authorization: "Bearer ${TEST_API_KEY}"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = MCPConfig.load(temp_path)
        assert config.servers["test"].headers["Authorization"] == "Bearer secret123"
    finally:
        os.unlink(temp_path)
        del os.environ["TEST_API_KEY"]


def test_mcp_config_load_shorthand_server():
    """Test loading config with shorthand server URL."""
    yaml_content = """
servers:
  simple: "http://localhost:3000"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config = MCPConfig.load(temp_path)
        assert "simple" in config.servers
        assert config.servers["simple"].url == "http://localhost:3000"
    finally:
        os.unlink(temp_path)


def test_mcp_config_save():
    """Test saving config to YAML file."""
    config = MCPConfig(
        mode="replay",
        artifact_path="test.kurral"
    )
    config.servers = {
        "test": ServerConfig(url="http://localhost:3000")
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = f.name

    try:
        config.save(temp_path)
        assert Path(temp_path).exists()

        # Load it back
        loaded = MCPConfig.load(temp_path)
        assert loaded.mode == "replay"
        assert loaded.artifact_path == "test.kurral"
        assert "test" in loaded.servers
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
