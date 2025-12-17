# Getting Started with Kurral - Practical Guide

**Time to value: 5 minutes** ⏱️

This guide gets you from zero to seeing Kurral's value with a working example.

---

## What You'll Learn

1. Run a simple AI agent instrumented with Kurral
2. See a complete `.kurral` artifact generated
3. Replay that artifact to test behavior
4. Understand ARS scoring with real numbers
5. View your traces in the beautiful dashboard

---

## Prerequisites

```bash
# Install Kurral
pip install kurral

# Install dependencies for the example
pip install langchain langchain-openai

# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

---

## Example 1: Simple Research Assistant (5 minutes)

### Step 1: Create the Agent

Create `research_agent.py`:

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from kurral import trace_agent, trace_agent_invoke

# Simple research tool (mock - no actual API calls)
def search_tool(query: str) -> str:
    """Search for information on a topic"""
    # Mock responses for demo purposes
    responses = {
        "python": "Python is a high-level programming language created by Guido van Rossum in 1991.",
        "ai": "AI (Artificial Intelligence) enables machines to perform tasks that typically require human intelligence.",
        "kurral": "Kurral is a testing and replay framework for AI agents that captures complete execution traces.",
    }
    for key in responses:
        if key in query.lower():
            return responses[key]
    return f"Information about '{query}' - this is a mock search result for demonstration."

def calculator_tool(expression: str) -> str:
    """Calculate mathematical expressions"""
    try:
        result = eval(expression)  # Don't do this in production!
        return f"The result is: {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"

# Create tools
tools = [
    Tool(
        name="search",
        func=search_tool,
        description="Useful for searching information about topics. Input should be a search query."
    ),
    Tool(
        name="calculator",
        func=calculator_tool,
        description="Useful for performing calculations. Input should be a mathematical expression like '2+2' or '10*5'."
    )
]

# Create prompt
template = """Answer the following question as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

@trace_agent()
def main():
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

    # Ask a question
    question = "What is Python and what is 25 * 4?"

    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}\n")

    result = trace_agent_invoke(agent_executor, {"input": question}, llm=llm)

    print(f"\n{'='*60}")
    print(f"Answer: {result['output']}")
    print(f"{'='*60}\n")

    return result

if __name__ == "__main__":
    main()
```

### Step 2: Run the Agent

```bash
python research_agent.py
```

**What you'll see:**

```
============================================================
Question: What is Python and what is 25 * 4?
============================================================

> Entering new AgentExecutor chain...
I need to search for information about Python and perform a calculation.

Action: search
Action Input: python
Observation: Python is a high-level programming language created by Guido van Rossum in 1991.

Action: calculator
Action Input: 25 * 4
Observation: The result is: 100

Thought: I now know the final answer
Final Answer: Python is a high-level programming language created by Guido van Rossum in 1991, and 25 * 4 equals 100.

> Finished chain.

============================================================
Answer: Python is a high-level programming language created by Guido van Rossum in 1991, and 25 * 4 equals 100.
============================================================

[Kurral] Session artifact saved: artifacts/abc123...kurral
[Kurral] Run ID: local_agent_1234567890
[Kurral] Kurral ID: abc123-def456-...
[Kurral] Total interactions: 1
```

**💡 What just happened?**
- Kurral captured EVERYTHING: your question, both tool calls, all results
- Saved to `artifacts/abc123...kurral`
- You can now replay this exact execution

### Step 3: Inspect the Artifact

```bash
# View the artifact (pretty-printed JSON)
cat artifacts/abc123...kurral | python -m json.tool | head -50
```

**You'll see:**

```json
{
  "kurral_id": "abc123-def456-...",
  "run_id": "local_agent_1234567890",
  "created_at": "2025-12-16T10:00:00Z",
  "duration_ms": 3420,

  "inputs": {
    "interactions": [
      {
        "input": "What is Python and what is 25 * 4?"
      }
    ]
  },

  "outputs": {
    "interactions": [
      {
        "input": "What is Python and what is 25 * 4?",
        "output": "Python is a high-level programming language created by Guido van Rossum in 1991, and 25 * 4 equals 100."
      }
    ]
  },

  "tool_calls": [
    {
      "tool_name": "search",
      "input": { "query": "python" },
      "output": { "result": "Python is a high-level programming language..." },
      "latency_ms": 120
    },
    {
      "tool_name": "calculator",
      "input": { "expression": "25 * 4" },
      "output": { "result": "The result is: 100" },
      "latency_ms": 15
    }
  ],

  "llm_config": {
    "model_name": "gpt-4",
    "provider": "openai",
    "temperature": 0.0
  }
}
```

**This is your execution "recording"** - everything the agent did, captured perfectly.

---

### Step 4: Configure Side Effects (First Time)

Before replaying, Kurral needs to know which tools are safe to re-run.

```bash
# Try to replay
kurral replay --latest
```

**You'll see:**

```
============================================================
REPLAY BLOCKED: Side Effect Configuration Required
============================================================

Config file: research_agent/side_effect/side_effects.yaml

Tool Analysis & Suggestions:
------------------------------------------------------------
  search: true  [SAFE]
    → No side effect keywords found
  calculator: true  [SAFE]
    → No side effect keywords found
------------------------------------------------------------

Instructions:
1. Review side_effects.yaml
2. Set 'done: true' when ready
3. Run replay again
```

**Edit `side_effect/side_effects.yaml`:**

```yaml
tools:
  search: true      # Safe - read-only
  calculator: true  # Safe - pure function
done: true          # ← Set this to true
```

---

### Step 5: Replay the Artifact

```bash
kurral replay --latest
```

**Output:**

```
Replay Type: A (Deterministic)
Determinism Score: 0.15 (threshold: 0.80)

No changes detected - using cached outputs

[Kurral] Replay Execution:
  - Cache Hits: 2
  - New Tool Calls: 0
  - Unused Tool Calls: 0

ARS (Agent Regression Score): 1.00
  - Output Similarity: 1.00  ✅ Perfect match
  - Tool Accuracy: 1.00      ✅ All tools matched

✅ Replay successful - behavior is identical!

[Kurral] Replay artifact saved: replay_runs/replay-abc123...kurral
```

**🎉 What does this mean?**

- **ARS = 1.00:** Your agent's behavior is 100% reproducible
- **0 API costs:** Used cached results, didn't call OpenAI
- **Perfect for regression testing:** If you change code and ARS drops, you broke something!

---

## Example 2: Testing Model Changes (ARS in Action)

Now let's see the REAL power - testing if GPT-3.5 can replace GPT-4.

### Modify the Agent

Edit `research_agent.py`, line with `ChatOpenAI`:

```python
# Change from:
llm = ChatOpenAI(model="gpt-4", temperature=0)

# To:
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
```

### Replay Again

```bash
kurral replay --latest
```

**Output:**

```
Replay Type: B (Non-Deterministic)
Determinism Score: 0.15 (threshold: 0.80)

Changes Detected:
  - llm_config:
      model_name: {'artifact': 'gpt-4', 'current': 'gpt-3.5-turbo'}

Executing B Replay (Re-executing with new model)...

[Kurral] Replay Execution:
  - Cache Hits: 2        ← Used cached tool results
  - New Tool Calls: 0
  - LLM Re-executed: Yes ← Called GPT-3.5

ARS (Agent Regression Score): 0.87
  - Output Similarity: 0.92  ⚠️  Slightly different wording
  - Tool Accuracy: 1.00      ✅ Same tools used

⚠️ Behavior changed slightly with new model
```

**💰 What you saved:**
- Original run: 2 tool calls + 1 LLM call = ~$0.03
- Replay: 0 tool calls + 1 LLM call = ~$0.01
- **Saved 66% on API costs!**

**📊 What you learned:**
- GPT-3.5 produced similar (but not identical) output
- ARS of 0.87 means 87% behavioral match
- You can now decide: "Is 87% good enough to downgrade?"

---

## Example 3: View in Dashboard

### Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open **http://localhost:5173/**

### Drag-and-Drop Your Artifact

1. Click "Traces" in navigation
2. Drag your `.kurral` file from `artifacts/` folder
3. See your execution visualized:
   - Timeline with tool calls
   - Input/output viewers
   - Execution metrics

**Screenshot opportunity:** Take a screenshot of the trace viewer to show stakeholders!

---

## What's Next?

Now that you've seen Kurral work, explore:

### For Testing
- Run your agent 10 times, compare ARS scores
- Set ARS threshold in CI/CD (fail if ARS < 0.9)
- Catch regressions before deployment

### For Cost Optimization
- Test if GPT-3.5 can replace GPT-4 (save 90% on costs)
- Benchmark different models on same tasks
- Replay production issues locally (zero API cost)

### For Debugging
- Reproduce production failures exactly
- Share `.kurral` files with team members
- Step through execution in dashboard

---

## Real-World Use Cases

See **[USE_CASES.md](USE_CASES.md)** for practical scenarios:
- Customer support chatbot regression testing
- Research agent cost optimization
- Production debugging workflow

---

## Need Help?

- **Discord**: https://discord.gg/pan6GRRV
- **Issues**: https://github.com/kurral/kurralv3/issues
- **Email**: team@kurral.com

---

**You're now ready to use Kurral in production!** 🎉

The key insight: Treat your agent executions as **testable artifacts** that you can replay, compare, and optimize.
