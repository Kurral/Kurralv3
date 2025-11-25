"""
Backtest command for regression testing
"""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from kurral.core.backtest import BacktestEngine
from kurral.models.kurral import KurralArtifact

console = Console()


@click.command()
@click.option(
    "--baseline",
    multiple=True,
    required=True,
    help="Baseline artifact files or semantic bucket (semantic:bucket_name)",
)
@click.option(
    "--candidate",
    required=True,
    type=click.Path(exists=True),
    help="Candidate agent config YAML/JSON",
)
@click.option(
    "--threshold",
    default=0.90,
    type=float,
    help="ARS threshold for passing (0.0-1.0)",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output report file (JSON)",
)
@click.option(
    "--max-replays",
    default=100,
    type=int,
    help="Maximum replays to execute",
)
@click.option(
    "--sample-strategy",
    default="adaptive",
    type=click.Choice(["adaptive", "fixed", "all"]),
    help="Sampling strategy",
)
def backtest(baseline, candidate, threshold, output, max_replays, sample_strategy):
    """
    Run backtest for regression testing

    Examples:
        # Test with specific artifacts
        kurral backtest --baseline artifact1.kurral --baseline artifact2.kurral \\
            --candidate config.yaml --threshold 0.90

        # Test with semantic bucket
        kurral backtest --baseline semantic:golden_tests \\
            --candidate config.yaml --output report.json
    """
    # Load baseline artifacts
    baseline_artifacts = []

    with Progress(console=console) as progress:
        task = progress.add_task("Loading baseline artifacts...", total=len(baseline))

        for baseline_spec in baseline:
            if baseline_spec.startswith("semantic:"):
                # Load from semantic bucket
                bucket_name = baseline_spec.split(":", 1)[1]
                console.print(f"[yellow]Loading from semantic bucket: {bucket_name}[/yellow]")
                # TODO: Implement bucket loading
                console.print("[red]Semantic bucket loading not yet implemented[/red]")
                continue
            else:
                # Load from file
                artifact = KurralArtifact.load(baseline_spec)
                baseline_artifacts.append(artifact)

            progress.advance(task)

    if not baseline_artifacts:
        console.print("[red]Error: No baseline artifacts loaded[/red]")
        raise click.Abort()

    console.print(f"\n[cyan]Loaded {len(baseline_artifacts)} baseline artifacts[/cyan]")

    # Load candidate config
    with open(candidate, "r") as f:
        if candidate.endswith(".json"):
            candidate_config = json.load(f)
        else:
            # Assume YAML
            try:
                import yaml

                candidate_config = yaml.safe_load(f)
            except ImportError:
                console.print(
                    "[red]Error: PyYAML not installed. Install with: pip install pyyaml[/red]"
                )
                raise click.Abort()

    console.print(f"[cyan]Loaded candidate config from {candidate}[/cyan]\n")

    # Run backtest
    engine = BacktestEngine()

    with Progress(console=console) as progress:
        task = progress.add_task("Running backtest...", total=None)

        result = asyncio.run(
            engine.backtest(
                baseline_artifacts=baseline_artifacts,
                candidate_config=candidate_config,
                threshold=threshold,
                sample_strategy=sample_strategy,
                max_replays=max_replays,
            )
        )

        progress.update(task, completed=True)

    # Display results
    _display_results(result, threshold)

    # Save report if requested
    if output:
        _save_report(result, output)
        console.print(f"\n[green]Report saved to {output}[/green]")

    # Exit with appropriate code
    if not result.passed:
        raise SystemExit(1)


def _display_results(result, threshold):
    """Display backtest results"""
    # Summary panel
    status = "✅ PASSED" if result.passed else "❌ FAILED"
    color = "green" if result.passed else "red"

    console.print(f"\n[{color}][bold]{status}[/bold][/{color}]\n")

    # Metrics table
    table = Table(title="Backtest Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Baseline Artifacts", str(result.baseline_count))
    table.add_row("Replays Executed", str(result.replays_executed))
    table.add_row("Average ARS", f"{result.ars_score:.4f}")
    table.add_row("Threshold", f"{threshold:.4f}")
    table.add_row("Failures", str(len(result.failures)))

    if result.breakdown:
        table.add_row("Min ARS", f"{result.breakdown.get('min_ars', 0):.4f}")
        table.add_row("Max ARS", f"{result.breakdown.get('max_ars', 0):.4f}")
        table.add_row(
            "Pass Rate", f"{result.breakdown.get('pass_rate', 0) * 100:.1f}%"
        )

    console.print(table)

    # Failures
    if result.failures:
        console.print(f"\n[yellow]Failures ({len(result.failures)}):[/yellow]")
        for i, failure in enumerate(result.failures[:5], 1):  # Show first 5
            console.print(f"  {i}. {failure['kurral_id']} (ARS: {failure['ars_score']:.4f})")

        if len(result.failures) > 5:
            console.print(f"  ... and {len(result.failures) - 5} more")


def _save_report(result, output_path):
    """Save backtest report to file"""
    report = {
        "backtest_id": str(result.backtest_id),
        "timestamp": result.timestamp.isoformat(),
        "baseline_count": result.baseline_count,
        "replays_executed": result.replays_executed,
        "ars_score": result.ars_score,
        "passed": result.passed,
        "threshold": result.threshold,
        "breakdown": result.breakdown,
        "failures": result.failures,
        "summary": result.summary,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

