"""
Simple CLI for replaying Kurral artifacts
Usage: python -m Kurral_tester.cli.replay_cli <artifact_path> [options]
Or: kurral-replay <artifact_path> [options]
"""

import sys
import json
from pathlib import Path
import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Kurral_tester.replay import replay_artifact


@click.command()
@click.argument("artifact", type=str, required=False)
@click.option(
    "--latest",
    "-l",
    is_flag=True,
    help="Replay the latest artifact",
)
@click.option(
    "--run-id",
    help="Replay artifact by run_id",
)
@click.option(
    "--storage-path",
    type=click.Path(exists=False),
    help="Path to artifact storage (defaults to ./artifacts)",
)
@click.option(
    "--llm-client",
    help="LLM client type (openai, anthropic) - required for B replay",
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
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def main(
    artifact: str,
    latest: bool,
    run_id: str,
    storage_path: str,
    llm_client: str,
    current_model: str,
    current_temperature: float,
    verbose: bool,
):
    """
    Replay a Kurral artifact
    
    Examples:
        # Replay by file path
        kurral-replay artifacts/xxx.kurral
        
        # Replay latest artifact
        kurral-replay --latest
        
        # Replay with verbose output
        kurral-replay artifacts/xxx.kurral --verbose
    """
    try:
        result = replay_artifact(
            artifact_path=artifact,
            run_id=run_id,
            latest=latest,
            storage_path=storage_path,
            llm_client=llm_client,
            current_model=current_model,
            current_temperature=current_temperature,
            verbose=verbose,
        )
        
        if verbose:
            print(f"\n[SUCCESS] Replay completed in {result['duration_ms']}ms")
            print(f"Replay type: {result['replay_type']}")
            print(f"Cache hits: {result['cache_hits']}, misses: {result['cache_misses']}")
            if result['validation']:
                print(f"Hash match: {result['validation']['hash_match']}")
            
            # Show final answer (clean output for both A and B replay)
            print(f"\n=== Final Answer ===")
            outputs = result['outputs']
            # Try to extract the most relevant output
            if isinstance(outputs, dict):
                # Look for common output keys
                if 'result' in outputs:
                    print(outputs['result'])
                elif 'full_text' in outputs:
                    print(outputs['full_text'])
                elif 'output' in outputs:
                    print(outputs['output'])
                elif 'answer' in outputs:
                    print(outputs['answer'])
                else:
                    # Fallback: show first string value or formatted dict
                    for key, value in outputs.items():
                        if isinstance(value, str) and value.strip():
                            print(f"{value}")
                            break
                    else:
                        # Last resort: show formatted JSON
                        print(json.dumps(outputs, indent=2, default=str))
            else:
                print(str(outputs))
        else:
            # Simple output
            print(f"Replay Type: {result['replay_type']}")
            print(f"Duration: {result['duration_ms']}ms")
            print(f"Cache: {result['cache_hits']} hits, {result['cache_misses']} misses")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

