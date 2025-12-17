# Kurral Use Cases - Real-World Scenarios

This document shows how developers are using Kurral TODAY to solve real problems.

---

## Table of Contents

1. [Regression Testing for Customer Support Bot](#1-regression-testing-for-customer-support-bot)
2. [Cost Optimization: GPT-4 → GPT-3.5](#2-cost-optimization-downgrading-models)
3. [Debugging Production Failures](#3-debugging-production-failures)
4. [Prompt Engineering A/B Testing](#4-prompt-engineering-ab-testing)
5. [CI/CD Integration](#5-cicd-integration)
6. [Team Collaboration & Knowledge Sharing](#6-team-collaboration--knowledge-sharing)

---

## 1. Regression Testing for Customer Support Bot

**Scenario:** You have a customer support chatbot that answers product questions. You're refactoring the code but need to ensure behavior doesn't change.

### The Problem

```python
# Original agent code
def support_agent():
    tools = [search_kb, check_order_status, create_ticket]
    # ... lots of complex logic
```

**Question:** How do you know your refactoring didn't break anything?

Traditional approach:
- ❌ Manual testing (tedious, incomplete)
- ❌ Unit tests (don't test real LLM behavior)
- ❌ Hope and pray

### The Kurral Solution

**Step 1: Capture Golden Dataset**

```bash
# Run your agent on 50 real customer questions
python support_agent.py < test_questions.txt
```

Kurral creates 50 `.kurral` artifacts - your "golden dataset" of correct behavior.

**Step 2: Refactor Code**

```python
# Refactored agent code
def support_agent():
    tools = [search_kb_v2, check_order_status, create_ticket]  # New KB search
    # ... cleaned up logic
```

**Step 3: Regression Test**

```bash
# Replay all 50 artifacts
for artifact in artifacts/*.kurral; do
  kurral replay $artifact --threshold 0.95
done
```

**Result:**

```
✅ 48/50 passed (ARS > 0.95)
⚠️ 2/50 failed (ARS < 0.95):
  - Artifact abc123: ARS = 0.82 (tool call mismatch)
  - Artifact def456: ARS = 0.88 (output wording changed)
```

**You immediately know:**
- 96% of cases work perfectly
- 2 edge cases need investigation
- Can fix BEFORE deploying

### Value Delivered

- ✅ **Confidence:** Know exactly what broke
- ✅ **Speed:** Test 50 cases in 30 seconds
- ✅ **Cost:** Zero API calls (Level 1 replay)
- ✅ **Coverage:** Real production scenarios

**ROI:** Prevented 1 production incident that would cost 10+ engineer hours to debug.

---

## 2. Cost Optimization: Downgrading Models

**Scenario:** Your agent uses GPT-4, costing $5,000/month. Can you use GPT-3.5 and save 90%?

### The Problem

- GPT-4: $0.03 per 1K tokens
- GPT-3.5: $0.003 per 1K tokens
- **10x price difference!**

**Question:** Will GPT-3.5 perform well enough on your specific use case?

### The Kurral Solution

**Step 1: Capture Production Workload**

```python
@trace_agent()
def research_agent():
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    # ... agent logic
```

Run on 100 real queries → 100 `.kurral` artifacts.

**Step 2: Test GPT-3.5**

```python
# Change model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
```

```bash
# Replay all 100 artifacts
kurral replay artifacts/* --model gpt-3.5-turbo
```

**Results:**

```
ARS Distribution:
  - 1.00 (perfect):  45 artifacts
  - 0.95-0.99:       38 artifacts
  - 0.90-0.94:       12 artifacts
  - <0.90:            5 artifacts

Average ARS: 0.94
```

**Decision Matrix:**

| ARS Range | Action |
|-----------|--------|
| > 0.95 | ✅ Use GPT-3.5 (safe) |
| 0.90-0.95 | ⚠️ Review manually (83% of cases) |
| < 0.90 | ❌ Keep GPT-4 (5% of cases) |

**Hybrid Approach:**
- Use GPT-3.5 for 95% of queries
- Route complex queries to GPT-4
- **Save $4,750/month (95%)**

### Value Delivered

- 💰 **Cost Savings:** $57,000/year
- 📊 **Data-Driven:** Not guessing, testing real workload
- ⚡ **Fast:** Test 100 queries in 5 minutes
- 🎯 **Precise:** Know exactly which 5% needs GPT-4

**ROI:** $57K saved vs. $0 cost to test.

---

## 3. Debugging Production Failures

**Scenario:** A customer reports your agent gave a wrong answer. How do you reproduce it?

### The Problem

**Customer ticket:**
> "The agent said my order was delivered, but it's not. This happened on Dec 15th at 3:42 PM."

Traditional debugging:
- ❌ Logs are scattered (LLM calls, tool results, app logs)
- ❌ Can't reproduce (LLM is non-deterministic)
- ❌ Expensive to re-run production scenario

### The Kurral Solution

**Production Setup:**

```python
@trace_agent()
def order_status_agent():
    # ... agent code
    # Kurral automatically captures all executions
```

Artifacts uploaded to S3 with customer ID metadata.

**Debugging Flow:**

**Step 1: Find the Artifact**

```bash
# Search by customer ID and timestamp
kurral search --customer-id C12345 --timestamp 2025-12-15T15:42
```

Returns: `artifacts/abc123-def456.kurral`

**Step 2: Download and Inspect**

```bash
kurral artifact abc123-def456 --format json
```

```json
{
  "inputs": {
    "interactions": [{
      "input": "Where is my order #ORD789?"
    }]
  },
  "tool_calls": [
    {
      "tool_name": "check_order_status",
      "input": {"order_id": "ORD789"},
      "output": {
        "status": "delivered",
        "tracking_number": "TRK123",
        "delivered_at": "2025-12-10T10:00:00Z"  ← Wrong data from API!
      }
    }
  ]
}
```

**Root Cause Found:** The `check_order_status` tool returned incorrect data from the shipping API.

**Step 3: Reproduce Locally**

```bash
# Replay exact scenario
kurral replay abc123-def456 --verbose
```

See the exact same behavior locally, no guessing.

**Step 4: Fix and Verify**

```python
# Fix: Add API response validation
def check_order_status(order_id):
    result = shipping_api.get_status(order_id)
    if not result.get("tracking_number"):
        raise ValueError("Invalid API response")
    return result
```

```bash
# Replay with fix
kurral replay abc123-def456
```

```
ARS: 1.00 (but now with proper error handling)
```

### Value Delivered

- 🔍 **Root Cause:** Found in 5 minutes vs. 2 hours
- 🎯 **Exact Reproduction:** No guessing
- ✅ **Verification:** Confirm fix works
- 📈 **Prevent Recurrence:** Add to regression test suite

**ROI:** Saved 2 hours of debugging + prevented future incidents.

---

## 4. Prompt Engineering A/B Testing

**Scenario:** You want to improve your prompt but need quantifiable results.

### The Problem

You have two prompt variations:

**Prompt A (Current):**
```
You are a helpful assistant. Answer the question concisely.
```

**Prompt B (New):**
```
You are an expert research assistant. Provide detailed, well-sourced answers with citations.
```

**Question:** Which is actually better for your use case?

### The Kurral Solution

**Step 1: Baseline with Prompt A**

```python
@trace_agent()
def agent():
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    prompt_template = "You are a helpful assistant..."  # Prompt A
```

Run on 50 test questions → 50 artifacts.

**Step 2: Test Prompt B**

```python
prompt_template = "You are an expert research assistant..."  # Prompt B
```

```bash
# Replay all 50 artifacts with new prompt
kurral replay artifacts/* --prompt-version B
```

**Results:**

| Metric | Prompt A | Prompt B | Winner |
|--------|----------|----------|--------|
| Avg ARS | 0.85 | 0.72 | ❌ A |
| Output Length | 50 words | 150 words | - |
| Tool Calls | 1.5 avg | 2.3 avg | - |
| API Cost | $0.05 | $0.12 | ❌ A |

**Insights:**
- Prompt B changes behavior significantly (ARS 0.72)
- Longer outputs, more tool calls
- 2.4x more expensive
- But is it BETTER for users?

**Step 3: Manual Quality Review**

Review the 10 cases with lowest ARS:

```bash
kurral diff abc123 --baseline A --test B --show-outputs
```

**Finding:** Prompt B adds unnecessary citations for simple questions but excels at complex research queries.

**Decision:** Use hybrid approach:
- Simple queries → Prompt A
- Complex queries → Prompt B

### Value Delivered

- 📊 **Quantified:** Not "feels better", actual numbers
- 💡 **Insights:** Discovered hybrid approach
- 💰 **Cost Awareness:** Knew exact price impact
- ⚡ **Fast:** Tested 50 cases in 10 minutes

**ROI:** Avoided deploying a 2.4x more expensive prompt system-wide.

---

## 5. CI/CD Integration

**Scenario:** Prevent regressions from reaching production.

### The Problem

Your team ships agent updates weekly. Sometimes changes break subtle behaviors.

### The Kurral Solution

**GitHub Actions Workflow:**

```yaml
name: Agent Regression Tests

on: [pull_request]

jobs:
  regression-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: pip install kurral

      - name: Run agent tests
        run: python agent.py

      - name: Replay golden artifacts
        run: |
          for artifact in tests/golden/*.kurral; do
            kurral replay $artifact --threshold 0.95 || exit 1
          done

      - name: Check ARS threshold
        run: |
          avg_ars=$(kurral stats replay_runs/ --metric avg_ars)
          if (( $(echo "$avg_ars < 0.95" | bc -l) )); then
            echo "❌ Average ARS ($avg_ars) below threshold (0.95)"
            exit 1
          fi
          echo "✅ Average ARS: $avg_ars"
```

**Result:** Pull requests are blocked if ARS drops below 95%.

### Value Delivered

- 🛡️ **Protection:** Catch regressions before merge
- 🤖 **Automated:** No manual testing needed
- 📈 **Trend Tracking:** See ARS over time
- 🚀 **Confidence:** Ship faster knowing tests pass

**ROI:** Prevented 3 production incidents in first month.

---

## 6. Team Collaboration & Knowledge Sharing

**Scenario:** Onboarding new engineers to your agent codebase.

### The Problem

New hire asks: "How does the agent handle complex queries?"

Traditional answer:
- Read code (3 hours)
- Run examples (1 hour)
- Ask questions (2 hours)

### The Kurral Solution

**Share Artifacts:**

```bash
# Senior engineer shares key scenarios
kurral export scenarios/complex_query.kurral \
  --format annotated \
  --comments "This shows how the agent chains 3 tools together"
```

**New engineer explores:**

```bash
# Download and replay
kurral import scenarios/complex_query.kurral
kurral replay complex_query --step-by-step
```

**Output:**

```
Step 1: User asks: "What were Tesla's earnings last quarter and how does it compare to Ford?"

Step 2: Agent calls search_tool("Tesla Q3 2024 earnings")
  → Result: "$25B revenue, $3.2B profit"

Step 3: Agent calls search_tool("Ford Q3 2024 earnings")
  → Result: "$41B revenue, $1.8B profit"

Step 4: Agent calls calculator("(3.2/25) vs (1.8/41)")
  → Result: "Tesla: 12.8% margin vs Ford: 4.4% margin"

Step 5: Agent responds: "Tesla had $25B in revenue with 12.8% profit margin, while Ford had $41B revenue with 4.4% margin. Tesla is more profitable per dollar of revenue."
```

**Learning time reduced:** 6 hours → 30 minutes

### Value Delivered

- 🎓 **Faster Onboarding:** See real executions
- 📚 **Living Documentation:** Artifacts are executable docs
- 🤝 **Knowledge Transfer:** Share expertise via artifacts
- 🐛 **Bug Reports:** Attach `.kurral` file to issues

**ROI:** 90% faster onboarding, better bug reports.

---

## Summary: When to Use Kurral

| Use Case | Value | Time to Value |
|----------|-------|---------------|
| Regression Testing | Prevent production bugs | 10 minutes |
| Cost Optimization | Save 90% on API costs | 30 minutes |
| Debugging | Find root cause faster | 5 minutes |
| Prompt Engineering | Quantify improvements | 15 minutes |
| CI/CD | Automate quality gates | 1 hour |
| Onboarding | Faster knowledge transfer | Immediate |

---

## Getting Started

1. **Pick ONE use case** from above
2. Follow the **[Getting Started Guide](GETTING_STARTED.md)**
3. See results in 5 minutes

**Join our community:**
- Discord: https://discord.gg/pan6GRRV
- Share your use case success story!

---

**The key insight:** Kurral turns agent executions into **testable, reproducible artifacts** that you can replay, compare, and optimize.

Stop guessing. Start testing.
