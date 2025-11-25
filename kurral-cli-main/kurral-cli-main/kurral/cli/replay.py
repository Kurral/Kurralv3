"""
Replay command for deterministic execution
"""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurral.core.replay import ReplayEngine
from kurral.models.kurral import KurralArtifact, ReplayOverrides

console = Console()


@click.command()
@click.argument("artifact", type=click.Path(exists=True))
@click.option(
    "--prompt-override",
    type=click.Path(exists=True),
    help="Override prompt with file contents",
)
@click.option(
    "--temperature",
    type=float,
    help="Override temperature",
)
@click.option(
    "--model",
    help="Override model name",
)
@click.option(
    "--diff",
    is_flag=True,
    help="Show diff between original and replay outputs",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode with verbose output",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def replay(artifact, prompt_override, temperature, model, diff, debug, verbose):
    """
    Replay a .kurral artifact

    Examples:
        # Basic replay
        kurral replay artifact.kurral

        # Replay with prompt override
        kurral replay artifact.kurral --prompt-override new_prompt.txt

        # Show diff
        kurral replay artifact.kurral --diff
    """
    # Load artifact
    artifact_obj = KurralArtifact.load(artifact)

    console.print(f"\n[cyan]Replaying artifact: {artifact_obj.kurral_id}[/cyan]")
    console.print(f"[dim]Original run: {artifact_obj.run_id}[/dim]")
    console.print(f"[dim]Replay level: {artifact_obj.replay_level.value}[/dim]\n")

    # Build overrides
    overrides = None
    if prompt_override or temperature or model:
        prompt_text = None
        if prompt_override:
            with open(prompt_override, "r") as f:
                prompt_text = f.read()
            console.print(f"[yellow]Using prompt override from {prompt_override}[/yellow]")

        overrides = ReplayOverrides(
            prompt=prompt_text,
            temperature=temperature,
            model_name=model,
        )

    # Run replay
    engine = ReplayEngine()
    result = asyncio.run(engine.replay(artifact_obj, overrides))

    # Display results
    if diff:
        _display_diff(artifact_obj, result)
    else:
        _display_outputs(result)

    # Summary
    console.print(f"\n[green]✅ Replay completed in {result.duration_ms}ms[/green]")
    console.print(f"[dim]Cache hits: {result.cache_hits}[/dim]")
    console.print(f"[dim]Cache misses: {result.cache_misses}[/dim]")
    if result.validation:
        console.print(
            f"[dim]Hash match:[/dim] {'✅' if result.validation.hash_match else '⚠️'} "
            f"({result.validation.original_hash[:8]} -> {result.validation.replay_hash[:8]})"
        )
        console.print(
            f"[dim]Structural match:[/dim] {'✅' if result.validation.structural_match else '⚠️'}"
        )
    if result.replay_metadata:
        console.print(
            f"[dim]Replay ID:[/dim] {result.replay_metadata.replay_id} "
            f"(record: {result.replay_metadata.record_ref})"
        )

    if result.match:
        console.print("[green]✅ Outputs match original[/green]")
    else:
        console.print("[yellow]⚠️  Outputs differ from original[/yellow]")

    if debug or verbose:
        _display_debug_info(artifact_obj, result)


def _display_outputs(result):
    """Display replay outputs"""
    console.print(Panel.fit("[bold]Replay Outputs[/bold]", style="cyan"))

    # Pretty print outputs
    import json

    output_json = json.dumps(result.outputs, indent=2)
    console.print(output_json)


def _display_diff(artifact, result):
    """Display diff between original and replay"""
    console.print(Panel.fit("[bold]Output Comparison[/bold]", style="cyan"))

    if result.match:
        console.print("[green]✅ No differences - outputs match exactly[/green]")
        return

    # Show diff
    if result.diff:
        if result.diff.get("added"):
            console.print("\n[yellow]Added fields:[/yellow]")
            for key, value in result.diff["added"].items():
                console.print(f"  + {key}: {value}")

        if result.diff.get("removed"):
            console.print("\n[red]Removed fields:[/red]")
            for key, value in result.diff["removed"].items():
                console.print(f"  - {key}: {value}")

        if result.diff.get("modified"):
            console.print("\n[blue]Modified fields:[/blue]")
            for key, changes in result.diff["modified"].items():
                console.print(f"  ~ {key}:")
                console.print(f"    - Original: {changes['original']}")
                console.print(f"    + Replayed: {changes['replayed']}")


def _display_debug_info(artifact, result):
    """Display debug information"""
    console.print("\n[bold]Debug Information[/bold]")

    # Tool calls
    table = Table(title="Tool Calls")
    table.add_column("Tool", style="cyan")
    table.add_column("Cache Key", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Stubbed", style="magenta")

    for tool_call in result.tool_calls or artifact.tool_calls:
        status = "✅ Cached" if tool_call.cache_key else "❌ Not cached"
        stubbed = "yes" if tool_call.stubbed_in_replay else "no"
        table.add_row(
            tool_call.tool_name,
            tool_call.cache_key[:16] + "..." if tool_call.cache_key else "N/A",
            status,
            stubbed,
        )

    console.print(table)

    # Model config
    console.print(f"\n[bold]Model Configuration[/bold]")
    console.print(f"  Model: {artifact.llm_config.model_name}")
    console.print(f"  Temperature: {artifact.llm_config.temperature}")
    console.print(f"  Seed: {artifact.llm_config.random_seed}")
    if result.llm_state:
        console.print(f"  Top P: {result.llm_state.top_p}")
        console.print(f"  Top K: {result.llm_state.top_k}")
        console.print(f"  Max Tokens: {result.llm_state.max_tokens}")
        console.print(f"  Frequency Penalty: {result.llm_state.frequency_penalty}")
        console.print(f"  Presence Penalty: {result.llm_state.presence_penalty}")
        console.print(f"  Replay Seed: {result.llm_state.seed}")

