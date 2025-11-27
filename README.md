# Kurralv3

# Kurral

**Kurral** is a powerful A/B testing and replay framework for LangChain agents that enables deterministic testing, regression detection, and performance comparison across different LLM configurations. With minimal code changes, Kurral automatically captures agent execution artifacts and provides intelligent replay capabilities.

## Overview

Kurral solves the critical challenge of testing and validating LLM agents by:

- **Automatic Artifact Generation**: Captures complete execution traces including inputs, outputs, tool calls, LLM configurations, and prompts
- **Intelligent Replay System**: Automatically determines whether to use deterministic (A) or non-deterministic (B) replay based on detected changes
- **Semantic Tool Matching**: Uses semantic similarity (85% threshold) to match and cache tool calls during replay, reducing unnecessary API calls
- **Agent Regression Scoring (ARS)**: Provides quantitative metrics to measure replay fidelity and detect regressions
- **Minimal Integration**: Requires only two simple changes to your existing agent code

## Key Features

- ✅ **Zero-Configuration Artifact Generation**: Automatically saves execution artifacts to `artifacts/` directory
- ✅ **A/B Replay Detection**: Intelligently determines replay type based on LLM, tools, prompts, and graph changes
- ✅ **Semantic Tool Caching**: Matches tool calls using semantic similarity to avoid redundant executions
- ✅ **Session-Based Artifacts**: Accumulates all interactions within a single `main()` run into one artifact
- ✅ **Comprehensive Change Detection**: Tracks changes in model, provider, parameters, tools, prompts, and graph structure
- ✅ **ARS Scoring**: Calculates Agent Regression Score based on output similarity and tool call accuracy
- ✅ **LangChain Integration**: Seamlessly works with LangChain's `AgentExecutor` and ReAct agents

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd Kurralv3

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
# From your agent directory
python ..\Kurral_tester\replay.py <artifact-id>

# Example
python ..\Kurral_tester\replay.py 4babbd1c-d250-4c7a-8e4b-25a1ac134f89
```

Kurral will automatically:
- Detect changes and determine replay type (A or B)
- Print replay results to stdout
- Save replay artifact to `replay_runs/` directory
- Report any changes detected
- Display ARS score

## How It Works

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

#### A Replay (Deterministic)
- **When**: Everything matches (same LLM, tools, prompt template, graph structure)
- **Behavior**: Returns cached outputs directly without re-executing LLM or tools
- **Use Case**: Regression testing, verifying identical behavior

#### B Replay (Non-Deterministic)
- **When**: Something changed (different LLM, model parameters, tools, or prompt template)
- **Behavior**: Re-executes LLM with semantic tool call matching (85% similarity threshold)
- **Use Case**: Testing different models, comparing performance, A/B testing

### Semantic Tool Matching

During B replay, Kurral uses semantic similarity to match tool calls:

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
python ..\Kurral_tester\replay.py <artifact-id>

# From project root
python Kurral_tester\replay.py <artifact-id>

# Using partial UUID
python Kurral_tester\replay.py 4babbd1c
```

## Replay Output

When you replay an artifact, Kurral provides detailed information:

```
[Kurral] Replay Type: B (Non-Deterministic)
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
- **`agent_replay.py`**: Main replay entry point with automatic A/B detection
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

[Your License Here]

## Support

For issues, questions, or contributions, please [open an issue](<repository-url>/issues).

---

**Note**: The `level1agentK`, `level2AgentK`, and `level3agent` directories are example agents used for testing Kurral. They demonstrate integration patterns but are not part of the core Kurral framework.
