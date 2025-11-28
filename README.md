<p align="center">
  <img width="350" height="350" alt="Kurral Logo" src="https://github.com/user-attachments/assets/248a09da-be82-4654-a5b1-0f09d45ebe4a" />
</p>

<h1 align="center">KURRAL</h1> <h3 align="center">Deterministic Testing and Replay for AI agents</h3>

<p align="center">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.9+-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/LangChain-Compatible-green" alt="LangChain Compatible" />
</p>



<p align="center">
  ⭐ If Kurral saves you hours (or dollars), please <a href="https://github.com/yourusername/kurral">star the repo</a> — it helps a lot!
</p>

**Kurral** is a powerful open-source testing and replay framework that brings control and reliability to AI agent development. It captures complete execution traces of your agents, enabling intelligent replay for regression detection, debugging, and quantifiable A/B performance comparison.

## Table of Contents
- [Why Kurral?](#why-kurral)
- [Key Features](#key-features)
- [When to Use Kurral](#when-to-use-kurral)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Deep Dive](#deep-dive)
- [Architecture](#architecture)
- [Best Practices](#best-practices)

## Why Kurral?

Testing AI agents is fundamentally different from testing traditional software:

- **Non-deterministic outputs**: LLMs don't return the same response twice
- **Expensive API calls**: Every test run costs money
- **Complex orchestration**: Multi-step tool chains are hard to debug
- **No ground truth**: How do you know if a change broke something?

Standard testing approaches (unit tests, mocks, integration tests) fall short because they assume deterministic behavior.

**Kurral's solution**: Treat agent executions as **replayable artifacts** - complete snapshots of behavior that can be validated, compared, and debugged deterministically.

## Key Features
**Automatic Artifact Generation**
- Captures complete execution traces: inputs, outputs, tool calls, LLM configs, and prompts
- Zero configuration - just add two lines to your agent code
- Session-based: accumulates all interactions within a single `main()` run

**Intelligent Replay System**

- Automatically detects changes (LLM model, tools, prompts, graph structure)
- Switches between Level 1 (deterministic) and Level 2 (exploratory) replay
- Semantic tool matching (85% threshold) caches similar tool calls to reduce API costs

**Quantifiable Regression Detection**

- Agent Regression Score (ARS) measures replay fidelity (0.0-1.0)
- Combines output similarity and tool call accuracy
- Use in CI/CD to catch regressions before deployment

**Developer-Friendly Integration**

- Works seamlessly with LangChain's `AgentExecutor` and ReAct agents
- Minimal code changes - just `@trace_agent()` decorator and `trace_agent_invoke()` wrapper
- Artifacts saved as readable JSON in `artifacts/` directory

## When to Use Kurral

- ✅ **Regression testing**: Verify that code changes don't break existing behavior
- ✅ **Model upgrades**: Test if GPT-4.5 behaves better than GPT-4 on your tasks
- ✅ **Prompt engineering**: Compare different prompt variations quantitatively
- ✅ **Debugging failures**: Reproduce and analyze production issues locally
- ✅ **CI/CD integration**: Fail builds if ARS drops below threshold


## How It Works

Kurral records the complete execution session (**Artifact**), which can include multiple user interactions, tool calls, and LLM steps within a single run of your agent's `main()` function.

> 💡 **What's an Artifact?** A `.kurral` file is a complete snapshot of your agent's execution - think of it as a "recording" that captures every LLM call, tool execution, and decision point. You can replay this recording later to verify behavior or test changes.

You can then replay this comprehensive session artifact against new code, different LLM configurations, or modified prompts. This allows you to verify behavioral consistency across the entire user dialogue, not just a single prompt-response cycle.

**Intelligent Replay Levels**
Kurral detects what changed between runs and automatically switches strategies based on the replay level required:

- **Level 1 Replay** (Deterministic): Logic changes? This mode achieves true deterministic testing of your agent's internal logic. It mocks the LLM entirely using the cached output from the artifact to verify that your agent code and tool orchestration remain identical (Zero API cost).

    - ✅ Zero API costs
    - ✅ Perfect for regression testing
    - ✅ Verifies logic without re-running LLM

- **Level 2 Replay** (Exploratory): Model or Prompt changes? This mode facilitates A/B testing. It re-runs the LLM live but intelligently caches tool calls using semantic matching to benchmark the quality of the new model or prompt against the original run.
  
    - ✅ Benchmark new models against original runs
    - ✅ Test prompt variations
    - ✅ Reduced API costs via semantic tool caching

With minimal code changes (just two lines), Kurral's captured artifacts unlock intelligent, production-ready replay capabilities.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kurral.git
cd kurral

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Integrate Kurral into Your Agent

Add Kurral to your existing LangChain agent with just two changes:

```python
from Kurral_tester.agent_decorator import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    # Your existing agent setup
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    tools = create_tools()
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Replace agent_executor.invoke() with trace_agent_invoke()
    result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    return result
```

That's it! Kurral will automatically:
- Generate artifacts in `artifacts/` directory
- Capture all interactions within the session
- Save a single artifact per `main()` execution

### 2. Run Your Agent

```bash
python agent.py
```

After execution, you'll see:
```
[Kurral] Session artifact saved: artifacts/4babbd1c-d250-4c7a-8e4b-25a1ac134f89.kurral
[Kurral] Run ID: local_agent_1234567890
[Kurral] Kurral ID: 4babbd1c-d250-4c7a-8e4b-25a1ac134f89
[Kurral] Total interactions: 1
```

### 3. Replay an Artifact
```bash
# From your agent directory, replay the artifact (pass ID or unique prefix)
python ../Kurral_tester/replay.py <artifact_id>

# Example
python ../Kurral_tester/replay.py 4babbd1c-d250-4c7a-8e4b-25a1ac134f89
```


Kurral will automatically:
- Detect changes and determine replay type (Level 1 or Level 2)
- Print replay results to stdout
- Save replay artifact to `replay_runs/` directory
- Report any changes detected
- Display ARS score

## Deep Dive
Want to understand how Kurral works under the hood? Read on.

### What’s in a `.kurral` artifact?
Human-readable JSON with everything:

- All user/agent hashed messages
- Tool calls + results
- Exact prompt templates (resolved)
- LLM config (model, temp, seed, provider)
- Graph/tool schema hash

### Artifact Generation

When you run your agent with Kurral, it automatically captures:

- **Inputs**: All user inputs for each interaction
- **Outputs**: Agent responses and final outputs
- **Tool Calls**: Complete tool execution traces (name, inputs, outputs, timestamps)
- **LLM Configuration**: Model name, provider, temperature, seed, and other parameters
- **Prompt**: Resolved prompt template with variables
- **Graph Version**: Hash of tool schemas and graph structure
- **Metadata**: Timestamps, duration, errors, token usage

All interactions within a single `main()` execution are accumulated into one session artifact.

### Replay Types

Kurral uses intelligent change detection to determine the appropriate replay strategy:

#### Level 1 Replay (Deterministic)
- **When**: Everything matches (same LLM, tools, prompt template, graph structure)
- **Behavior**: Returns cached outputs directly without re-executing LLM or tools
- **Use Case**: Regression testing, verifying identical behavior

#### Level 2 Replay (Non-Deterministic)
- **When**: Something changed (different LLM, model parameters, tools, or prompt template)
- **Behavior**: Re-executes LLM with semantic tool call matching (85% similarity threshold)
- **Use Case**: Testing different models, comparing performance, A/B testing

### Semantic Tool Matching

During Level 2 replay, Kurral uses semantic similarity to match tool calls:

- **Exact Match**: If tool name and inputs match exactly → use cached output
- **Semantic Match**: If similarity ≥ 85% → use cached output (no tool execution)
- **New Call**: If similarity < 85% → execute tool and cache result

This ensures:
- Reduced API costs (fewer tool executions)
- Faster replay execution
- Accurate cache hit/miss tracking

### Agent Regression Score (ARS)

ARS provides a quantitative measure of replay fidelity:

```
ARS = (Output Similarity + Tool Accuracy) / 2
```

Where:
- **Output Similarity**: Semantic similarity between original and replayed outputs
- **Tool Accuracy**: Ratio of correctly matched tool calls

ARS ranges from 0.0 to 1.0, where 1.0 indicates perfect replay fidelity.

## Usage Examples

### Basic Integration

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from Kurral_tester.agent_decorator import trace_agent, trace_agent_invoke

@trace_agent()
def main():
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    tools = create_tools()
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)
    
    user_input = input("You: ")
    result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    print(f"Agent: {result['output']}")

if __name__ == "__main__":
    main()
```

### Multiple Interactions

Kurral automatically accumulates all interactions:

```python
@trace_agent()
def main():
    # ... setup agent ...
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        
        result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
        print(f"Agent: {result['output']}")
    
    # All interactions saved in one artifact when main() exits
```

### Replay from Anywhere
```bash
# From agent directory
cd my_agent
python ../Kurral_tester/replay.py <artifact-id>

# From project root
python Kurral_tester/replay.py <artifact-id>

# Using partial UUID
python Kurral_tester/replay.py 4babbd1c
```

...

### Replay Output

When you replay an artifact, Kurral provides detailed information:

```
[Kurral] Replay Type: Level 2 (Non-Deterministic)
[Kurral] Changes Detected:
  - LLM Model: gpt-4 → llama-3.3-70b-versatile
  - Provider: openai → groq

[Kurral] Replay Execution:
  - Cache Hits: 1
  - New Tool Calls: 2
  - Unused Tool Calls: 0

[Kurral] ARS Score: 0.626
  - Output Similarity: 0.5515
  - Tool Accuracy: 0.8

[Kurral] Replay artifact saved: replay_runs/5a9d2627-4dec-4954-96af-b127ba038056.kurral
```

## Architecture

### Core Components

- **`agent_decorator.py`**: `@trace_agent()` decorator and `trace_agent_invoke()` function
- **`agent_replay.py`**: Main replay entry point with automatic Level 1/Level 2 detection
- **`replay_detector.py`**: Change detection logic and determinism scoring
- **`tool_stubber.py`**: Semantic tool matching and caching during B replay
- **`ars_scorer.py`**: Agent Regression Score calculation
- **`artifact_manager.py`**: Artifact storage and retrieval
- **`artifact_generator.py`**: Artifact generation from execution traces

### Artifact Structure

Kurral artifacts (`.kurral` files) are JSON files containing:

```json
{
  "run_id": "local_agent_1234567890",
  "kurral_id": "4babbd1c-d250-4c7a-8e4b-25a1ac134f89",
  "inputs": {
    "interactions": [...]
  },
  "outputs": {
    "interactions": [...]
  },
  "llm_config": {
    "model_name": "gpt-4",
    "provider": "openai",
    "parameters": {...}
  },
  "tool_calls": [...],
  "resolved_prompt": {...},
  "graph_version": {...}
}
```

### Current Limitations (we’re working on them!)

- Only ReAct-style and LCEL agents fully supported (no native LangGraph streaming yet)
- Vision / image inputs not captured
- No built-in dashboard (yet – artifacts are JSON, just open one in VS Code/any editor)



## Best Practices

1. **Always pass `llm` parameter**: `trace_agent_invoke(agent_executor, input_data, llm=llm)` ensures accurate LLM config extraction
2. **Use session artifacts**: Let Kurral accumulate interactions automatically within `main()`
3. **Check ARS scores**: Monitor ARS to detect regressions when testing different models
4. **Review replay artifacts**: Check `replay_runs/` directory for detailed replay analysis
5. **Handle optional dependencies**: Kurral gracefully handles missing optional LLM packages

## Requirements

- Python 3.9+
- LangChain
- Pydantic
- Optional: OpenAI, Google Generative AI, Groq, or other LLM providers

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Community
Join our Discord → [https://discord.gg/pan6GRRV]

## Support

For issues, questions, or contributions, please [open an issue](https://github.com/yourusername/kurral/issues).


---

Star this repo if Kurral just saved you $50 in OpenAI credits.

Made with ❤️ for the agent-building community.

**Note**: The `level1agentK`, `level2AgentK`, and `level3agent` directories are example agents used for testing Kurral. They demonstrate integration patterns but are not part of the core Kurral framework.
