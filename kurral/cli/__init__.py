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
@click.argument("artifact_id")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def replay(artifact_id: str, verbose: bool, debug: bool):
    """Replay an artifact by ID or partial ID.
    
    Examples:
        kurral replay 4babbd1c-d250-4c7a-8e4b-25a1ac134f89
        kurral replay 4babbd1c
    """
    from kurral.cli.replay_cmd import run_replay
    run_replay(artifact_id, verbose=verbose, debug=debug)


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


if __name__ == "__main__":
    main()