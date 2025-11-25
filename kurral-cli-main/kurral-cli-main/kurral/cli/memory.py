"""
CLI commands for managing in-memory artifact storage.
"""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def memory():
    """Manage in-memory artifact storage"""
    pass


@memory.command()
def stats():
    """Show memory storage statistics"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        stats = mem_storage.get_stats()
        
        table = Table(title="Memory Storage Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Artifact Count", f"{stats['artifact_count']} / {stats['max_artifacts']}")
        table.add_row("Total Size", f"{stats['total_size_mb']} MB / {stats['max_size_mb']} MB")
        table.add_row("Utilization", f"{stats['utilization_percent']}%")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting memory stats:[/red] {e}")


@memory.command()
@click.option("--prefix", default=None, help="Filter by artifact ID prefix")
def list(prefix):
    """List all artifacts in memory"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        artifact_ids = mem_storage.list_artifacts(prefix=prefix)
        
        if not artifact_ids:
            console.print("[yellow]No artifacts found in memory[/yellow]")
            return
        
        table = Table(title="Artifacts in Memory", show_header=True)
        table.add_column("Artifact ID", style="cyan")
        
        for aid in artifact_ids:
            table.add_row(aid)
        
        console.print(table)
        console.print(f"\n[green]Total: {len(artifact_ids)} artifacts[/green]")
        
    except Exception as e:
        console.print(f"[red]Error listing artifacts:[/red] {e}")


@memory.command()
@click.argument("artifact_id")
def get(artifact_id):
    """Retrieve an artifact from memory"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        artifact = mem_storage.download(artifact_id)
        
        if not artifact:
            console.print(f"[red]Artifact not found:[/red] {artifact_id}")
            return
        
        console.print(f"[green]✓ Found artifact:[/green] {artifact_id}")
        console.print(f"  Tenant: {artifact.tenant_id}")
        console.print(f"  Environment: {artifact.environment}")
        console.print(f"  Timestamp: {artifact.timestamp}")
        console.print(f"  Model: {artifact.llm_config.model_name} ({artifact.llm_config.provider})")
        
        if artifact.tool_calls:
            console.print(f"  Tool Calls: {len(artifact.tool_calls)}")
        
    except Exception as e:
        console.print(f"[red]Error retrieving artifact:[/red] {e}")


@memory.command()
@click.argument("artifact_id")
@click.argument("output_path")
def export(artifact_id, output_path):
    """Export an artifact from memory to disk"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        artifact = mem_storage.download(artifact_id)
        
        if not artifact:
            console.print(f"[red]Artifact not found:[/red] {artifact_id}")
            return
        
        artifact.save(output_path)
        console.print(f"[green]✓ Exported to:[/green] {output_path}")
        
    except Exception as e:
        console.print(f"[red]Error exporting artifact:[/red] {e}")


@memory.command()
@click.argument("artifact_id")
@click.confirmation_option(prompt="Are you sure you want to delete this artifact?")
def delete(artifact_id):
    """Delete an artifact from memory"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        success = mem_storage.delete(artifact_id)
        
        if success:
            console.print(f"[green]✓ Deleted:[/green] {artifact_id}")
        else:
            console.print(f"[red]Artifact not found:[/red] {artifact_id}")
        
    except Exception as e:
        console.print(f"[red]Error deleting artifact:[/red] {e}")


@memory.command()
@click.confirmation_option(prompt="Are you sure you want to clear all artifacts from memory?")
def clear():
    """Clear all artifacts from memory"""
    try:
        from kurral.storage.memory import get_memory_storage
        
        mem_storage = get_memory_storage()
        mem_storage.clear()
        console.print("[green]✓ Memory storage cleared[/green]")
        
    except Exception as e:
        console.print(f"[red]Error clearing memory:[/red] {e}")

