
 <h1>
   <p align="center">
  Deterministic Replay & A/B Testing for Agents
</h1>
  </p>
<p align="center" style="margin-bottom: 0; line-height: 0;">
<img width="350" height="350" alt="4c469b1e-6cc4-479e-b18a-16a9cb214d8e" src="https://github.com/user-attachments/assets/248a09da-be82-4654-a5b1-0f09d45ebe4a" />
<h1 align="center" margin-top: -20px; margin-bottom: 70px;>
KURRAL 
</h1>


<p align="center">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" />
  <img src="https://img.shields.io/badge/Observability-black" />
  <img src="https://img.shields.io/badge/Security_Monitoring-black" />
  <img src="https://img.shields.io/badge/Replay_Agent_Actions-purple" />
</p>


# Overview
**Deterministic LLM Agent Testing & Replay Framework**

Kurral enables you to capture, replay, and A/B test LLM agent behaviors with deterministic precision. Built for teams that need reliable testing, version comparison, and evidence-based deployment decisions.

## Features

- 🎬 **Capture & Replay**: Record LLM traces with full tool/MCP calls and replay them deterministically with stubbed responses
- 🔬 **A/B Testing**: Compare agent versions before deployment (model migration, prompt changes, config tweaks)
- 📊 **ARS (Agent Regression Score)**: Quantify behavioral differences between versions
- ✅ **Validation & Diff**: Hash + structural comparison with detailed diff output
- 🪣 **Semantic Buckets**: Organize traces by business logic (e.g., `refund_flow`, `support_chat`)
- 🔐 **Authentication**: One-command registration with automatic API key generation
- 🔌 **LangSmith Integration**: Seamless import from LangSmith traces
- 🔧 **MCP Support**: Full Model Context Protocol tool capture and stubbing
- 💾 **Flexible Storage**: Local, Memory, API (Kurral Cloud), or your own R2/S3 bucket
- 🎨 **Beautiful CLI**: Rich terminal UI with progress bars, diffs, and tables

## Quick Start

### Installation

```bash
pip install kurral
```

### Register & Configure (One Command!)

```bash
# Register with Kurral Cloud and get API key automatically
kurral auth register

# Or use your own API backend
kurral auth register --api-url http://your-api:8000
```

Behind the scenes, this:
1. Creates your account
2. Logs you in (gets JWT)
3. Generates API key
4. Saves config to `~/.kurral/config.json`

You're ready to go! 🚀

### Capture Agent Traces

```python
from kurral import trace_llm
from openai import OpenAI

client = OpenAI()

@trace_llm(semantic_bucket="customer_support", tenant_id="acme")
def handle_customer_query(query: str) -> str:
    """Handle customer support query with LLM"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        seed=12345,  # Recommended for reproducibility
    )
    return response.choices[0].message.content

# Automatically traced and uploaded to Kurral Cloud
result = handle_customer_query("I need a refund for order #12345")
```

### A/B Test Agent Changes

**Before deploying changes, test them against production baselines:**

```python
from kurral.core.ab_test import ComparativeABTest

engine = ComparativeABTest()

# Test: Can we migrate from GPT-4 to GPT-4-turbo?
result = await engine.test_model_migration(
    baseline_artifacts=production_traces,
    from_model="gpt-4",
    to_model="gpt-4-turbo",
    threshold=0.90
)

# Decision
if result.recommendation == "deploy":
    print(f"✅ Safe to migrate (ARS: {result.b_mean_ars:.2f})")
else:
    print(f"❌ Migration causes {len(result.failures)} regressions")
```

**CLI A/B Testing:**

```bash
# Test model migration
kurral ab model-migration \
  --baseline ./production-traces/ \
  --model-a gpt-4 \
  --model-b gpt-4-turbo \
  --threshold 0.90

# Test prompt changes
kurral ab prompt-test \
  --baseline ./traces/ \
  --prompt-a current_prompt.txt \
  --prompt-b new_prompt.txt

# Compare custom configurations
kurral ab compare \
  --baseline ./traces/ \
  --config-a version_a.json \
  --config-b version_b.json
```

### Replay Traces

```bash
# Basic replay - stubs all tool/MCP calls
kurral replay trace.kurral

# Show diff between original and replayed outputs
kurral replay trace.kurral --diff

# Debug mode - shows LLM sampler state, stub status
kurral replay trace.kurral --debug --verbose
```

**What Replay Does:**
- Loads the `.kurral` artifact with all recorded data
- Primes cache with every tool/MCP call (inputs, outputs, hashes)
- Stubs external calls—nothing hits live APIs
- Reconstructs the output stream
- Validates outputs via hash + structural comparison
- Returns validation results and metadata

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your LLM Agent                       │
│               (with @trace_llm decorator)               │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   Kurral Deep Capture   │
         │  • LLM interactions     │
         │  • Tool calls (I/O)     │
         │  • Timing & metadata    │
         │  • Execution graphs     │
         │  • Stream capture       │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │  .kurral Artifact       │
         │  • Complete trace       │
         │  • Graph fingerprint    │
         │  • Replay metadata      │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │    Storage Backend      │
         │  • Kurral Cloud (API)   │
         │  • Your R2/S3 bucket    │
         │  • Local filesystem     │
         │  • In-memory            │
         └─────────────────────────┘
```

**Key Capabilities:**

1. **Direct Capture**: Captures from agent code (not via proxy), ensuring complete data
2. **Replay-First**: Every artifact contains everything needed for deterministic replay
3. **A/B Testing**: Evidence-based deployment decisions via version comparison
4. **Graph Hashing**: Detects when agent structure/behavior changes
5. **Cost Attribution**: Track spend by semantic bucket, model, and tenant

## CLI Commands

### Authentication

```bash
# Register new account (auto-generates API key)
kurral auth register

# Login to existing account
kurral auth login

# Check authentication status
kurral auth status
```

### Configuration

```bash
# Interactive configuration setup
kurral config init

# Show current configuration
kurral config show

# Show config file locations
kurral config path

# Reset configuration
kurral config reset --global
```

### A/B Testing

```bash
# Test model migration
kurral ab model-migration \
  --baseline ./traces/ \
  --model-a gpt-4 \
  --model-b gpt-4-turbo

# Test prompt changes
kurral ab prompt-test \
  --baseline ./traces/ \
  --prompt-a prompt1.txt \
  --prompt-b prompt2.txt

# Compare configurations
kurral ab compare \
  --baseline ./traces/ \
  --config-a v1.json \
  --config-b v2.json
```

### Replay

```bash
# Basic replay
kurral replay artifact.kurral

# With diff
kurral replay artifact.kurral --diff

# Debug mode
kurral replay artifact.kurral --debug
```

### Export

```bash
# Export from LangSmith
kurral export --run-id ls_abc123 --output trace.kurral

# Export from local file
kurral export --input trace.json --output trace.kurral
```

### Artifact Management

```bash
# List semantic buckets
kurral buckets list

# Show artifacts in bucket
kurral buckets show --semantic refund_flow

# Memory storage (when using memory backend)
kurral memory stats
kurral memory list
kurral memory get <artifact_id>
```

## Storage Backends

Kurral supports multiple storage backends:

### 1. Kurral Cloud (API) - Recommended

```bash
# Register and configure automatically
kurral auth register

# Or configure manually
export KURRAL_STORAGE_BACKEND=api
export KURRAL_API_KEY=kurral_your_key_here
export KURRAL_API_URL=https://api.kurral.io
```

### 2. Your Own R2/S3 Bucket

```bash
# Cloudflare R2
export KURRAL_CUSTOM_BUCKET_ENABLED=true
export KURRAL_CUSTOM_BUCKET_NAME=my-bucket
export KURRAL_CUSTOM_BUCKET_ACCOUNT_ID=abc123
export KURRAL_CUSTOM_BUCKET_REGION=auto
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=key
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=secret

# AWS S3
export KURRAL_CUSTOM_BUCKET_ENABLED=true
export KURRAL_CUSTOM_BUCKET_NAME=my-s3-bucket
export KURRAL_CUSTOM_BUCKET_REGION=us-west-2
export KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=AKIA...
export KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=wJal...
```

### 3. Local Storage

```bash
export KURRAL_STORAGE_BACKEND=local
export KURRAL_LOCAL_STORAGE_PATH=./artifacts
```

### 4. In-Memory (for testing)

```bash
export KURRAL_STORAGE_BACKEND=memory
export KURRAL_MEMORY_MAX_ARTIFACTS=1000
export KURRAL_MEMORY_MAX_SIZE_MB=500
```

## A/B Testing Use Cases

### Model Migration

```python
# Test: Can we switch from GPT-4 to GPT-4-turbo?
result = await engine.test_model_migration(
    baseline_artifacts=prod_traces,
    from_model="gpt-4",
    to_model="gpt-4-turbo",
    threshold=0.90
)

if result.b_mean_ars >= 0.90 and result.failures == 0:
    print("✅ Safe to migrate")
```

### Prompt Optimization

```python
current_prompt = "You are a helpful assistant."
optimized_prompt = """
You are a friendly customer support expert.

Guidelines:
- Be empathetic and understanding
- Provide clear, step-by-step solutions
- Offer to escalate if needed
"""

result = await engine.test_prompt_change(
    baseline_artifacts=traces,
    current_prompt=current_prompt,
    new_prompt=optimized_prompt,
    threshold=0.90
)
```

### Temperature Tuning

```python
# Find optimal temperature
for temp in [0.0, 0.3, 0.7, 1.0]:
    result = await engine.test_temperature_tuning(
        baseline_artifacts=traces,
        current_temp=0.0,
        new_temp=temp,
        threshold=0.85
    )
    print(f"temp={temp}: ARS={result.b_mean_ars:.3f}")
```

### Complex Configuration Changes

```python
# Production config
version_a = VersionConfig(
    name="prod-v1.0",
    model_name="gpt-4",
    temperature=0.0,
    max_tokens=500,
)

# Candidate config
version_b = VersionConfig(
    name="candidate-v1.1",
    model_name="gpt-4-turbo",
    temperature=0.2,
    max_tokens=1000,
)

result = await engine.run_ab_test(
    test_suite=traces,
    version_a=version_a,
    version_b=version_b,
    threshold=0.90
)
```

## .kurral Artifact Format

A `.kurral` file is a JSON artifact containing everything needed for replay and analysis:

```json
{
  "kurral_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "local_abc123",
  "tenant_id": "acme_prod",
  "semantic_buckets": ["refund_flow"],
  "environment": "production",
  "deterministic": true,
  "replay_level": "A",
  "timestamp": "2024-01-15T10:30:00Z",
  
  "llm_config": {
    "model_name": "gpt-4-0613",
    "provider": "openai",
    "parameters": {
      "temperature": 0.0,
      "top_p": 1.0,
      "seed": 12345,
      "max_tokens": 500
    }
  },
  
  "resolved_prompt": {
    "template": "You are a helpful assistant...",
    "variables": {"tone": "professional"},
    "final_text": "You are a helpful assistant. Be professional..."
  },
  
  "graph_version": {
    "graph_hash": "d35d48cb...",
    "graph_checksum": "2f2011f2..."
  },
  
  "tool_calls": [
    {
      "id": "tc_abc123",
      "tool_name": "check_order_status",
      "type": "http",
      "start_time": "2024-01-15T10:30:00.123Z",
      "end_time": "2024-01-15T10:30:00.265Z",
      "latency_ms": 142,
      "input": {"order_id": "12345"},
      "output": {"status": "shipped"},
      "status": "ok",
      "cache_key": "sha256:abc123...",
      "output_hash": "sha256:def456..."
    }
  ],
  
  "outputs": {
    "items": ["Refund", " initiated", "..."],
    "full_text": "Refund initiated...",
    "stream_map": [...]
  }
}
```

**Key Fields:**
- `graph_version`: Execution graph fingerprint (detects code changes)
- `tool_calls[]`: Complete tool execution history with I/O
- `llm_config.parameters`: Full sampler state for reproducibility
- `replay_level`: Determinism classification (A/B/C) - metadata only
- `outputs.stream_map`: Stream reconstruction data with timing

## Determinism Levels (Metadata)

Kurral classifies traces by expected reproducibility:

- **Level A** (score ≥ 0.90): High reproducibility (frozen model, seed set, complete capture)
- **Level B** (0.50 ≤ score < 0.90): Medium reproducibility (partial determinism)
- **Level C** (score < 0.50): Low reproducibility (high temperature, no seed)

**⚠️ Important**: These levels are **metadata only** for analytics. All artifacts are replayed the same way (tool calls stubbed, outputs cached) regardless of level. For version comparison, use **A/B testing** instead.

## Integration Examples

### Basic Usage

```python
from kurral import trace_llm
from openai import OpenAI

client = OpenAI()

@trace_llm(semantic_bucket="support", tenant_id="acme")
def my_agent(query: str):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        seed=42  # For reproducibility
    )
    return response.choices[0].message.content
```

### With LangGraph

```python
from kurral import trace_llm
from langgraph.graph import StateGraph

@trace_llm(semantic_bucket="workflows", tenant_id="acme")
def run_workflow(input_data):
    graph = build_langgraph()  # Your LangGraph
    result = graph.invoke(input_data)
    return result
```

### With MCP Tools

```python
from kurral.core.decorator import trace_llm

@trace_llm(
    semantic_bucket="data_ops",
    tenant_id="acme",
    mcp_servers=["filesystem", "database"]
)
def process_data(request):
    # MCP tools are automatically captured and stubbed during replay
    return agent.run(request)
```

## Environment Variables

```bash
# Storage Backend
KURRAL_STORAGE_BACKEND=api  # api, local, memory, r2

# Kurral Cloud API
KURRAL_API_KEY=kurral_your_key_here
KURRAL_API_URL=https://api.kurral.io
KURRAL_TENANT_ID=your_tenant

# Custom Bucket (R2/S3)
KURRAL_CUSTOM_BUCKET_ENABLED=true
KURRAL_CUSTOM_BUCKET_NAME=my-bucket
KURRAL_CUSTOM_BUCKET_REGION=auto
KURRAL_CUSTOM_BUCKET_ACCESS_KEY_ID=key
KURRAL_CUSTOM_BUCKET_SECRET_ACCESS_KEY=secret

# Local Storage
KURRAL_LOCAL_STORAGE_PATH=./artifacts

# Memory Storage
KURRAL_MEMORY_MAX_ARTIFACTS=1000
KURRAL_MEMORY_MAX_SIZE_MB=500

# LangSmith Integration (Optional)
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=default

# Application
KURRAL_ENVIRONMENT=production
KURRAL_DEBUG=false
```

## Best Practices

### 1. Use Semantic Buckets

Organize traces by business logic:

```python
@trace_llm(semantic_bucket="payment_flow", tenant_id="acme")
def process_payment(order): ...

@trace_llm(semantic_bucket="customer_support", tenant_id="acme")
def handle_ticket(ticket): ...
```

### 2. Set Seeds for Reproducibility

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    seed=42,  # Makes outputs more reproducible
    temperature=0.0  # For maximum determinism
)
```

### 3. Build Good Baselines for A/B Testing

- Collect 50-100 production traces minimum
- Include diverse scenarios (success, errors, edge cases)
- Use semantic buckets to organize by use case

### 4. Set Appropriate ARS Thresholds

- **0.95+**: Critical paths (payments, auth, deletions)
- **0.90**: Standard production code
- **0.85**: Experimental features
- **0.80**: Research/exploration

### 5. Test Changes Before Deployment

```bash
# Always A/B test before deploying
kurral ab model-migration \
  --baseline ./prod-traces/ \
  --model-a gpt-4 \
  --model-b gpt-4-turbo \
  --threshold 0.90
```

## Troubleshooting

### Installation Issues

```bash
# Ensure Python 3.11+
python --version

# Upgrade pip
pip install --upgrade pip

# Install kurral
pip install kurral
```

### Authentication Issues

```bash
# Check current status
kurral auth status

# Re-register if needed
kurral auth register --api-url http://your-api:8000
```

### Storage Issues

```bash
# Verify configuration
kurral config show

# Reinitialize if needed
kurral config init
```

### Import Issues

```bash
# If using optional features, install dependencies
pip install boto3  # For R2/S3 storage
pip install langsmith  # For LangSmith integration
```

## Development

```bash
# Clone repository
git clone https://github.com/kurral-dev/kurral-cli.git
cd kurral-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black kurral/
ruff check kurral/

# Run CLI
kurral --help
```

## License

Apache-2.0 License - see LICENSE file

## Links

- **PyPI**: https://pypi.org/project/kurral/
- **GitHub**: https://github.com/kurral-dev/kurral-cli
- **Documentation**: [PUBLISHING.md](./PUBLISHING.md)
- **Changelog**: [CHANGELOG.md](./CHANGELOG.md)

## Support

- Open an issue on GitHub
- Check documentation in repo
- Email: team@kurral.dev

---

**Ready to start?** Run `pip install kurral && kurral auth register` 🚀
