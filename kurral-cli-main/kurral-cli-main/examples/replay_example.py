"""
Example of replaying a .kurral artifact
"""

import asyncio

from kurral.core.replay import ReplayEngine
from kurral.models.kurral import KurralArtifact, ReplayOverrides


async def basic_replay():
    """Basic replay example"""
    # Load artifact
    artifact = KurralArtifact.load("example_artifact.kurral")

    # Create replay engine
    engine = ReplayEngine()

    # Replay
    result = await engine.replay(artifact)

    print(f"Replay completed in {result.duration_ms}ms")
    print(f"Match: {result.match}")
    print(f"Cache hits: {result.cache_hits}")


async def replay_with_overrides():
    """Replay with prompt override for testing"""
    artifact = KurralArtifact.load("example_artifact.kurral")

    # Override prompt for testing
    overrides = ReplayOverrides(
        prompt="You are a very concise assistant. Answer in one sentence.",
        temperature=0.1,
    )

    engine = ReplayEngine()
    result = await engine.replay(artifact, overrides)

    print(f"Original output: {artifact.outputs}")
    print(f"Replayed output: {result.outputs}")

    if not result.match:
        print(f"Diff: {result.diff}")


if __name__ == "__main__":
    # Run examples
    print("Example 1: Basic Replay")
    asyncio.run(basic_replay())

    print("\nExample 2: Replay with Overrides")
    asyncio.run(replay_with_overrides())

