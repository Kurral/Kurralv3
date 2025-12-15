"""
Kurral CLI - Command line interface for Kurral

Usage:
    kurral replay <artifact_id>
    kurral list
    kurral --help
"""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="kurral")
def main():
    """Kurral - Deterministic Testing and Replay for AI Agents"""
    pass


@main.command()
@click.argument("artifact", required=False)
@click.option("--run-id", help="Replay artifact by run_id")
@click.option("--latest", is_flag=True, help="Replay the latest artifact")
@click.option("--storage-path", type=click.Path(exists=False), help="Path to artifact storage (defaults to ./artifacts)")
@click.option("--llm-client", help="LLM client type (openai, anthropic, etc.) - required for B replay")
@click.option("--diff", is_flag=True, help="Show diff between original and replay outputs")
@click.option("--debug", is_flag=True, help="Enable debug mode with verbose output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--current-model", help="Current model name (for change detection)")
@click.option("--current-temperature", type=float, help="Current temperature (for change detection)")
def replay(artifact, run_id, latest, storage_path, llm_client, diff, debug, verbose, current_model, current_temperature):
    """Replay a .kurral artifact with automatic A/B replay detection.
    
    Examples:
        kurral replay 4babbd1c-d250-4c7a-8e4b-25a1ac134f89
        kurral replay artifacts/4babbd1c-d250-4c7a-8e4b-25a1ac134f89.kurral
        kurral replay --latest
        kurral replay --run-id my_run_123
    """
    from kurral.cli.replay_cmd import replay as replay_func
    replay_func(
        artifact=artifact,
        run_id=run_id,
        latest=latest,
        storage_path=storage_path,
        llm_client=llm_client,
        diff=diff,
        debug=debug,
        verbose=verbose,
        current_model=current_model,
        current_temperature=current_temperature
    )


@main.command("list")
@click.option("--limit", "-n", default=10, help="Number of artifacts to show")
@click.option("--bucket", "-b", help="Filter by semantic bucket")
def list_artifacts(limit: int, bucket: str):
    """List recent artifacts."""
    from kurral.artifact_manager import ArtifactManager
    
    manager = ArtifactManager()
    artifacts = manager.list_artifacts(limit=limit, bucket=bucket)
    
    if not artifacts:
        console.print("[yellow]No artifacts found.[/yellow]")
        return
    
    console.print(f"\n[bold]Recent Artifacts[/bold] (showing {len(artifacts)})\n")
    
    for artifact in artifacts:
        kurral_id = artifact.get("kurral_id", "unknown")[:8]
        timestamp = artifact.get("timestamp", "unknown")
        model = artifact.get("llm_config", {}).get("model_name", "unknown")
        interactions = len(artifact.get("inputs", {}).get("interactions", []))
        
        console.print(f"  [cyan]{kurral_id}[/cyan]  {model}  {interactions} interaction(s)  {timestamp}")
    
    console.print()


@main.command()
@click.argument("artifact_id")
def show(artifact_id: str):
    """Show details of a specific artifact."""
    from kurral.artifact_manager import ArtifactManager
    from rich.json import JSON
    
    manager = ArtifactManager()
    artifact = manager.get_artifact(artifact_id)
    
    if not artifact:
        console.print(f"[red]Artifact not found: {artifact_id}[/red]")
        return
    
    console.print(JSON.from_data(artifact))


@main.command()
def init():
    """Initialize Kurral in the current directory."""
    import os

    # Create artifacts directory
    os.makedirs("artifacts", exist_ok=True)
    os.makedirs("replay_runs", exist_ok=True)
    os.makedirs("side_effect", exist_ok=True)

    console.print("[green]✓[/green] Created artifacts/ directory")
    console.print("[green]✓[/green] Created replay_runs/ directory")
    console.print("[green]✓[/green] Created side_effect/ directory")
    console.print("\n[bold]Kurral initialized![/bold] Add @trace_agent() to your agent.")


# Register MCP commands
try:
    from kurral.cli.mcp_cmd import mcp_group
    main.add_command(mcp_group)
except ImportError:
    # MCP dependencies not installed, skip
    pass


if __name__ == "__main__":
    main()