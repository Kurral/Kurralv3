"""
Customer Support Agent - Kurral Production Example

Demonstrates:
- Multi-turn conversations with context retention
- Knowledge base lookup (deterministic, fast)
- Web search for real-time info (e.g., order status, product availability)
- Professional, empathetic tone
- Kurral replay for regression testing support scenarios

Cost comparison:
- Without Kurral: Testing 20 support scenarios = ~$2-5
- With Kurral: Capture once ($0.10), replay unlimited times = $0

Generated from: kurral init (vanilla template)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
load_dotenv()

# Kurral integration
from kurral import trace_agent, trace_agent_invoke


# ===================================================================
# TOOLS
# ===================================================================

def search_knowledge_base(query: str) -> str:
    """
    Search FAQ knowledge base for relevant answers.

    Deterministic tool - perfect for Kurral replay!
    """
    kb_path = Path(__file__).parent / "knowledge_base" / "faqs.json"

    try:
        with open(kb_path) as f:
            kb = json.load(f)

        # Simple keyword matching (production would use embeddings)
        query_lower = query.lower()
        results = []

        for category, faqs in kb.items():
            for faq in faqs:
                q = faq["question"].lower()
                a = faq["answer"]

                # Match keywords
                if any(word in q for word in query_lower.split()):
                    results.append(f"Q: {faq['question']}\nA: {a}\nCategory: {category}")

        if not results:
            return "No matching FAQs found. Consider using web_search for real-time information."

        return "\n\n".join(results[:3])  # Top 3 matches

    except Exception as e:
        return f"Error accessing knowledge base: {e}"


def web_search(query: str) -> str:
    """
    Search web for real-time information.

    Note: This is a simplified version. Production would use Tavily API.
    """
    # Mock for demo purposes
    return f"""[WEB SEARCH RESULTS]
Query: {query}

1. Company Status Page
   Our systems are currently operational. No service disruptions reported.

2. Latest Shipping Updates
   Current processing time: 1-2 business days. Holiday shipping deadlines apply.

3. Product Availability
   Most items in stock and ready to ship. Check specific product pages for details.

💡 Set TAVILY_API_KEY in .env for real web search results.
"""


# ===================================================================
# LLM CLIENT
# ===================================================================

def call_llm(messages: list[dict], model: str, temperature: float, api_key: str, mock: bool) -> str:
    """Call OpenAI API."""
    if mock:
        return (
            "THOUGHT: I should check our knowledge base for shipping information.\n"
            "ACTION: search_knowledge_base\n"
            "INPUT: shipping options"
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Missing 'openai'. Run: pip install openai")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages
    )

    return resp.choices[0].message.content or ""


# ===================================================================
# AGENT LOOP
# ===================================================================

TOOLS = {
    "search_knowledge_base": search_knowledge_base,
    "web_search": web_search,
}

TOOL_DESCRIPTIONS = {
    "search_knowledge_base": "Search company FAQ/knowledge base for policies, procedures, common questions. Fast and deterministic.",
    "web_search": "Search web for real-time information like order status, product availability, service status.",
}

SYSTEM_PROMPT = """You are a helpful customer support agent.

You MUST respond in one of these formats:

1) If you need a tool:
THOUGHT: <brief reasoning>
ACTION: <tool_name>
INPUT: <tool_input>

2) If you're ready to answer:
FINAL: <your empathetic, professional response>

Available tools:
{tool_list}

Guidelines:
- Always check knowledge_base first for FAQs/policies
- Be professional, empathetic, and concise
- If unsure, acknowledge it and offer to escalate
- Use web_search for real-time info (order status, availability)
"""


def parse_action(text: str) -> Dict[str, str]:
    """Parse model output."""
    t = text.strip()

    if t.startswith("FINAL:"):
        return {"type": "final", "final": t[len("FINAL:"):].strip()}

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    action = None
    tool_input = None

    for ln in lines:
        if ln.startswith("ACTION:"):
            action = ln[len("ACTION:"):].strip()
        elif ln.startswith("INPUT:"):
            tool_input = ln[len("INPUT:"):].strip()

    if not action:
        return {"type": "final", "final": t}

    return {"type": "tool", "tool": action, "input": tool_input or ""}


def run_agent(user_input: str, model: str, temperature: float, api_key: str, mock: bool, max_steps: int = 6) -> Dict[str, Any]:
    """Run customer support agent loop."""
    tool_list = "\n".join([f"- {k}: {TOOL_DESCRIPTIONS[k]}" for k in TOOLS.keys()])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(tool_list=tool_list)},
        {"role": "user", "content": user_input},
    ]

    for step in range(1, max_steps + 1):
        assistant_text = call_llm(messages, model=model, temperature=temperature, api_key=api_key, mock=mock)
        action = parse_action(assistant_text)

        if action["type"] == "final":
            return {"output": action["final"], "steps": step}

        tool_name = action["tool"]
        tool_in = action["input"]

        if tool_name not in TOOLS:
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": f"Tool '{tool_name}' not available. Use: {list(TOOLS.keys())}."})
            continue

        try:
            tool_fn = TOOLS[tool_name]
            tool_out = tool_fn(tool_in)
        except Exception as e:
            tool_out = f"ERROR: {e}"

        messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "tool", "content": tool_out, "name": tool_name})

    return {"output": "Reached max steps. Please try again or contact human support.", "steps": max_steps}


# ===================================================================
# MAIN
# ===================================================================

@trace_agent()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run without API (demo mode)")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model")
    parser.add_argument("--temperature", type=float, default=0.3, help="Temperature (0.3 for consistent support)")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "")

    if not args.mock and not api_key:
        print("❌ OPENAI_API_KEY not set. Run with --mock or set API key in .env")
        sys.exit(1)

    print("=" * 60)
    print("  Customer Support Agent (Powered by Kurral)")
    print("=" * 60)
    print()
    print("🛠️ Available tools:")
    for name, desc in TOOL_DESCRIPTIONS.items():
        print(f"  - {name}: {desc}")
    print()
    print("💡 Try asking about: shipping, returns, account, pricing")
    print()

    user_input = input("Customer: ").strip()
    if not user_input:
        print("❌ No input provided.")
        sys.exit(1)

    print("\n🤖 Agent processing...\n" + "-" * 60)

    result = trace_agent_invoke(
        run_agent,
        user_input=user_input,
        model=args.model,
        temperature=args.temperature,
        api_key=api_key,
        mock=args.mock
    )

    print("-" * 60)
    print("\n✅ Agent Response:\n")
    print(result["output"])
    print()

    artifact_dir = Path.cwd() / "artifacts"
    if artifact_dir.exists():
        artifacts = sorted(artifact_dir.iterdir())
        if artifacts:
            latest = artifacts[-1].name
            print(f"📦 Captured: artifacts/{latest}")
            print(f"   Replay: kurral replay {latest.replace('.kurral', '')}")

    print()
    print("💡 Testing tip: Run this 20 times with different queries,")
    print("   then replay all with 'kurral replay --latest' → $0 cost!")

    return result


if __name__ == "__main__":
    main()
