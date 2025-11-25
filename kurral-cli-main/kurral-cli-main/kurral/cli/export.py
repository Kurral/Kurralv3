"""
Export command for generating .kurral artifacts
"""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from kurral.core.artifact import ArtifactGenerator
from kurral.core.config import get_config
from kurral.integrations.langsmith import LangSmithIntegration
from kurral.models.kurral import KurralArtifact

console = Console()


@click.command()
@click.option(
    "--input",
    "input_file",
    type=click.Path(exists=True),
    help="Input trace JSON file",
)
@click.option(
    "--run-id",
    help="LangSmith run ID to fetch and export",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(),
    help="Output .kurral file path",
)
@click.option(
    "--tenant-id",
    default="default",
    help="Tenant ID for the artifact",
)
@click.option(
    "--semantic-bucket",
    help="Semantic bucket tag (e.g., 'refund_flow')",
)
@click.option(
    "--pretty",
    is_flag=True,
    help="Pretty-print JSON output",
)
def export(input_file, run_id, output, tenant_id, semantic_bucket, pretty):
    """
    Export trace to .kurral artifact

    Examples:
        # Export from local JSON file
        kurral export --input trace.json --output artifact.kurral

        # Export from LangSmith
        kurral export --run-id ls_abc123 --output artifact.kurral --tenant-id acme_prod
    """
    if not input_file and not run_id:
        console.print("[red]Error: Must provide either --input or --run-id[/red]")
        raise click.Abort()

    if input_file and run_id:
        console.print("[red]Error: Cannot use both --input and --run-id[/red]")
        raise click.Abort()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if run_id:
            # Fetch from LangSmith
            task = progress.add_task("Fetching from LangSmith...", total=None)

            config = get_config()
            if not config.langsmith_api_key:
                console.print(
                    "[red]Error: LANGSMITH_API_KEY not set in environment[/red]"
                )
                raise click.Abort()

            # Run async function
            artifact = asyncio.run(_export_from_langsmith(run_id, tenant_id, config))

        else:
            # Load from file
            task = progress.add_task("Loading trace file...", total=None)

            with open(input_file, "r") as f:
                trace_data = json.load(f)

            generator = ArtifactGenerator()
            artifact = generator.from_langsmith_run(trace_data, tenant_id)

        # Add semantic bucket if provided
        if semantic_bucket and semantic_bucket not in artifact.semantic_buckets:
            artifact.semantic_buckets.append(semantic_bucket)

        # Save artifact
        progress.update(task, description="Saving artifact...")
        artifact.save(output)

        progress.update(task, description="Done!", completed=True)

    # Print summary
    console.print("\n[green]✅ Successfully generated .kurral artifact[/green]")
    console.print(f"[dim]Output:[/dim] {output}")
    console.print(f"[dim]Kurral ID:[/dim] {artifact.kurral_id}")
    console.print(f"[dim]Deterministic:[/dim] {artifact.deterministic}")
    console.print(f"[dim]Replay Level:[/dim] {artifact.replay_level.value}")
    console.print(
        f"[dim]Determinism Score:[/dim] {artifact.determinism_report.overall_score:.4f}"
    )

    if not artifact.deterministic:
        console.print("\n[yellow]⚠️  Warning: This artifact is not fully deterministic[/yellow]")
        console.print("[dim]Recommendations:[/dim]")
        for rec in artifact.determinism_report.recommendations:
            console.print(f"  • {rec}")


async def _export_from_langsmith(run_id: str, tenant_id: str, config) -> KurralArtifact:
    """Async helper to export from LangSmith"""
    async with LangSmithIntegration(config.langsmith_api_key) as integration:
        return await integration.import_run(run_id, tenant_id)

