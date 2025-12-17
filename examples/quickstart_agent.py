"""
Kurral Quick Start Example - Research Assistant

This is a simple, copy-paste ready example that demonstrates Kurral's core value.

Time to run: 2 minutes
Prerequisites: pip install kurral langchain langchain-openai

What you'll see:
1. Agent executes with multiple tool calls
2. .kurral artifact generated automatically
3. Instructions to replay and see ARS scoring
"""

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from kurral import trace_agent, trace_agent_invoke


# ==============================================================================
# TOOLS (Mock implementations for demo - no external APIs needed)
# ==============================================================================

def search_wikipedia(query: str) -> str:
    """Search Wikipedia for information (mock implementation)"""
    # Mock responses - in production this would call real Wikipedia API
    knowledge_base = {
        "python": "Python is a high-level, interpreted programming language created by Guido van Rossum, first released in 1991. It emphasizes code readability with significant indentation.",
        "ai": "Artificial Intelligence (AI) is the simulation of human intelligence by machines. It includes learning, reasoning, and self-correction. Major subfields include machine learning, neural networks, and natural language processing.",
        "tesla": "Tesla, Inc. is an American electric vehicle and clean energy company founded in 2003. CEO Elon Musk joined in 2004. Known for Model S, Model 3, Model X, and Model Y vehicles.",
        "kurral": "Kurral is an open-source testing and replay framework for AI agents. It captures complete execution traces and enables deterministic replay for regression testing and debugging.",
    }

    query_lower = query.lower()
    for key, value in knowledge_base.items():
        if key in query_lower:
            return f"[Wikipedia] {value}"

    return f"[Wikipedia] No specific information found for '{query}'. This is a mock search result."


def calculate(expression: str) -> str:
    """Perform mathematical calculations (safe eval for demo)"""
    try:
        # WARNING: Never use eval() in production! This is just for demo.
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_current_date() -> str:
    """Get today's date"""
    from datetime import datetime
    return f"Today is {datetime.now().strftime('%B %d, %Y')}"


# ==============================================================================
# AGENT SETUP
# ==============================================================================

tools = [
    Tool(
        name="search_wikipedia",
        func=search_wikipedia,
        description="Search Wikipedia for information about topics. Input should be a search query string."
    ),
    Tool(
        name="calculator",
        func=calculate,
        description="Perform mathematical calculations. Input should be a math expression like '25 * 4' or '(10 + 5) / 3'."
    ),
    Tool(
        name="get_date",
        func=get_current_date,
        description="Get today's date. No input needed."
    )
]

# ReAct prompt template
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


# ==============================================================================
# KURRAL-INSTRUMENTED MAIN FUNCTION
# ==============================================================================

@trace_agent()  # 👈 This decorator captures everything!
def main():
    """
    Main agent function - all interactions within this function
    are captured in a single .kurral artifact
    """

    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,  # Deterministic for better replay
    )

    # Create agent
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # See the agent's thinking process
        handle_parsing_errors=True
    )

    # Test question
    question = "What is Python? Also, what is 15 * 23?"

    print("\n" + "="*70)
    print("KURRAL QUICKSTART EXAMPLE")
    print("="*70)
    print(f"\nQuestion: {question}\n")
    print("="*70 + "\n")

    # Execute agent with Kurral tracing
    result = trace_agent_invoke(
        agent_executor,
        {"input": question},
        llm=llm  # 👈 Pass llm for accurate config capture
    )

    print("\n" + "="*70)
    print("FINAL ANSWER")
    print("="*70)
    print(f"\n{result['output']}\n")
    print("="*70 + "\n")

    return result


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                   KURRAL QUICKSTART EXAMPLE                           ║
║                                                                       ║
║  This example demonstrates:                                           ║
║  1. Capturing a complete agent execution trace                        ║
║  2. Automatic .kurral artifact generation                             ║
║  3. Tool call instrumentation                                         ║
║                                                                       ║
║  After running this:                                                  ║
║  • Check the artifacts/ folder for your .kurral file                  ║
║  • Try: kurral replay --latest                                        ║
║  • See ARS score and replay results                                   ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)

    try:
        main()

        print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                           SUCCESS! 🎉                                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  Your agent execution was captured in a .kurral artifact!             ║
║                                                                       ║
║  Next steps:                                                          ║
║  1. Check artifacts/ folder for your .kurral file                     ║
║  2. Configure side effects:                                           ║
║     - Run: kurral replay --latest                                     ║
║     - Edit side_effect/side_effects.yaml                              ║
║     - Set done: true                                                  ║
║  3. Replay again to see ARS scoring                                   ║
║  4. Try modifying the agent and replay to see behavior changes        ║
║                                                                       ║
║  Example modifications to try:                                        ║
║  • Change model from gpt-4 to gpt-3.5-turbo                           ║
║  • Modify the prompt template                                         ║
║  • Add/remove tools                                                   ║
║  • Change temperature parameter                                       ║
║                                                                       ║
║  Then replay and compare ARS scores!                                  ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

Quick commands:
  kurral replay --latest              # Replay your latest artifact
  kurral list                         # List all artifacts
  kurral stats                        # Show statistics
  cat artifacts/*.kurral | python -m json.tool | head -50  # View artifact

Dashboard (optional):
  cd dashboard && npm install && npm run dev
  Then drag-and-drop your .kurral file at http://localhost:5173

Need help? https://discord.gg/pan6GRRV
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        print("Make sure you have:")
        print("  1. Installed dependencies: pip install kurral langchain langchain-openai")
        print("  2. Set OPENAI_API_KEY environment variable")
        print("\nFor help: https://github.com/kurral/kurralv3/issues")
