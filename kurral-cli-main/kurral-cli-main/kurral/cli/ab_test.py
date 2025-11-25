"""
CLI commands for A/B testing between agent versions
"""

import asyncio
import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from kurral.core.ab_test import ABTestEngine, VersionConfig, ComparativeABTest
from kurral.models.kurral import KurralArtifact

console = Console()


@click.group()
def ab():
    """A/B testing for agent version comparison"""
    pass


@ab.command()
@click.option("--baseline", required=True, help="Baseline artifacts (semantic bucket or directory)")
@click.option("--model-a", required=True, help="Baseline model name (e.g., gpt-4)")
@click.option("--model-b", required=True, help="Candidate model name (e.g., gpt-4-turbo)")
@click.option("--threshold", default=0.90, help="ARS threshold for passing (0.0-1.0)")
@click.option("--min-samples", default=5, help="Minimum test cases to run")
@click.option("--max-samples", default=None, type=int, help="Maximum test cases (None = all)")
@click.option("--output", help="Save results to JSON file")
def model_migration(baseline, model_a, model_b, threshold, min_samples, max_samples, output):
    """
    Test model migration impact
    
    Example:
        kurral ab model-migration \\
            --baseline semantic:customer_support \\
            --model-a gpt-4 \\
            --model-b gpt-4-turbo \\
            --threshold 0.90
    """
    console.print(f"\n[bold cyan]🔬 A/B Test: Model Migration[/bold cyan]")
    console.print(f"   Baseline: {model_a}")
    console.print(f"   Candidate: {model_b}\n")
    
    # Load baseline artifacts
    artifacts = _load_artifacts(baseline)
    
    if not artifacts:
        console.print(f"[red]❌ No artifacts found in: {baseline}[/red]")
        return
    
    console.print(f"[green]✓ Loaded {len(artifacts)} baseline artifacts[/green]\n")
    
    # Run A/B test
    engine = ComparativeABTest()
    
    with console.status("[bold yellow]Running A/B test..."):
        result = asyncio.run(engine.test_model_migration(
            baseline_artifacts=artifacts,
            from_model=model_a,
            to_model=model_b,
            threshold=threshold,
        ))
    
    # Display results
    _display_results(result)
    
    # Save to file if requested
    if output:
        _save_results(result, output)
        console.print(f"\n[green]✓ Results saved to: {output}[/green]")


@ab.command()
@click.option("--baseline", required=True, help="Baseline artifacts (semantic bucket or directory)")
@click.option("--prompt-a", required=True, help="Current prompt (or file path)")
@click.option("--prompt-b", required=True, help="New prompt (or file path)")
@click.option("--threshold", default=0.90, help="ARS threshold for passing")
@click.option("--output", help="Save results to JSON file")
def prompt_test(baseline, prompt_a, prompt_b, threshold, output):
    """
    Test prompt changes
    
    Example:
        kurral ab prompt-test \\
            --baseline semantic:support \\
            --prompt-a current_prompt.txt \\
            --prompt-b new_prompt.txt
    """
    console.print(f"\n[bold cyan]🔬 A/B Test: Prompt Optimization[/bold cyan]\n")
    
    # Load prompts
    prompt_a_text = _load_text(prompt_a)
    prompt_b_text = _load_text(prompt_b)
    
    # Load artifacts
    artifacts = _load_artifacts(baseline)
    
    if not artifacts:
        console.print(f"[red]❌ No artifacts found in: {baseline}[/red]")
        return
    
    console.print(f"[green]✓ Loaded {len(artifacts)} baseline artifacts[/green]\n")
    
    # Run test
    engine = ComparativeABTest()
    
    with console.status("[bold yellow]Running A/B test..."):
        result = asyncio.run(engine.test_prompt_change(
            baseline_artifacts=artifacts,
            current_prompt=prompt_a_text,
            new_prompt=prompt_b_text,
            threshold=threshold,
        ))
    
    # Display results
    _display_results(result)
    
    if output:
        _save_results(result, output)
        console.print(f"\n[green]✓ Results saved to: {output}[/green]")


@ab.command()
@click.option("--baseline", required=True, help="Baseline artifacts")
@click.option("--config-a", required=True, help="Version A config (JSON file)")
@click.option("--config-b", required=True, help="Version B config (JSON file)")
@click.option("--threshold", default=0.90, help="ARS threshold")
@click.option("--output", help="Save results to JSON file")
def compare(baseline, config_a, config_b, threshold, output):
    """
    Compare two agent configurations
    
    Example:
        kurral ab compare \\
            --baseline semantic:support \\
            --config-a version_a.json \\
            --config-b version_b.json
    """
    console.print(f"\n[bold cyan]🔬 A/B Test: Configuration Comparison[/bold cyan]\n")
    
    # Load configs
    with open(config_a) as f:
        config_a_dict = json.load(f)
    
    with open(config_b) as f:
        config_b_dict = json.load(f)
    
    version_a = VersionConfig(**config_a_dict)
    version_b = VersionConfig(**config_b_dict)
    
    # Load artifacts
    artifacts = _load_artifacts(baseline)
    
    if not artifacts:
        console.print(f"[red]❌ No artifacts found: {baseline}[/red]")
        return
    
    console.print(f"[green]✓ Loaded {len(artifacts)} baseline artifacts[/green]\n")
    
    # Run test
    engine = ABTestEngine()
    
    with console.status("[bold yellow]Running A/B test..."):
        result = asyncio.run(engine.run_ab_test(
            test_suite=artifacts,
            version_a=version_a,
            version_b=version_b,
            threshold=threshold,
        ))
    
    # Display results
    _display_results(result)
    
    if output:
        _save_results(result, output)


def _load_artifacts(source: str) -> list[KurralArtifact]:
    """Load artifacts from semantic bucket or directory"""
    artifacts = []
    
    if source.startswith("semantic:"):
        # Load from semantic bucket (not yet implemented)
        # TODO: Implement semantic bucket loading with proper storage backend
        console.print(f"[yellow]⚠️  Semantic bucket loading not fully implemented[/yellow]")
        console.print(f"[dim]Use directory path for now (e.g., ./artifacts/)[/dim]")
        return []
    
    else:
        # Load from directory
        path = Path(source)
        if not path.exists():
            return []
        
        if path.is_file():
            # Single artifact
            artifact = KurralArtifact.from_json(path.read_text())
            artifacts.append(artifact)
        else:
            # Directory of artifacts
            for file in path.glob("*.kurral"):
                artifact = KurralArtifact.from_json(file.read_text())
                artifacts.append(artifact)
    
    return artifacts


def _load_text(source: str) -> str:
    """Load text from string or file"""
    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text()
    return source


def _display_results(result):
    """Display A/B test results in rich format"""
    
    # Summary panel
    console.print(Panel(
        result.summary,
        title=f"🔬 A/B Test Results",
        border_style="cyan",
    ))
    
    # Metrics table
    console.print("\n[bold]Detailed Metrics:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Version A", style="white")
    table.add_column("Version B", style="white")
    table.add_column("Change", style="yellow")
    
    table.add_row(
        "Mean ARS",
        f"{result.a_mean_ars:.4f}",
        f"{result.b_mean_ars:.4f}",
        f"{result.b_improvement:+.4f}",
    )
    
    table.add_row(
        "Min ARS",
        f"{result.a_min_ars:.4f}",
        f"{result.b_min_ars:.4f}",
        f"{result.b_min_ars - result.a_min_ars:+.4f}",
    )
    
    table.add_row(
        "Max ARS",
        f"{result.a_max_ars:.4f}",
        f"{result.b_max_ars:.4f}",
        f"{result.b_max_ars - result.a_max_ars:+.4f}",
    )
    
    console.print(table)
    
    # Failures
    if result.failures:
        console.print(f"\n[bold red]⚠️  Regressions Detected ({len(result.failures)}):[/bold red]\n")
        
        for i, failure in enumerate(result.failures[:5], 1):  # Show first 5
            console.print(f"[red]{i}. Artifact {failure['artifact_id'][:8]}...[/red]")
            console.print(f"   ARS: {failure['a_ars']:.4f} → {failure['b_ars']:.4f} ({failure['regression']:-.4f})")
        
        if len(result.failures) > 5:
            console.print(f"\n[dim]... and {len(result.failures) - 5} more[/dim]")
    
    console.print()


def _save_results(result, output_path: str):
    """Save results to JSON file"""
    output = {
        "test_id": str(result.test_id),
        "timestamp": result.timestamp.isoformat(),
        "version_a": {
            "name": result.version_a.name,
            "model_name": result.version_a.model_name,
        },
        "version_b": {
            "name": result.version_b.name,
            "model_name": result.version_b.model_name,
        },
        "metrics": {
            "test_suite_size": result.test_suite_size,
            "replays_executed": result.replays_executed,
            "a_mean_ars": result.a_mean_ars,
            "b_mean_ars": result.b_mean_ars,
            "b_improvement": result.b_improvement,
        },
        "recommendation": result.recommendation,
        "per_artifact_scores": result.per_artifact_scores,
        "failures": result.failures,
        "summary": result.summary,
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

