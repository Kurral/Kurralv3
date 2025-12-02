<p align="center">
  <img width="350" height="350" alt="Kurral Logo" src="https://github.com/user-attachments/assets/248a09da-be82-4654-a5b1-0f09d45ebe4a" />
</p>

<h1 align="center">KURRAL</h1>
<h3 align="center">Deterministic Testing and Replay for AI Agents</h3>

<p align="center">
  <img src="https://img.shields.io/pypi/v/kurral" alt="PyPI" />
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.9+-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/LangChain-Compatible-green" alt="LangChain Compatible" />
</p>

<p align="center">
  ⭐ If Kurral saves you hours (or dollars), please <a href="https://github.com/kurral/kurralv3">star the repo</a> — it helps a lot!
</p>

---

**Kurral** is a powerful open-source testing and replay framework that brings control and reliability to AI agent development. It captures complete execution traces of your agents, enabling intelligent replay for regression detection, debugging, and quantifiable A/B performance comparison.

## Table of Contents

- [Why Kurral?](#why-kurral)
- [Key Features](#key-features)
- [When to Use Kurral](#when-to-use-kurral)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Centralized Storage (Kurral API)](#centralized-storage-kurral-api)
- [Deep Dive](#deep-dive)
- [Architecture](#architecture)
- [Best Practices](#best-practices)
- [Contributing](#contributing)

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

**Side Effect Protection**: Prevents dangerous operations (emails, payments, writes) during replay

**Quantifiable Regression Detection**

- Agent Regression Score (ARS) measures replay fidelity (0.0-1.0)
- Combines output similarity and tool call accuracy
- Use in CI/CD to catch regressions before deployment

**Developer-Friendly Integration**

- Works seamlessly with LangChain's `AgentExecutor` and ReAct agents
- Minimal code changes - just `@trace_agent()` decorator and `trace_agent_invoke()` wrapper
- Artifacts saved as readable JSON in `artifacts/` directory
- **Intelligent Side Effect Detection**: Auto-generates configuration with smart suggestions based on tool names and descriptions

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

- **Level 2 Replay** (Non-Deterministic / Exploratory): Model or Prompt changes? This mode facilitates A/B testing. It re-runs the LLM live but intelligently caches tool calls using semantic matching to benchmark the quality of the new model or prompt against the original run.
  
    - ✅ Benchmark new models against original runs
    - ✅ Test prompt variations
    - ✅ Reduced API costs via semantic tool caching

With minimal code changes (just two lines), Kurral's captured artifacts unlock intelligent, production-ready replay capabilities.

## Installation

### From PyPI (Recommended)

```bash
pip install kurral
```

### From Source

```bash
# Clone the repository
git clone https://github.com/kurral/kurralv3.git
cd kurralv3

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Quick Start

### 1. Integrate Kurral into Your Agent

Add Kurral to your existing LangChain agent with just two changes:

```python
from kurral import trace_agent, trace_agent_invoke

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

### 3. Configure Side Effects (First Time Only)

On your first replay, Kurral will auto-generate a `side_effect/side_effects.yaml` file with intelligent suggestions:

```yaml
tools:
  send_email: false    # Side effect - blocked during replay
  tavily_search: true  # Safe - allowed during replay
done: false            # Set to true after reviewing
```

Kurral automatically analyzes tool names, descriptions, and docstrings for keywords like "update", "send", "write" (case-insensitive) and suggests which tools should be blocked.

**First Replay Output**:

```
============================================================
REPLAY BLOCKED: Side Effect Configuration Required
============================================================
The side effect configuration file has been auto-generated or needs review.
Please manually review and configure the side effects before replay:

Config file: my_agent/side_effect/side_effects.yaml

Tool Analysis & Suggestions:
------------------------------------------------------------
  send_email: false  [SIDE EFFECT]
    → Contains side effect keywords in name/description/docstring
  tavily_search: true  [SAFE]
    → No side effect keywords found
------------------------------------------------------------

Instructions:
1. Review each tool above - tools marked as SIDE EFFECT should be set to 'false'
2. Tools marked as SAFE can remain 'true' (unless you know they have side effects)
3. Manually edit the YAML file to adjust any values if needed
4. Set 'done: true' when you have finished configuring

Once you have set 'done: true', run the replay again.
============================================================
```

**Important**: You must manually set `done: true` after reviewing the configuration to allow replay.

### 4. Replay an Artifact

```bash
# Replay using the kurral CLI
kurral replay <artifact_id>

# Example
kurral replay 4babbd1c-d250-4c7a-8e4b-25a1ac134f89

# Or using partial UUID
kurral replay 4babbd1c
```

Kurral will automatically:

- Detect changes and determine replay type (Level 1 or Level 2)
- Check side effect configuration (blocks dangerous operations)
- Print replay results to stdout
- Save replay artifact to `replay_runs/` directory
- Report any changes detected
- Display ARS score

## Centralized Storage (Kurral API)

By default, Kurral stores artifacts locally in the `artifacts/` directory. For teams that need centralized storage, analytics, and collaboration, you can set up **Kurral API**.

### What Kurral API Provides

- ☁️ **Cloudflare R2 / S3 Storage**: Store artifacts in your own bucket
- 🔐 **Authentication**: API keys with scopes and rate limiting
- 📊 **Analytics**: Time series data, aggregations, and statistics
- 🔍 **Advanced Filtering**: Query by tenant, environment, semantic bucket, model, and more
- 🏢 **Multi-Tenant**: Organize artifacts by team or project

### Quick Setup

```bash
cd kurral-api
cp .env.example .env
# Configure your R2/S3 credentials in .env
docker-compose up -d
```

### Connect Kurral to the API

```python
from kurral import configure

configure(
    storage_backend="api",
    api_url="http://localhost:8000/api/v1",
    api_key="kurral_YOUR_API_KEY"
)
```

For full API documentation, see [kurral/storage/README-API.md](kurral/storage/README-API.md).

## Deep Dive

Want to understand how Kurral works under the hood? Read on.

### What's in a `.kurral` artifact?

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

#### Level 2 Replay (Non-Deterministic / Exploratory)

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

### Side Effect Management

Kurral protects against dangerous operations during replay through a YAML-based configuration system:

**Auto-Generation**: On first replay, Kurral automatically:

- Discovers all tools used in your agent
- Analyzes tool names, descriptions, and docstrings
- Suggests side effect status based on keywords ("update", "send", "write")
- Creates `side_effect/side_effects.yaml` in your agent directory

**Configuration Format**:

```yaml
tools:
  send_email: false    # false = side effect (blocked), true = safe (allowed)
  tavily_search: true
  write_file: false
done: false            # Must be set to true manually after review
```

**How It Works**:

- **Cached Results Available**: Side effect tools use cached outputs from the original artifact (no execution)
- **No Cache Available**: Side effect tools return a safe default message (blocked, never executed)
- **Safe Tools**: Normal tools execute if no cache match is found

**Safety First**: The `done` flag defaults to `false`, requiring manual review before any replay can proceed. This ensures you explicitly approve which tools can execute during replay.

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
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from kurral import trace_agent, trace_agent_invoke

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

- **`trace_agent`**: Decorator that wraps your agent's main function
- **`trace_agent_invoke`**: Wrapper for `agent_executor.invoke()` that captures traces
- **`replay`**: Replay engine with automatic Level 1/Level 2 detection
- **`replay_detector`**: Change detection logic and determinism scoring
- **`tool_stubber`**: Semantic tool matching and caching during replay
- **`side_effect_config`**: Side effect configuration management and auto-generation
- **`ars_scorer`**: Agent Regression Score calculation
- **`artifact_manager`**: Artifact storage and retrieval

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

### Current Limitations (we're working on them!)

- Only ReAct-style and LCEL agents fully supported (no native LangGraph streaming yet)
- Vision / image inputs not captured
- No built-in dashboard (yet – artifacts are JSON, just open one in VS Code/any editor)

## Best Practices

1. **Always pass `llm` parameter**: `trace_agent_invoke(agent_executor, input_data, llm=llm)` ensures accurate LLM config extraction
2. **Use session artifacts**: Let Kurral accumulate interactions automatically within `main()`
3. **Check ARS scores**: Monitor ARS to detect regressions when testing different models
4. **Review replay artifacts**: Check `replay_runs/` directory for detailed replay analysis
5. **Handle optional dependencies**: Kurral gracefully handles missing optional LLM packages
6. **Review side effect configuration**: Always review `side_effect/side_effects.yaml` before enabling replay (`done: true`)
7. **Mark dangerous tools as side effects**: Any tool that sends emails, makes payments, writes files, or modifies external state should be set to `false`

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

Join our Discord → [https://discord.gg/pan6GRRV](https://discord.gg/pan6GRRV)

## Support

- **Issues**: [github.com/kurral/kurralv3/issues](https://github.com/kurral/kurralv3/issues)
- **Email**: team@kurral.com

---

⭐ Star this repo if Kurral just saved you $50 in OpenAI credits.

Made with ❤️ for the agent-building community.
