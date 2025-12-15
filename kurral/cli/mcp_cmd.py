"""
MCP Proxy CLI Commands

CLI commands for starting and managing the Kurral MCP proxy.
"""

import click
import logging
import sys


@click.group(name="mcp")
def mcp_group():
    """MCP proxy commands."""
    pass


@mcp_group.command(name="start")
@click.option("--config", "-c", default="kurral-mcp.yaml", help="Config file path")
@click.option("--host", "-h", default=None, help="Override host")
@click.option("--port", "-p", default=None, type=int, help="Override port")
@click.option("--mode", "-m", type=click.Choice(["record", "replay"]), default=None)
@click.option("--artifact", "-a", default=None, help="Artifact path for replay mode")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def start_proxy(config, host, port, mode, artifact, verbose):
    """Start the MCP proxy server."""
    try:
        from kurral.mcp.proxy import KurralMCPProxy
        from kurral.mcp.config import MCPConfig
    except ImportError as e:
        click.echo(
            "Error: MCP proxy dependencies not installed.\n"
            "Install with: pip install kurral[mcp]",
            err=True
        )
        sys.exit(1)

    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[Kurral MCP] %(levelname)s: %(message)s"
    )

    # Load config
    try:
        cfg = MCPConfig.load(config)
    except FileNotFoundError:
        click.echo(
            f"Config file not found: {config}\n"
            f"Create one with: kurral mcp init",
            err=True
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

    # Apply overrides
    if mode:
        cfg.mode = mode
    if artifact:
        cfg.artifact_path = artifact
    if host:
        cfg.proxy.host = host
    if port:
        cfg.proxy.port = port

    # Validate replay mode
    if cfg.mode == "replay" and not cfg.artifact_path:
        click.echo(
            "Error: Replay mode requires --artifact or artifact_path in config",
            err=True
        )
        sys.exit(1)

    # Create and run proxy
    try:
        proxy = KurralMCPProxy(cfg)
        proxy.run()
    except Exception as e:
        click.echo(f"Error starting proxy: {e}", err=True)
        sys.exit(1)


@mcp_group.command(name="init")
@click.option("--output", "-o", default="kurral-mcp.yaml", help="Output config path")
def init_config(output):
    """Generate a sample MCP proxy config file."""
    sample_config = """# Kurral MCP Proxy Configuration
# Documentation: https://github.com/Kurral/Kurralv3

proxy:
  host: "127.0.0.1"
  port: 3100

mode: "record"  # "record" or "replay"

# For replay mode, specify artifact path
# artifact_path: "artifacts/your-artifact.kurral"

# Configure upstream MCP servers
servers:
  # Example: GitHub MCP
  # github:
  #   url: "https://mcp.github.com/sse"
  #   headers:
  #     Authorization: "Bearer ${GITHUB_TOKEN}"

  # Example: Local MCP server
  # local:
  #   url: "http://localhost:3000/mcp"

# Capture settings
capture:
  include_methods:
    - "tools/call"
    - "resources/read"
  exclude_tools: []

# Replay settings
replay:
  semantic_threshold: 0.85
  on_cache_miss: "error"  # "error", "passthrough", or "mock"
"""

    try:
        with open(output, "w") as f:
            f.write(sample_config)
        click.echo(f"Created config file: {output}")
    except Exception as e:
        click.echo(f"Error creating config: {e}", err=True)
        sys.exit(1)


@mcp_group.command(name="export")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=3100, type=int)
@click.option("--output", "-o", default=None, help="Output file path")
def export_captured(host, port, output):
    """Export captured MCP calls from running proxy."""
    try:
        import httpx
    except ImportError:
        click.echo(
            "Error: httpx not installed.\n"
            "Install with: pip install kurral[mcp]",
            err=True
        )
        sys.exit(1)

    url = f"http://{host}:{port}/export"

    try:
        response = httpx.post(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if output:
            import json
            with open(output, "w") as f:
                json.dump(data, f, indent=2, default=str)
            click.echo(f"Exported to: {output}")
        else:
            import json
            click.echo(json.dumps(data, indent=2, default=str))

    except httpx.ConnectError:
        click.echo(
            f"Error: Could not connect to proxy at {host}:{port}\n"
            f"Is the proxy running?",
            err=True
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
