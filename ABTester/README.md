# Kurral Replay Mechanism

A/B replay system for agent testing that automatically determines whether to use A replay (full artifact replay) or B replay (LLM re-execution with cached tools) based on detected changes.

## Overview

This replay mechanism provides:

- **A Replay**: When everything matches (LLM, tools, graph, prompt) - returns artifact outputs directly
- **B Replay**: When something changed - re-executes LLM with cached tool calls

## Architecture

### Components

1. **ReplayDetector** (`replay_detector.py`): Detects changes between artifact and current execution context
2. **ArtifactManager** (`artifact_manager.py`): Manages storage and retrieval of kurral artifacts
3. **ReplayExecutor** (`replay_executor.py`): Executes A or B replay based on detection
4. **CLI** (`cli/replay_cmd.py`): Command-line interface for replay

### Change Detection

The system detects changes in:
- LLM model name/version
- LLM parameters (temperature, seed, top_p, etc.)
- Tool schemas (graph_version.tool_schemas_hash)
- Graph structure (graph_version.graph_hash)
- Prompt (final_text_hash, template_hash, variables_hash)
- Inputs

If **any** change is detected, B replay is used. Otherwise, A replay is used.

## Usage

### CLI Command

```bash
# Replay by file path
python -m ABTester.cli.replay_cmd artifact.kurral

# Replay by run_id
python -m ABTester.cli.replay_cmd --run-id my_run_123

# Replay latest artifact
python -m ABTester.cli.replay_cmd --latest

# Replay with change detection (B replay if model changed)
python -m ABTester.cli.replay_cmd artifact.kurral --current-model gpt-4-turbo

# Show diff between original and replay
python -m ABTester.cli.replay_cmd artifact.kurral --diff

# Debug mode
python -m ABTester.cli.replay_cmd artifact.kurral --debug
```

### Programmatic Usage

```python
from ABTester.models.kurral import KurralArtifact
from ABTester.artifact_manager import ArtifactManager
from ABTester.replay_detector import ReplayDetector
from ABTester.replay_executor import ReplayExecutor

# Load artifact
manager = ArtifactManager(storage_path="./artifacts")
artifact = manager.load_by_run_id("my_run_123")

# Detect changes
detector = ReplayDetector()
detection_result = detector.detect_changes(
    artifact=artifact,
    current_llm_config=current_llm_config,  # Optional
    current_prompt=current_prompt,  # Optional
    current_graph_version=current_graph_version,  # Optional
)

# Execute replay
executor = ReplayExecutor()
result = await executor.execute_replay(
    artifact=artifact,
    detection_result=detection_result,
    llm_client=llm_client,  # Required for B replay
)
```

## Testing

Run the test suite:

```bash
python ABTester/test_replay.py
```

This tests:
- A replay detection (everything matches)
- B replay detection (model change)
- B replay detection (temperature change)
- B replay detection (prompt change)
- B replay detection (graph change)
- Artifact storage and retrieval

## Storage

Artifacts are stored locally by default in `./artifacts/`. You can specify a custom path:

```python
manager = ArtifactManager(storage_path="/path/to/artifacts")
```

## Integration with LangGraph

To integrate with LangGraph agents, you'll need to:

1. Capture artifacts during agent execution (using the decorator pattern from kurral-cli)
2. Store artifacts using `ArtifactManager`
3. Use `ReplayDetector` to determine replay type
4. Use `ReplayExecutor` to execute replay

## Notes

- This implementation is independent of kurral-cli (no imports from kurral-cli)
- Code was copied from kurral-cli where needed, not imported
- The A/B replay types are independent of the existing A/B/C determinism levels in kurral-cli
- B replay requires an LLM client (OpenAI or Anthropic supported)

