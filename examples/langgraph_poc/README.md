# LangGraph POC Example

**Status:** Proof of Concept
**Purpose:** Validate Kurral integration with LangGraph v1

## What This Tests

This example validates:
- ✅ `@trace_graph()` decorator works with StateGraph
- ✅ Graph execution is traced
- ✅ Artifact is generated with graph metadata
- ✅ Basic node tracking works

## Running the Example

```bash
# Install LangGraph if not installed
pip install langgraph>=1.0.0

# Run from project root
cd /path/to/Kurralv3
python examples/langgraph_poc/simple_graph.py
```

## Expected Output

```
============================================================
LangGraph POC Test - Simple State Graph
============================================================

[Building Graph]
  ✓ Graph structure defined
  ✓ Nodes: process, format
  ✓ Entry point: process
  ✓ Graph compiled successfully

[Executing Graph]
  Input: ['Hello', 'World', 'Test']

  [Node: process] Processing 3 messages...
  [Node: format] Creating output: FINAL: Processed 3 messages (Total: 3)

[Execution Complete]
  Output: FINAL: Processed 3 messages (Total: 3)
  Count: 3

============================================================
✓ POC Test Completed
============================================================

[Kurral] LangGraph artifact saved: artifacts/...kurral
[Kurral] Kurral ID: ...
[Kurral] Graph nodes: 2 nodes executed

✓ Artifact created: ...kurral
  Location: .../artifacts
```

## What Gets Captured

The generated `.kurral` artifact contains:
- Graph structure (nodes, edges, entry point)
- Node execution trace (enter/exit events)
- Input and output states
- Execution timing
- Framework metadata (langgraph)

## Known Limitations (POC)

- ❌ LLM config not extracted (placeholder used)
- ❌ Tool calls within nodes not captured yet
- ❌ Streaming not supported
- ❌ Checkpoint/persistence not tracked
- ❌ Full state details not captured (only keys)

These are expected for POC - full implementation will address them.

## For Dev Team

**Questions to answer:**
1. Does the artifact generation work?
2. Does graph structure get captured?
3. Does it interfere with graph execution?
4. Are there any errors?

**Next Steps if POC succeeds:**
1. Extract real LLM config from graph nodes
2. Capture tool calls from within nodes
3. Add replay logic
4. Full state tracking
5. Streaming support
