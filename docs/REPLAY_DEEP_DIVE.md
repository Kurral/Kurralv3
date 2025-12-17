# Deep Dive: How Replay Works

Kurral's intelligent replay system captures complete agent execution traces and enables deterministic or exploratory replay — perfect for regression testing, model upgrades, prompt engineering, and massive cost reduction.

---

## Table of Contents

- [What's in a .kurral Artifact?](#whats-in-a-kurral-artifact)
- [Determinism Score](#determinism-score)
- [Decision Flow](#decision-flow)
- [Replay Types Explained](#replay-types-explained)
- [Semantic Tool Matching](#semantic-tool-matching)
- [Agent Regression Score (ARS)](#agent-regression-score-ars)
- [Side Effect Management](#side-effect-management)
- [Storage Options](#storage-options)
- [Best Practices](#best-practices)

---

## What's in a .kurral Artifact?

Human-readable JSON with complete execution trace:

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
    "temperature": 0,
    "seed": 42
  },
  "tool_calls": [...],
  "resolved_prompt": {...},
  "graph_version": {...}
}
```

**What's Captured:**

- ✅ All user inputs and agent outputs
- ✅ Complete tool execution traces (name, inputs, outputs, timestamps)
- ✅ LLM configuration (model, provider, temperature, seed)
- ✅ Resolved prompt templates
- ✅ Graph structure hash (detects tool/agent changes)
- ✅ Metadata (duration, errors, token usage)

---

## Determinism Score

Measures **configuration similarity** between the artifact and current run.

### Calculation

```
determinism_score = (temp_score + seed_score + model_score + provider_score) / 4
```

### Scoring Factors (each 0.0-1.0)

| Factor | Weight | Scoring Logic |
|--------|--------|---------------|
| **Temperature** | 25% | 1.0 if identical, 0.5 if one missing, else `1.0 - abs(difference)` |
| **Seed** | 25% | 1.0 if identical, 0.5 if both/one missing, 0.0 if different |
| **Model Name** | 25% | 1.0 if identical, 0.0 if different |
| **Provider** | 25% | 1.0 if identical, 0.0 if different |

### Example

```python
# Artifact config
{
  "model_name": "gpt-4",
  "provider": "openai",
  "temperature": 0.0,
  "seed": 42
}

# Current config
{
  "model_name": "gpt-4",
  "provider": "openai",
  "temperature": 0.5,
  "seed": 42
}

# Calculation
temp_score = 1.0 - abs(0.0 - 0.5) = 0.50  # Different temperature
seed_score = 1.0                           # Same seed
model_score = 1.0                          # Same model
provider_score = 1.0                       # Same provider

determinism_score = (0.50 + 1.0 + 1.0 + 1.0) / 4 = 0.875
```

**Result:** Score = 0.875 (≥ 0.8) → **A Replay** (if no critical changes)

### Threshold

**Default:** 0.8

- **Score ≥ 0.8** → Config similar enough → A replay (if no critical changes)
- **Score < 0.8** → Config too different → B replay (must re-execute)

**⚠️ Note:** Critical changes (model name, provider, tools) **always** trigger B replay, regardless of score.

---

## Decision Flow

```
┌─────────────────────────────────┐
│ Calculate Determinism Score     │
│ (0.0 - 1.0)                     │
└────────────┬────────────────────┘
             │
             ▼
   ┌──────────────────────┐
   │ Check for Critical   │
   │ Changes:             │
   │ • Model changed?     │
   │ • Provider changed?  │
   │ • Tools changed?     │
   └──────┬───────────────┘
          │
     ┌────┴────┐
     │         │
     ▼         ▼
   YES        NO
     │         │
     │         ▼
     │   ┌─────────────┐
     │   │ Score < 0.8?│
     │   └──┬──────┬───┘
     │      │ YES  │ NO
     │      │      │
     ▼      ▼      ▼
  ┌───────────┐ ┌───────────┐
  │ B REPLAY  │ │ A REPLAY  │
  │ (Re-exec) │ │ (Cached)  │
  └───────────┘ └───────────┘
```

**Key:** High score (≥ 0.8) + no critical changes → **A Replay** | Low score (< 0.8) OR critical changes → **B Replay**

---

## Replay Types Explained

### A Replay (Deterministic)

**When**: Determinism score ≥ 0.8 AND no critical changes detected

**What happens:**
- Returns artifact outputs directly
- No LLM or tool re-execution
- Perfect behavioral match

**Use cases:**
- ✅ Regression testing (verify no breaking changes)
- ✅ CI/CD pipelines (fast, zero-cost validation)
- ✅ Logic verification without LLM calls

**Cost:** Zero API costs

**Example triggers:**
- Same model, provider, and similar temperature/seed
- No tool or graph structure changes
- No prompt template changes

**Example output:**
```
Replay Type: A
Determinism Score: 1.00 (threshold: 0.80)

No changes detected.
Executing A Replay (Using cached outputs)...

[Kurral] Replay Execution:
  - Cache Hits: 3
  - New Tool Calls: 0
  - Unused Tool Calls: 0

ARS (Agent Regression Score): 1.000
  - Output Similarity: 1.000
  - Tool Accuracy: 1.000
```

---

### B Replay (Non-Deterministic / Exploratory)

**When**: Determinism score < 0.8 OR critical changes detected

**What happens:**
- Re-executes LLM with new config
- Uses semantic tool matching (85% threshold)
- Caches matched tool calls to reduce costs

**Use cases:**
- ✅ Model upgrades (test GPT-4.5 vs GPT-4)
- ✅ Prompt engineering (compare variations)
- ✅ A/B testing with quantifiable metrics

**Cost:** Reduced API costs via semantic tool caching

**Example triggers:**
- Different model (gpt-4 → gpt-3.5)
- Different provider (openai → anthropic)
- Different temperature/seed values
- Tool schema changes
- Prompt template changes

**Example output:**
```
Replay Type: B
Determinism Score: 0.62 (threshold: 0.80)

Changes Detected:
  - llm_config:
      model_name: {'artifact': 'gpt-4', 'current': 'gpt-4o'}

Executing B Replay (Re-executing agent with cached tool calls)...

[Kurral] Replay Execution:
  - Cache Hits: 2
  - New Tool Calls: 1
  - Unused Tool Calls: 0

ARS (Agent Regression Score): 0.845
  - Output Similarity: 0.95
  - Tool Accuracy: 0.60
```

---

## Semantic Tool Matching

During B replay, Kurral intelligently caches tool calls to reduce API costs:

### Matching Strategy

- **Exact Match**: Tool name and inputs match exactly → use cached output (no execution)
- **Semantic Match**: Similarity ≥ 85% → use cached output (no execution)
- **New Call**: Similarity < 85% → execute tool and cache result

### Example

**Cached call from artifact:**
```json
{
  "tool": "search_web",
  "arguments": {
    "location": "San Francisco, CA",
    "units": "metric"
  }
}
```

**Replay request:**
```json
{
  "tool": "search_web",
  "arguments": {
    "location": "San Francisco",
    "units": "metric"
  }
}
```

**Similarity:** 87% → **CACHE HIT** (no tool execution)

### Benefits

- ✅ Reduced API costs (fewer tool executions)
- ✅ Faster replay execution
- ✅ Accurate cache hit/miss tracking

### Configuration

Default threshold: **85%**

Can be adjusted in replay configuration (not yet exposed in API).

---

## Agent Regression Score (ARS)

Quantifies replay fidelity for A/B comparison.

### Formula

```
ARS = (Output Similarity × 0.7) + (Tool Accuracy × 0.3)
```

### Components

#### 1. Output Similarity (70% weight)

- Semantic text comparison between original and replayed outputs
- **1.0** = exact match
- **0.0** = complete divergence

Uses sentence transformers for semantic similarity.

#### 2. Tool Accuracy (30% weight)

**Formula:**
```
base_score = (used_original_tools / total_original_tools)
new_penalty = min(0.5, new_tools_count × 0.1)      # -10% per new tool, max -50%
unused_penalty = min(0.5, unused_tools_count × 0.1) # -10% per unused tool, max -50%
tool_accuracy = max(0.0, base_score - new_penalty - unused_penalty)
```

**Penalties:**
- **New tools**: -10% per tool (capped at -50%)
- **Unused tools**: -10% per tool (capped at -50%)

**Score range:** 0.0 (many changes) to 1.0 (perfect match)

---

### ARS Calculation Flow

```
┌──────────────────────────────────────┐
│ Output Similarity (0.0 - 1.0)        │
│ • Semantic text comparison           │
│ • 1.0 = exact match                  │
└────────────┬─────────────────────────┘
             │ × 0.7 (70% weight)
             ▼
     ┌───────────────┐
     │  Weighted     │
     │  Output       │───┐
     │  Score        │   │
     └───────────────┘   │
                         ▼
┌──────────────────────────────────────┐     ┌─────────┐
│ Tool Accuracy (0.0 - 1.0)            │     │   ARS   │
│ • Base: used_tools / total_tools     │────▶│  Score  │
│ • Penalties: new & unused tools      │     │ (0-1.0) │
└────────────┬─────────────────────────┘     └─────────┘
             │ × 0.3 (30% weight)
             ▼
     ┌───────────────┐
     │  Weighted     │
     │  Tool         │───┘
     │  Score        │
     └───────────────┘
```

---

### Example Calculation

**Scenario:**
- Output similarity: **0.95** (very similar text)
- Original tools: 5
- Used original tools: 4
- New tools added: 1
- Unused original tools: 1

**Tool Accuracy:**
```
base_score = 4 / 5 = 0.80
new_penalty = min(0.5, 1 × 0.1) = 0.10
unused_penalty = min(0.5, 1 × 0.1) = 0.10
tool_accuracy = max(0.0, 0.80 - 0.10 - 0.10) = 0.60
```

**ARS:**
```
ARS = (0.95 × 0.7) + (0.60 × 0.3)
    = 0.665 + 0.18
    = 0.845
```

---

### Interpretation

| ARS Range | Interpretation | Action |
|-----------|----------------|--------|
| **0.9 - 1.0** | Excellent fidelity | Minimal differences, likely safe |
| **0.7 - 0.9** | Good fidelity | Acceptable variations, review changes |
| **0.5 - 0.7** | Moderate fidelity | Investigate differences, potential issues |
| **< 0.5** | Poor fidelity | Likely regression, review carefully |

---

## Side Effect Management

Kurral protects against dangerous operations during replay through a YAML-based configuration system.

### Auto-Generation

On first replay, Kurral automatically:

1. **Discovers** all tools used in your agent
2. **Analyzes** tool names, descriptions, and docstrings
3. **Suggests** side effect status based on keywords:
   - Side effect keywords: "update", "send", "write", "delete", "email", "payment", "purchase", "post", "create"
   - Safe keywords: "read", "get", "search", "find", "list", "fetch"
4. **Creates** `side_effect/side_effects.yaml` in your agent directory

### Configuration Format

```yaml
tools:
  send_email: false    # false = side effect (blocked), true = safe (allowed)
  tavily_search: true  # true = safe (allowed during replay)
  write_file: false
  process_payment: false
done: false            # Must be set to true manually after review
```

### How It Works

**Cached Results Available:**
- Side effect tools use cached outputs from the artifact
- No execution occurs
- Returns original output

**No Cache Available:**
- Side effect tools return a safe default message
- Tool is blocked, never executed
- Message: `"[Kurral] Tool 'send_email' blocked (side effect, no cache available)"`

**Safe Tools:**
- Execute normally if no cache match found
- Allows for flexible replay with new tool calls

### Safety First

The `done` flag defaults to `false`, requiring **manual review** before any replay can proceed.

**First replay output:**
```
============================================================
REPLAY BLOCKED: Side Effect Configuration Required
============================================================
The side effect configuration file has been auto-generated.
Please manually review and configure the side effects before replay:

Config file: my_agent/side_effect/side_effects.yaml

Tool Analysis & Suggestions:
------------------------------------------------------------
  send_email: false  [SIDE EFFECT]
    → Contains side effect keywords in name/description
  tavily_search: true  [SAFE]
    → No side effect keywords found
  write_file: false  [SIDE EFFECT]
    → Contains side effect keywords in name/description
------------------------------------------------------------

Instructions:
1. Review each tool above
2. Manually edit the YAML file to adjust any values if needed
3. Set 'done: true' when you have finished configuring

Once you have set 'done: true', run the replay again.
============================================================
```

---

## Storage Options

Kurral supports two storage backends for artifact storage.

### Local Storage (Default)

Artifacts stored in your local filesystem:

```python
from kurral import configure

# Explicit configuration (optional - this is the default)
configure(storage_backend="local")
```

**Artifacts saved to:**
- `artifacts/` - Original execution artifacts
- `replay_runs/` - Replay artifacts

**Benefits:**
- ✅ Simple setup (no configuration needed)
- ✅ Fast access
- ✅ Works offline

**Limitations:**
- ❌ Limited to local disk space
- ❌ No team sharing
- ❌ Manual backup required

---

### Cloud Storage (R2 / S3)

For production environments or team collaboration:

```python
from kurral import configure

configure(
    storage_backend="r2",
    r2_account_id="your-account-id",
    r2_access_key_id="your-access-key",
    r2_secret_access_key="your-secret-key",
    r2_bucket_name="kurral-artifacts"
)
```

**Or via environment variables:**

```bash
# .env file
KURRAL_STORAGE_BACKEND=r2
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=kurral-artifacts
```

**Benefits:**
- ✅ **Scalable**: No local disk space limits
- ✅ **Team Access**: Share artifacts across team members
- ✅ **Cost-Effective**: Cloudflare R2 has zero egress fees
- ✅ **Secure**: Encrypted at rest
- ✅ **Backup**: Automatic redundancy

---

### Setup Cloudflare R2

1. Create an R2 bucket in Cloudflare Dashboard
2. Navigate to: **R2 → Manage R2 API Tokens**
3. Generate API credentials
4. Copy:
   - Account ID
   - Access Key ID
   - Secret Access Key
5. Configure Kurral with your credentials

---

### AWS S3 Compatible

Kurral works with any S3-compatible storage (AWS S3, MinIO, DigitalOcean Spaces, etc.):

```python
configure(
    storage_backend="r2",  # Use "r2" for any S3-compatible storage
    r2_endpoint_url="https://s3.amazonaws.com",  # For AWS S3
    r2_bucket_name="your-bucket",
    r2_access_key_id="...",
    r2_secret_access_key="..."
)
```

---

## Best Practices

### 1. Always Pass LLM Parameter

```python
# ✅ Correct
result = trace_agent_invoke(agent_executor, input_data, llm=llm)

# ❌ Incorrect (missing LLM config extraction)
result = trace_agent_invoke(agent_executor, input_data)
```

**Why:** Ensures accurate LLM config extraction for determinism scoring.

---

### 2. Use Session Artifacts

Let Kurral accumulate interactions automatically within `main()`:

```python
@trace_agent()
def main():
    # All interactions within this function
    # are saved to a single artifact
    while True:
        user_input = input("You: ")
        if user_input == "exit":
            break
        result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
        print(f"Agent: {result['output']}")
    # Artifact saved when main() exits
```

---

### 3. Monitor ARS Scores

Set thresholds for CI/CD:

```bash
# Example CI pipeline
python test_agent.py
kurral replay --latest

# Check ARS score
if [ $ARS_SCORE < 0.8 ]; then
  echo "Regression detected! ARS: $ARS_SCORE"
  exit 1
fi
```

---

### 4. Review Side Effect Configuration

Always review `side_effect/side_effects.yaml` before enabling replay:

```yaml
tools:
  # ✅ Review these carefully
  send_email: false         # Blocks emails during replay
  process_payment: false    # Blocks payments during replay
  write_database: false     # Blocks writes during replay

  # ✅ Safe for replay
  search_web: true
  read_file: true
  calculate: true

done: true  # Only set to true after reviewing ALL tools
```

---

### 5. Mark Dangerous Tools

Any tool that has side effects should be set to `false`:

**Side effects include:**
- Sending emails
- Making payments
- Writing files
- Modifying databases
- Posting to APIs
- Creating resources
- Deleting data

---

### 6. Use Cloud Storage for Teams

For team collaboration, use R2/S3:

```python
configure(
    storage_backend="r2",
    r2_bucket_name="team-kurral-artifacts"
)
```

**Benefits:**
- Team members can replay each other's sessions
- Centralized artifact storage
- Automatic backup

---

### 7. Capture Golden Paths

Record expected behavior as baselines for testing:

```bash
# Record golden path
python agent.py  # Run with trusted inputs
# Artifact: artifacts/golden-path.kurral

# Test changes against golden path
kurral replay artifacts/golden-path.kurral

# Expect high ARS (≥ 0.9)
```

---

### 8. Handle Optional Dependencies

Kurral gracefully handles missing optional LLM packages:

```python
# If google-generativeai not installed
# Kurral will still work with OpenAI, Anthropic, etc.

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-pro")
except ImportError:
    llm = ChatOpenAI(model="gpt-4")  # Fallback
```

---

## Advanced Topics

### Multiple Interactions

Kurral automatically accumulates all interactions within a session:

```python
@trace_agent()
def main():
    # First interaction
    result1 = trace_agent_invoke(agent_executor, {"input": "Hello"}, llm=llm)

    # Second interaction
    result2 = trace_agent_invoke(agent_executor, {"input": "What's the weather?"}, llm=llm)

    # Third interaction
    result3 = trace_agent_invoke(agent_executor, {"input": "Thanks!"}, llm=llm)

    # All 3 interactions saved in one artifact when main() exits
```

---

### Artifact Inspection

Artifacts are human-readable JSON:

```bash
# View artifact
cat artifacts/4babbd1c-d250-4c7a-8e4b-25a1ac134f89.kurral | jq

# Extract tool calls
cat artifacts/4babbd1c.kurral | jq '.tool_calls'

# Extract LLM config
cat artifacts/4babbd1c.kurral | jq '.llm_config'
```

---

### Custom Replay Logic

For advanced use cases, you can programmatically replay:

```python
from kurral.replay import replay

# Load artifact
artifact_path = "artifacts/4babbd1c.kurral"

# Replay with custom logic
replay(artifact_path, verbose=True)
```

---

## Troubleshooting

### Issue: Replay not finding artifact

**Solution:** Use full path or kurral_id:

```bash
# ✅ Full path
kurral replay artifacts/4babbd1c-d250-4c7a-8e4b-25a1ac134f89.kurral

# ✅ Kurral ID
kurral replay 4babbd1c-d250-4c7a-8e4b-25a1ac134f89

# ✅ Partial UUID
kurral replay 4babbd1c

# ✅ Latest
kurral replay --latest
```

---

### Issue: Side effect configuration not found

**Solution:** Run replay once to auto-generate config:

```bash
kurral replay <artifact>
# Kurral generates side_effect/side_effects.yaml
# Review and set done: true
kurral replay <artifact>  # Now works
```

---

### Issue: Low ARS score unexpectedly

**Possible causes:**
- Model change detected (triggers B replay)
- Tools changed (new/unused tools penalize score)
- Prompt template changed
- Temperature/seed changed

**Solution:** Check replay output for "Changes Detected" section.

---

## Additional Resources

- **[MCP Proxy Documentation](MCP_PROXY.md)** - Full HTTP/SSE proxy guide
- **[SSE Implementation](kurral/mcp/SSE_IMPLEMENTATION.md)** - Deep dive into SSE streaming
- **[Getting Started](GETTING_STARTED.md)** - 5-minute tutorial with examples
- **[Use Cases](USE_CASES.md)** - Real-world scenarios with ROI calculations
- **[Security Roadmap](MCP_SECURITY_VISION.md)** - MCP security testing vision

---

**Have questions?** Join our Discord: [https://discord.gg/pan6GRRV](https://discord.gg/pan6GRRV)
