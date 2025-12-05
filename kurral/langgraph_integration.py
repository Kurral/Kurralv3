"""
LangGraph integration for Kurral artifact generation
Provides @trace_graph() decorator for StateGraph-based agents

Compatible with LangChain v1 + LangGraph v1
"""

import functools
import hashlib
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar
from pathlib import Path

try:
    from langgraph.graph import StateGraph
    from langgraph.graph.graph import CompiledGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    CompiledGraph = None

from kurral.models.kurral import (
    KurralArtifact,
    ModelConfig,
    LLMParameters,
    ToolCall,
    ToolCallStatus,
    GraphVersion,
)
from kurral.artifact_manager import ArtifactManager

T = TypeVar("T")


class GraphExecutionTracker:
    """
    Tracks state transitions and tool calls during LangGraph execution
    Uses LangChain v1 patterns for capturing execution data
    """

    def __init__(self):
        self.node_executions: List[Dict[str, Any]] = []
        self.tool_calls: List[ToolCall] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.graph_structure: Optional[Dict[str, Any]] = None

    def on_node_enter(self, node_name: str, state: Dict[str, Any]):
        """Called when entering a graph node"""
        self.node_executions.append({
            "node": node_name,
            "action": "enter",
            "timestamp": datetime.utcnow().isoformat(),
            "state_keys": list(state.keys()) if state else [],
        })

    def on_node_exit(self, node_name: str, state: Dict[str, Any], output: Any):
        """Called when exiting a graph node"""
        self.node_executions.append({
            "node": node_name,
            "action": "exit",
            "timestamp": datetime.utcnow().isoformat(),
            "output_type": type(output).__name__ if output else None,
        })

    def capture_graph_structure(self, compiled_graph: Any):
        """Extract and hash graph structure for determinism tracking"""
        try:
            # LangGraph v1 - try to extract node and edge information
            nodes = []
            edges = []

            if hasattr(compiled_graph, 'nodes'):
                nodes = list(compiled_graph.nodes.keys()) if hasattr(compiled_graph.nodes, 'keys') else []

            if hasattr(compiled_graph, 'edges'):
                # Extract edge information
                edges = str(compiled_graph.edges) if compiled_graph.edges else ""

            self.graph_structure = {
                "nodes": nodes,
                "edges": edges,
                "entry_point": getattr(compiled_graph, 'entry_point', None),
            }

        except Exception as e:
            # Fallback for structure extraction
            self.graph_structure = {
                "error": f"Could not extract graph structure: {str(e)}",
                "type": type(compiled_graph).__name__,
            }


def trace_graph(
    tenant_id: str = "default",
    environment: str = "production",
    auto_export: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for LangGraph StateGraph functions

    Usage:
        @trace_graph()
        def build_agent():
            from langgraph.graph import StateGraph, END

            class AgentState(TypedDict):
                messages: list
                data: dict

            graph = StateGraph(AgentState)
            graph.add_node("process", process_node)
            graph.set_entry_point("process")
            graph.add_edge("process", END)

            return graph.compile()

    Args:
        tenant_id: Tenant identifier for multi-tenant deployments
        environment: Environment name (production, staging, etc.)
        auto_export: Whether to automatically save artifacts

    Returns:
        Decorated function that returns a traced CompiledGraph
    """

    if not LANGGRAPH_AVAILABLE:
        raise ImportError(
            "LangGraph is not installed. "
            "Install it with: pip install langgraph>=1.0.0"
        )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build the graph
            compiled_graph = func(*args, **kwargs)

            # Create tracker
            tracker = GraphExecutionTracker()
            tracker.capture_graph_structure(compiled_graph)

            # Wrap the invoke method to capture execution
            original_invoke = compiled_graph.invoke

            def traced_invoke(inputs, config=None):
                """Traced version of graph.invoke()"""
                tracker.start_time = datetime.utcnow()

                try:
                    # Execute the graph
                    result = original_invoke(inputs, config)
                    tracker.end_time = datetime.utcnow()

                    # Generate artifact
                    if auto_export:
                        _generate_and_save_artifact(
                            inputs=inputs,
                            outputs=result,
                            tracker=tracker,
                            tenant_id=tenant_id,
                            environment=environment,
                        )

                    return result

                except Exception as e:
                    tracker.end_time = datetime.utcnow()
                    # Still try to save artifact with error info
                    if auto_export:
                        _generate_and_save_artifact(
                            inputs=inputs,
                            outputs={"error": str(e)},
                            tracker=tracker,
                            tenant_id=tenant_id,
                            environment=environment,
                            error=e,
                        )
                    raise

            # Replace invoke method
            compiled_graph.invoke = traced_invoke

            return compiled_graph

        return wrapper
    return decorator


def _generate_and_save_artifact(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    tracker: GraphExecutionTracker,
    tenant_id: str,
    environment: str,
    error: Optional[Exception] = None,
):
    """Generate Kurral artifact from LangGraph execution"""

    # Create artifact directory
    artifacts_dir = Path.cwd() / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Compute graph version hash
    graph_hash = _compute_graph_hash(tracker.graph_structure)

    # Build GraphVersion
    graph_version = GraphVersion(
        schema_hash=graph_hash,
        tools_hash=graph_hash,  # For now, use same hash
        tool_names=tracker.graph_structure.get("nodes", []) if tracker.graph_structure else [],
    )

    # Calculate duration
    duration_ms = 0
    if tracker.start_time and tracker.end_time:
        duration_ms = int((tracker.end_time - tracker.start_time).total_seconds() * 1000)

    # Build artifact
    artifact = KurralArtifact(
        tenant_id=tenant_id,
        environment=environment,
        inputs={"interactions": [{"input": inputs}]},
        outputs={"interactions": [{"output": outputs}]},
        llm_config=ModelConfig(
            model_name="langgraph",  # Placeholder - would extract from nodes
            provider="langgraph",
            parameters=LLMParameters(temperature=0.0),
        ),
        tool_calls=tracker.tool_calls,
        graph_version=graph_version,
        execution_metadata={
            "framework": "langgraph",
            "framework_version": "1.0",
            "node_executions": tracker.node_executions,
            "graph_structure": tracker.graph_structure,
        },
        start_time=tracker.start_time or datetime.utcnow(),
        end_time=tracker.end_time or datetime.utcnow(),
        duration_ms=duration_ms,
        error_info={"error": str(error)} if error else None,
    )

    # Save artifact
    artifact_manager = ArtifactManager(storage_path=artifacts_dir)
    saved_path = artifact_manager.save_artifact(artifact)

    print(f"[Kurral] LangGraph artifact saved: {saved_path}")
    print(f"[Kurral] Kurral ID: {artifact.kurral_id}")
    print(f"[Kurral] Graph nodes: {len(tracker.graph_structure.get('nodes', []))} nodes executed")


def _compute_graph_hash(graph_structure: Optional[Dict[str, Any]]) -> str:
    """Compute deterministic hash of graph structure"""
    if not graph_structure:
        return "no-structure"

    # Create stable JSON representation
    stable_repr = json.dumps(graph_structure, sort_keys=True)
    return hashlib.sha256(stable_repr.encode()).hexdigest()[:16]


# Export main decorator
__all__ = ["trace_graph", "GraphExecutionTracker"]
