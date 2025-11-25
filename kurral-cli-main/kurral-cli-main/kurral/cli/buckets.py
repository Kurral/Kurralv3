"""
Buckets command for querying semantic buckets
"""

import click
from rich.console import Console
from rich.table import Table

from kurral.core.config import get_config
from kurral.storage.postgres import PostgresStorage

console = Console()


@click.group()
def buckets():
    """
    Query and manage semantic buckets

    Examples:
        kurral buckets list
        kurral buckets show --semantic refund_flow
    """
    pass


@buckets.command()
@click.option(
    "--tenant-id",
    help="Filter by tenant ID",
)
def list(tenant_id):
    """List all semantic buckets"""
    config = get_config()

    if not config.database_url:
        console.print("[red]Error: DATABASE_URL not configured[/red]")
        raise click.Abort()

    storage = PostgresStorage(config.database_url)

    try:
        bucket_names = storage.list_semantic_buckets(tenant_id)

        if not bucket_names:
            console.print("[yellow]No semantic buckets found[/yellow]")
            return

        # Display as table
        table = Table(title="Semantic Buckets")
        table.add_column("#", style="dim")
        table.add_column("Bucket Name", style="cyan")

        for i, bucket in enumerate(bucket_names, 1):
            table.add_row(str(i), bucket)

        console.print(table)
        console.print(f"\n[dim]Total: {len(bucket_names)} buckets[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@buckets.command()
@click.option(
    "--semantic",
    help="Semantic bucket name",
)
@click.option(
    "--tenant-id",
    help="Filter by tenant ID",
)
@click.option(
    "--environment",
    help="Filter by environment",
)
@click.option(
    "--deterministic",
    type=bool,
    help="Filter by deterministic flag",
)
@click.option(
    "--replay-level",
    type=click.Choice(["A", "B", "C"]),
    help="Filter by replay level",
)
@click.option(
    "--limit",
    default=20,
    type=int,
    help="Maximum results to show",
)
def show(semantic, tenant_id, environment, deterministic, replay_level, limit):
    """Show artifacts in a bucket"""
    config = get_config()

    if not config.database_url:
        console.print("[red]Error: DATABASE_URL not configured[/red]")
        raise click.Abort()

    storage = PostgresStorage(config.database_url)

    try:
        # Query artifacts
        results = storage.query(
            tenant_id=tenant_id,
            environment=environment,
            semantic_bucket=semantic,
            deterministic=deterministic,
            replay_level=replay_level,
            limit=limit,
        )

        if not results:
            console.print("[yellow]No artifacts found[/yellow]")
            return

        # Display as table
        table = Table(title=f"Artifacts{' in ' + semantic if semantic else ''}")
        table.add_column("Kurral ID", style="cyan")
        table.add_column("Tenant", style="dim")
        table.add_column("Level", style="yellow")
        table.add_column("Score", style="green")
        table.add_column("Created", style="dim")

        for artifact in results:
            table.add_row(
                str(artifact["kurral_id"])[:8] + "...",
                artifact["tenant_id"],
                artifact["replay_level"],
                f"{artifact.get('determinism_score', 0):.2f}",
                artifact["created_at"].strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(results)} artifacts[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@buckets.command()
@click.option(
    "--tenant-id",
    help="Filter by tenant ID",
)
def stats(tenant_id):
    """Show statistics about stored artifacts"""
    config = get_config()

    if not config.database_url:
        console.print("[red]Error: DATABASE_URL not configured[/red]")
        raise click.Abort()

    storage = PostgresStorage(config.database_url)

    try:
        stats_data = storage.get_stats(tenant_id)

        # Display as table
        table = Table(title="Artifact Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Artifacts", str(stats_data["total"]))
        table.add_row("Deterministic", str(stats_data["deterministic"]))
        table.add_row("Non-deterministic", str(stats_data["non_deterministic"]))
        table.add_row("Level A", str(stats_data["level_a"]))
        table.add_row("Level B", str(stats_data["level_b"]))
        table.add_row("Level C", str(stats_data["level_c"]))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()

