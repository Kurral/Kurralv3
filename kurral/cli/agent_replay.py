"""
Simple replay CLI for agents
Usage: python -m kurral.cli.agent_replay <run_id> or --latest
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kurral.models.kurral import KurralArtifact, ModelConfig, LLMParameters
from kurral.artifact_manager import ArtifactManager
from kurral.replay_detector import ReplayDetector
from kurral.replay_executor import ReplayExecutor
from kurral.artifact_generator import ArtifactGenerator
from kurral.replay import replay_artifact

console = Console()


@click.command()
@click.argument("run_id", required=False)
@click.option(
    "--latest",
    is_flag=True,
    help="Replay the latest artifact",
)
@click.option(
    "--artifacts-dir",
    type=click.Path(exists=False),
    help="Path to artifacts directory (defaults to ./artifacts)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def replay(run_id: Optional[str], latest: bool, artifacts_dir: Optional[str], verbose: bool):
    """
    Replay an agent artifact
    
    Examples:
        # Replay by run_id
        python -m kurral.cli.agent_replay local_agent_1234567890
        
        # Replay latest
        python -m kurral.cli.agent_replay --latest
    """
    # Determine artifacts directory
    if artifacts_dir:
        artifacts_path = Path(artifacts_dir)
    else:
        # Default to ./artifacts in current directory
        artifacts_path = Path.cwd() / "artifacts"
    
    if not artifacts_path.exists():
        console.print(f"[red]Error: Artifacts directory not found: {artifacts_path}[/red]")
        raise click.Abort()
    
    # Determine agent directory for config loading
    agent_dir = artifacts_path.parent if artifacts_path.name == "artifacts" else None
    
    artifact_manager = ArtifactManager(storage_path=artifacts_path, agent_dir=agent_dir)
    
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
    else:
        console.print("[red]Error: Must provide run_id or --latest[/red]")
        raise click.Abort()
    
    console.print(f"\n[cyan]Replaying artifact: {artifact_obj.kurral_id}[/cyan]")
    console.print(f"[dim]Original run: {artifact_obj.run_id}[/dim]\n")
    
    # Determine replay_runs directory
    replay_runs_dir = artifacts_path.parent / "replay_runs"
    replay_runs_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the replay_artifact function from replay.py
    try:
        result = replay_artifact(
            run_id=artifact_obj.run_id,
            storage_path=str(artifacts_path),
            verbose=verbose,
        )
        
        # Display results
        console.print(f"\n[green]Replay completed[/green]")
        console.print(f"[dim]Replay type: {result['replay_type']}[/dim]")
        console.print(f"[dim]Duration: {result['duration_ms']}ms[/dim]")
        console.print(f"[dim]Cache hits: {result['cache_hits']}[/dim]")
        console.print(f"[dim]Cache misses: {result['cache_misses']}[/dim]")
        
        if result.get('outputs'):
            console.print("\n[bold]Outputs:[/bold]")
            import json
            output_json = json.dumps(result['outputs'], indent=2)
            console.print(output_json)
        
        # Generate replay artifact
        replay_artifact_obj = _generate_replay_artifact(
            original_artifact=artifact_obj,
            replay_result=result,
            replay_runs_dir=replay_runs_dir,
        )
        
        if replay_artifact_obj:
            # Create replay storage backend with replay_runs path prefix
            from kurral.config import get_storage_config
            from kurral.storage import create_storage_backend
            
            replay_config = get_storage_config(agent_dir)
            replay_backend = create_storage_backend(
                replay_config,
                replay_runs_dir,
                agent_dir=agent_dir,
                path_prefix="replay_runs"
            )
            
            replay_result = replay_backend.save(replay_artifact_obj)
            if not replay_result.success:
                console.print(f"[yellow]Warning: Failed to save replay artifact: {replay_result.error}[/yellow]")
            else:
                replay_path = replay_result.local_path or replay_runs_dir / f"{replay_artifact_obj.kurral_id}.kurral"
                console.print(f"\n[green]Replay artifact saved: {replay_path}[/green]")
                console.print(f"[dim]Replay ID: {replay_artifact_obj.run_id}[/dim]")
        
        # Report new and unused tool calls if any
        new_tool_calls = result.get('new_tool_calls', [])
        unused_tool_calls = result.get('unused_tool_calls', [])
        
        if new_tool_calls:
            console.print(f"\n[yellow]New tool calls (not in original artifact): {len(new_tool_calls)}[/yellow]")
            for tc in new_tool_calls:
                if isinstance(tc, dict):
                    console.print(f"  - {tc.get('tool_name', 'unknown')}: {tc.get('input', {})}")
                else:
                    console.print(f"  - {tc.tool_name}: {tc.input}")
        
        if unused_tool_calls:
            console.print(f"\n[yellow]Unused tool calls (from original but not used): {len(unused_tool_calls)}[/yellow]")
            for tc in unused_tool_calls:
                if isinstance(tc, dict):
                    console.print(f"  - {tc.get('tool_name', 'unknown')}: {tc.get('input', {})}")
                else:
                    console.print(f"  - {tc.tool_name}: {tc.input}")
        
    except Exception as e:
        console.print(f"[red]Error during replay: {str(e)}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


def _generate_replay_artifact(
    original_artifact: KurralArtifact,
    replay_result: dict,
    replay_runs_dir: Path,
) -> Optional[KurralArtifact]:
    """Generate a replay artifact with references to original"""
    try:
        from datetime import datetime
        from uuid import uuid4
        
        generator = ArtifactGenerator()
        
        # Create replay artifact
        replay_run_id = f"replay_{original_artifact.run_id}_{int(datetime.utcnow().timestamp())}"
        
        # Include original artifact references in metadata
        replay_inputs = {
            "original_kurral_id": str(original_artifact.kurral_id),
            "original_run_id": original_artifact.run_id,
            "replay_type": replay_result.get('replay_type', 'unknown'),
            "determinism_score": replay_result.get('determinism_score', 0.0),
        }
        
        # Include new and unused tool calls info
        replay_outputs = replay_result.get('outputs', {})
        new_tool_calls = replay_result.get('new_tool_calls', [])
        unused_tool_calls = replay_result.get('unused_tool_calls', [])
        
        if new_tool_calls:
            replay_outputs['new_tool_calls'] = [
                {
                    "tool_name": tc.tool_name if hasattr(tc, 'tool_name') else tc.get('tool_name', 'unknown'),
                    "input": tc.input if hasattr(tc, 'input') else tc.get('input', {}),
                    "output": tc.output if hasattr(tc, 'output') else tc.get('output', {}),
                    "outside_original_artifact": True,
                }
                for tc in new_tool_calls
            ]
        
        if unused_tool_calls:
            replay_outputs['unused_tool_calls'] = [
                {
                    "tool_name": tc.tool_name if hasattr(tc, 'tool_name') else tc.get('tool_name', 'unknown'),
                    "input": tc.input if hasattr(tc, 'input') else tc.get('input', {}),
                    "output": tc.output if hasattr(tc, 'output') else tc.get('output', {}),
                }
                for tc in unused_tool_calls
            ]
        
        replay_artifact = generator.generate(
            run_id=replay_run_id,
            tenant_id=original_artifact.tenant_id,
            inputs=replay_inputs,
            outputs=replay_outputs,
            llm_config=original_artifact.llm_config,  # Use original config
            resolved_prompt=original_artifact.resolved_prompt,  # Use original prompt
            tool_calls=replay_result.get('tool_calls', []),
            duration_ms=replay_result.get('duration_ms', 0),
            graph_version=original_artifact.graph_version,
        )
        
        return replay_artifact
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to generate replay artifact: {e}[/yellow]")
        return None


if __name__ == "__main__":
    replay()

