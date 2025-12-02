"""
Enhanced replay command with A/B replay detection
Extends the kurral replay command with automatic A/B replay type detection
"""

import asyncio
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import from local modules (not kurral-cli)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kurral.models.kurral import KurralArtifact, ModelConfig, ResolvedPrompt, GraphVersion
from kurral.artifact_manager import ArtifactManager
from kurral.replay_detector import ReplayDetector
from kurral.replay_executor import ReplayExecutor

console = Console()


@click.command()
@click.argument("artifact", type=str, required=False)
@click.option(
    "--run-id",
    help="Replay artifact by run_id",
)
@click.option(
    "--latest",
    is_flag=True,
    help="Replay the latest artifact",
)
@click.option(
    "--storage-path",
    type=click.Path(exists=False),
    help="Path to artifact storage (defaults to ./artifacts)",
)
@click.option(
    "--llm-client",
    help="LLM client type (openai, anthropic, etc.) - required for B replay",
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
@click.option(
    "--current-model",
    help="Current model name (for change detection)",
)
@click.option(
    "--current-temperature",
    type=float,
    help="Current temperature (for change detection)",
)
def replay(
    artifact: Optional[str],
    run_id: Optional[str],
    latest: bool,
    storage_path: Optional[str],
    llm_client: Optional[str],
    diff: bool,
    debug: bool,
    verbose: bool,
    current_model: Optional[str],
    current_temperature: Optional[float],
):
    """
    Replay a .kurral artifact with automatic A/B replay detection
    
    A replay: Everything matches - returns artifact outputs directly
    B replay: Something changed - re-executes LLM with cached tool calls
    
    Examples:
        # Replay by file path
        kurral replay artifact.kurral
        
        # Replay by run_id
        kurral replay --run-id my_run_123
        
        # Replay latest artifact
        kurral replay --latest
        
        # Replay with change detection (B replay if model changed)
        kurral replay artifact.kurral --current-model gpt-4-turbo
    """
    # Determine storage path
    if storage_path:
        storage = Path(storage_path)
    else:
        storage = Path("./artifacts")
    
    # Determine agent directory for config loading
    agent_dir = storage.parent if storage.name == "artifacts" else None
    
    artifact_manager = ArtifactManager(storage_path=storage, agent_dir=agent_dir)
    
    # Ensure R2 migration before loading artifacts
    if artifact_manager.using_r2:
        console.print("[dim]Loading R2...[/dim]")
        migration_stats = artifact_manager.ensure_r2_migration(show_message=False)
        if migration_stats["migrated"] > 0:
            console.print(f"[green]Migrated {migration_stats['migrated']} artifact(s) to R2[/green]")
            if migration_stats["skipped"] > 0:
                console.print(f"[dim]Skipped {migration_stats['skipped']} (already in R2)[/dim]")
        elif migration_stats.get("message"):
            console.print(f"[dim]{migration_stats['message']}[/dim]")
    
    # Load artifact
    artifact_obj = None
    
    if latest:
        artifact_obj = artifact_manager.load_latest()
        if not artifact_obj:
            console.print("[red]Error: No artifacts found[/red]")
            raise click.Abort()
    elif run_id:
        artifact_obj = artifact_manager.load_by_run_id(run_id)
        if not artifact_obj:
            console.print(f"[red]Error: Artifact with run_id '{run_id}' not found[/red]")
            raise click.Abort()
    elif artifact:
        # Try as file path first
        artifact_path = Path(artifact)
        if artifact_path.exists():
            artifact_obj = KurralArtifact.load(artifact_path)
        else:
            # Try as UUID
            try:
                kurral_id = UUID(artifact)
                artifact_obj = artifact_manager.load(kurral_id)
            except ValueError:
                console.print(f"[red]Error: Artifact '{artifact}' not found[/red]")
                raise click.Abort()
    else:
        console.print("[red]Error: Must provide artifact, --run-id, or --latest[/red]")
        raise click.Abort()
    
    console.print(f"\n[cyan]Replaying artifact: {artifact_obj.kurral_id}[/cyan]")
    console.print(f"[dim]Original run: {artifact_obj.run_id}[/dim]\n")
    
    # Build current execution context for change detection
    current_llm_config = None
    current_prompt = None
    current_graph_version = None
    
    if current_model or current_temperature is not None:
        # Build current LLM config from artifact + overrides
        from models.kurral import LLMParameters
        
        params = artifact_obj.llm_config.parameters
        llm_params = LLMParameters(
            temperature=current_temperature if current_temperature is not None else params.temperature,
            top_p=params.top_p,
            top_k=params.top_k,
            max_tokens=params.max_tokens,
            frequency_penalty=params.frequency_penalty,
            presence_penalty=params.presence_penalty,
            seed=params.seed,
        )
        
        current_llm_config = ModelConfig(
            model_name=current_model or artifact_obj.llm_config.model_name,
            model_version=artifact_obj.llm_config.model_version,
            provider=artifact_obj.llm_config.provider,
            parameters=llm_params,
        )
    
    # Determine replay type (A or B) based on determinism score and changes
    detector = ReplayDetector()
    detection_result = detector.determine_replay_type(
        artifact=artifact_obj,
        current_llm_config=current_llm_config,
        current_prompt=current_prompt,
        current_graph_version=current_graph_version,
    )
    
    # Display detection result
    determinism_score = detection_result.changes.get("determinism_score", 0.0)
    threshold = detection_result.changes.get("determinism_threshold", 0.8)
    
    console.print(f"[bold]Replay Type: {detection_result.replay_type}[/bold]")
    console.print(f"[dim]Determinism Score: {determinism_score:.2f} (threshold: {threshold:.2f})[/dim]")
    
    # Filter out determinism_score and threshold from changes display
    display_changes = {k: v for k, v in detection_result.changes.items() 
                      if k not in ["determinism_score", "determinism_threshold"]}
    
    if display_changes:
        console.print(f"[yellow]Changes detected:[/yellow]")
        for key, change in display_changes.items():
            console.print(f"  - {key}: {change}")
    else:
        console.print("[green]No changes detected[/green]")
    
    # Get LLM client if needed for B replay
    llm_client_obj = None
    if detection_result.replay_type == "B":
        if not llm_client:
            # Try to auto-detect from environment
            if os.getenv("OPENAI_API_KEY"):
                llm_client = "openai"
            elif os.getenv("ANTHROPIC_API_KEY"):
                llm_client = "anthropic"
        
        if llm_client == "openai":
            try:
                from openai import AsyncOpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    console.print("[red]Error: OPENAI_API_KEY not set (required for B replay)[/red]")
                    raise click.Abort()
                llm_client_obj = AsyncOpenAI(api_key=api_key)
            except ImportError:
                console.print("[red]Error: openai package not installed (required for B replay)[/red]")
                raise click.Abort()
        elif llm_client == "anthropic":
            try:
                from anthropic import AsyncAnthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    console.print("[red]Error: ANTHROPIC_API_KEY not set (required for B replay)[/red]")
                    raise click.Abort()
                llm_client_obj = AsyncAnthropic(api_key=api_key)
            except ImportError:
                console.print("[red]Error: anthropic package not installed (required for B replay)[/red]")
                raise click.Abort()
        else:
            console.print(f"[yellow]Warning: LLM client '{llm_client}' not supported, falling back to A replay[/yellow]")
            detection_result.replay_type = "A"
    
    # Execute replay
    executor = ReplayExecutor()
    result = asyncio.run(
        executor.execute_replay(
            artifact=artifact_obj,
            detection_result=detection_result,
            llm_client=llm_client_obj,
        )
    )
    
    # Display results
    if diff:
        _display_diff(artifact_obj, result)
    else:
        _display_outputs(result)
    
    # Summary
    console.print(f"\n[green][SUCCESS] Replay completed in {result.duration_ms}ms[/green]")
    console.print(f"[dim]Replay type: {detection_result.replay_type}[/dim]")
    console.print(f"[dim]Cache hits: {result.cache_hits}[/dim]")
    console.print(f"[dim]Cache misses: {result.cache_misses}[/dim]")
    
    if result.validation:
        hash_status = "[SUCCESS]" if result.validation.hash_match else "[WARNING]"
        console.print(
            f"[dim]Hash match:[/dim] {hash_status} "
            f"({result.validation.original_hash[:8]} -> {result.validation.replay_hash[:8]})"
        )
        struct_status = "[SUCCESS]" if result.validation.structural_match else "[WARNING]"
        console.print(
            f"[dim]Structural match:[/dim] {struct_status}"
        )
    
    if result.replay_metadata:
        console.print(
            f"[dim]Replay ID:[/dim] {result.replay_metadata.replay_id} "
            f"(record: {result.replay_metadata.record_ref})"
        )
    
    if result.match:
        console.print("[green][SUCCESS] Outputs match original[/green]")
    else:
        console.print("[yellow][WARNING] Outputs differ from original[/yellow]")
    
    if debug or verbose:
        _display_debug_info(artifact_obj, result, detection_result)


def _display_outputs(result):
    """Display replay outputs"""
    console.print(Panel.fit("[bold]Replay Outputs[/bold]", style="cyan"))
    
    import json
    output_json = json.dumps(result.outputs, indent=2)
    console.print(output_json)


def _display_diff(artifact, result):
    """Display diff between original and replay"""
    console.print(Panel.fit("[bold]Output Comparison[/bold]", style="cyan"))
    
    if result.match:
        console.print("[green][SUCCESS] No differences - outputs match exactly[/green]")
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


def _display_debug_info(artifact, result, detection_result):
    """Display debug information"""
    console.print("\n[bold]Debug Information[/bold]")
    
    # Change detection
    console.print(f"\n[bold]Change Detection:[/bold]")
    console.print(f"  Replay type: {detection_result.replay_type}")
    console.print(f"  Changes: {len(detection_result.changes)}")
    console.print(f"  Matches: {len(detection_result.matches)}")
    
    # Tool calls
    table = Table(title="Tool Calls")
    table.add_column("Tool", style="cyan")
    table.add_column("Cache Key", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Stubbed", style="magenta")
    
    for tool_call in result.tool_calls or artifact.tool_calls:
        status = "[CACHED]" if tool_call.cache_key else "[NOT CACHED]"
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
    console.print(f"  Temperature: {artifact.llm_config.parameters.temperature}")
    console.print(f"  Seed: {artifact.llm_config.parameters.seed}")
    if result.llm_state:
        console.print(f"  Top P: {result.llm_state.top_p}")
        console.print(f"  Top K: {result.llm_state.top_k}")
        console.print(f"  Max Tokens: {result.llm_state.max_tokens}")


if __name__ == "__main__":
    replay()
