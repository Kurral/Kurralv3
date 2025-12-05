"""
Simple LangGraph POC Example
Tests @trace_graph() decorator with minimal StateGraph

This is a POC test - not production code!
"""

import sys
from pathlib import Path
from typing import TypedDict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Check if LangGraph is installed
try:
    from langgraph.graph import StateGraph, END
    from kurral.langgraph_integration import trace_graph
    print("✓ LangGraph and Kurral integration loaded successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nTo run this POC, install:")
    print("  pip install langgraph>=1.0.0")
    sys.exit(1)


# Define state schema
class AgentState(TypedDict):
    """Simple state with messages"""
    messages: list
    count: int
    result: str


def process_node(state: AgentState) -> AgentState:
    """Simple processing node - just counts messages"""
    messages = state.get("messages", [])
    count = len(messages)
    result = f"Processed {count} messages"

    print(f"  [Node: process] Processing {count} messages...")

    return {
        "messages": messages,
        "count": count,
        "result": result
    }


def format_node(state: AgentState) -> AgentState:
    """Formatting node - creates final output"""
    result = state.get("result", "")
    count = state.get("count", 0)

    formatted = f"FINAL: {result} (Total: {count})"
    print(f"  [Node: format] Creating output: {formatted}")

    return {
        **state,
        "result": formatted
    }


@trace_graph()
def build_simple_graph():
    """
    Build a simple 2-node graph for POC testing

    Graph structure:
      START → process → format → END
    """
    print("\n[Building Graph]")

    # Create StateGraph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("process", process_node)
    graph.add_node("format", format_node)

    # Add edges
    graph.set_entry_point("process")
    graph.add_edge("process", "format")
    graph.add_edge("format", END)

    print("  ✓ Graph structure defined")
    print("  ✓ Nodes: process, format")
    print("  ✓ Entry point: process")

    # Compile and return
    compiled = graph.compile()
    print("  ✓ Graph compiled successfully\n")

    return compiled


def main():
    """Run the POC test"""
    print("=" * 60)
    print("LangGraph POC Test - Simple State Graph")
    print("=" * 60)

    # Build the graph (decorator applies tracing)
    app = build_simple_graph()

    # Test input
    test_input = {
        "messages": ["Hello", "World", "Test"],
        "count": 0,
        "result": ""
    }

    print("[Executing Graph]")
    print(f"  Input: {test_input['messages']}")
    print()

    # Invoke the graph (tracing happens automatically)
    result = app.invoke(test_input)

    print("\n[Execution Complete]")
    print(f"  Output: {result['result']}")
    print(f"  Count: {result['count']}")

    print("\n" + "=" * 60)
    print("✓ POC Test Completed")
    print("=" * 60)

    # Check if artifact was created
    artifacts_dir = Path.cwd() / "artifacts"
    if artifacts_dir.exists():
        artifacts = list(artifacts_dir.glob("*.kurral"))
        if artifacts:
            latest = max(artifacts, key=lambda p: p.stat().st_mtime)
            print(f"\n✓ Artifact created: {latest.name}")
            print(f"  Location: {artifacts_dir}")
        else:
            print("\n✗ No artifacts found (expected one)")
    else:
        print("\n✗ Artifacts directory not created")

    return result


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
