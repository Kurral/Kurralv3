"""
Agent decorator for automatic artifact generation from LangChain agents
Minimal code changes - just add @trace_agent() decorator to your main function
"""

import functools
import inspect
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Dict

try:
    from langchain.agents import AgentExecutor
except ImportError:
    from langchain_core.agents import AgentExecutor

from kurral.langchain_integration import (
    ToolCallCaptureHandler,
    extract_llm_config_from_langchain,
    extract_resolved_prompt,
    compute_graph_version,
)
from kurral.models.kurral import (
    ModelConfig,
    ResolvedPrompt,
    ToolCall,
    TokenUsage,
    LLMParameters,
    KurralArtifact,
    TimeEnvironment,
)
from kurral.artifact_manager import ArtifactManager
from kurral.artifact_generator import ArtifactGenerator

T = TypeVar("T")

# Global context for current execution
_current_context: Optional[Dict[str, Any]] = None

# Session artifact context - accumulates all interactions in one artifact
_session_artifact: Optional[Any] = None  # Will hold KurralArtifact
_session_interactions: list[Dict[str, Any]] = []  # List of all interactions
_session_start_time: Optional[datetime] = None


def _sanitize_for_serialization(obj: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
    """Sanitize object for JSON serialization"""
    if current_depth >= max_depth:
        return "<max_depth_reached>"
    
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_for_serialization(v, max_depth, current_depth + 1) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_serialization(item, max_depth, current_depth + 1) for item in obj]
    elif hasattr(obj, "__dict__"):
        return _sanitize_for_serialization(obj.__dict__, max_depth, current_depth + 1)
    else:
        return str(obj)


def _get_agent_folder_path(func: Callable) -> Path:
    """Determine the agent folder path from the calling function's file location"""
    try:
        # Get the file path of the function
        file_path = inspect.getfile(func)
        func_path = Path(file_path).resolve()
        
        # If we're in a level*agent folder, use that
        # Otherwise default to current directory
        if "level" in func_path.parts and "agent" in func_path.parts:
            # Find the agent folder (e.g., level1agentK)
            parts = func_path.parts
            for i, part in enumerate(parts):
                if "level" in part.lower() and "agent" in part.lower():
                    # Return the agent folder path
                    agent_folder = Path(*parts[:i+1])
                    return agent_folder
        
        # Default: use directory containing the file
        return func_path.parent
    except:
        # Fallback: current directory
        return Path.cwd()


def trace_agent_invoke(
    agent_executor: AgentExecutor,
    input_data: Dict[str, Any],
    llm: Optional[Any] = None,  # Pass LLM directly for proper extraction
    tenant_id: str = "default",
    environment: str = "production",
    auto_export: bool = True,
    artifacts_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Wrapper for agent_executor.invoke() that automatically traces execution and generates artifacts
    
    Usage:
        # Instead of: result = agent_executor.invoke({"input": user_input})
        # Use: result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
    
    Args:
        agent_executor: The AgentExecutor instance
        input_data: Input dictionary (typically {"input": user_input})
        llm: Optional LLM object (if not provided, will try to extract from agent_executor)
        tenant_id: Tenant identifier
        environment: Environment name
        auto_export: Whether to save artifacts
        artifacts_dir: Optional explicit artifacts directory
        
    Returns:
        Result from agent_executor.invoke()
    """
    global _current_context
    
    # Determine artifacts directory
    if artifacts_dir is None:
        # Try to get from current context
        if _current_context and "artifacts_dir" in _current_context:
            artifacts_dir = _current_context["artifacts_dir"]
        else:
            # Default to ./artifacts in current directory
            artifacts_dir = Path.cwd() / "artifacts"
    
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine agent directory for config loading (parent of artifacts_dir)
    agent_dir = artifacts_dir.parent if artifacts_dir.name == "artifacts" else None
    
    # Create managers
    artifact_manager = ArtifactManager(storage_path=artifacts_dir, agent_dir=agent_dir)
    artifact_generator = ArtifactGenerator()
    
    # Start timing
    start_time = datetime.utcnow()
    start_ms = time.time() * 1000
    
    # Initialize capture handler
    tool_handler = ToolCallCaptureHandler()
    
    # Extract LLM and tools - use provided LLM or try to extract from agent_executor
    extracted_llm = llm
    # Only try to extract LLM if not provided
    if extracted_llm is None and hasattr(agent_executor, 'agent'):
        agent = agent_executor.agent
        
        # Try to get LLM from various locations
        # Method 1: Direct llm attribute
        if hasattr(agent, 'llm'):
            extracted_llm = agent.llm
        
        # Method 2: From llm_chain
        if extracted_llm is None and hasattr(agent, 'llm_chain'):
            if hasattr(agent.llm_chain, 'llm'):
                extracted_llm = agent.llm_chain.llm
        
        # Method 3: From runnable (for ReAct agents created with create_react_agent)
        if extracted_llm is None and hasattr(agent, 'runnable'):
            runnable = agent.runnable
            # Check if it's a RunnableSequence or similar
            if hasattr(runnable, 'runnables'):
                runnables = runnable.runnables
                # Try to find LLM in the runnable steps
                if hasattr(runnables, 'steps'):
                    for step in runnables.steps:
                        if hasattr(step, 'llm'):
                            extracted_llm = step.llm
                            break
                        elif hasattr(step, 'bound') and hasattr(step.bound, 'llm'):
                            extracted_llm = step.bound.llm
                            break
                # Also check if runnables itself has steps attribute
                elif hasattr(runnables, '__iter__'):
                    try:
                        for step in runnables:
                            if hasattr(step, 'llm'):
                                extracted_llm = step.llm
                                break
                            elif hasattr(step, 'bound') and hasattr(step.bound, 'llm'):
                                extracted_llm = step.bound.llm
                                break
                    except:
                        pass
            
            # Method 4: Try to get from the prompt chain if available
            if extracted_llm is None:
                try:
                    # For ReAct agents, the LLM might be in the prompt chain
                    if hasattr(runnable, 'first'):
                        first_runnable = runnable.first
                        if hasattr(first_runnable, 'llm'):
                            extracted_llm = first_runnable.llm
                    # Also try middle and last
                    if extracted_llm is None and hasattr(runnable, 'middle'):
                        for middle_runnable in runnable.middle:
                            if hasattr(middle_runnable, 'llm'):
                                extracted_llm = middle_runnable.llm
                                break
                    if extracted_llm is None and hasattr(runnable, 'last'):
                        if hasattr(runnable.last, 'llm'):
                            extracted_llm = runnable.last.llm
                except:
                    pass
        
        # Method 5: Try to extract from the agent's internal structure recursively
        if extracted_llm is None:
            try:
                def find_llm_in_obj(obj, depth=0, max_depth=5):
                    """Recursively search for LLM object"""
                    if depth > max_depth:
                        return None
                    if obj is None:
                        return None
                    # Check if this is an LLM object
                    class_name = obj.__class__.__name__.lower()
                    if any(x in class_name for x in ['chatopenai', 'chatgoogle', 'chatanthropic', 'chatollama']):
                        return obj
                    # Check attributes
                    for attr in ['llm', 'model', 'client']:
                        if hasattr(obj, attr):
                            candidate = getattr(obj, attr)
                            if candidate:
                                result = find_llm_in_obj(candidate, depth+1, max_depth)
                                if result:
                                    return result
                    # Check if it's iterable
                    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                        try:
                            for item in obj:
                                result = find_llm_in_obj(item, depth+1, max_depth)
                                if result:
                                    return result
                        except:
                            pass
                    return None
                
                extracted_llm = find_llm_in_obj(agent)
            except:
                pass
    
    tools = getattr(agent_executor, 'tools', [])
    
    # Extract user input
    user_input = str(input_data.get('input', ''))
    
    # Declare globals at the start
    global _session_artifact, _session_interactions
    
    # Execute with callbacks
    try:
        result = agent_executor.invoke(input_data, config={"callbacks": [tool_handler]})
    except Exception as e:
        error_msg = str(e)
        duration_ms = int(time.time() * 1000 - start_ms)
        
        # Append error interaction to session artifact
        if auto_export:
            # Extract LLM config and prompt for error case
            llm_config = extract_llm_config_from_langchain(extracted_llm) if extracted_llm else ModelConfig(
                model_name="unknown",
                provider="unknown",
                parameters=LLMParameters(temperature=0.0),
            )
            
            prompt = extract_resolved_prompt(agent_executor, user_input)
            graph_version = compute_graph_version(tools, prompt) if tools else None
            
            # Initialize session artifact if needed
            if _session_artifact is None:
                run_id = f"local_agent_{int(start_time.timestamp())}"
                _session_artifact = artifact_generator.generate(
                    run_id=run_id,
                    tenant_id=tenant_id,
                    inputs={"interactions": []},
                    outputs={"interactions": []},
                    llm_config=llm_config,
                    resolved_prompt=prompt,
                    tool_calls=[],
                    duration_ms=0,
                    error=None,  # Will be set per interaction
                )
                
                if graph_version:
                    _session_artifact.graph_version = graph_version
            
            # Append error interaction
            interaction = {
                "input": _sanitize_for_serialization(input_data),
                "output": {"error": error_msg},
                "tool_calls": tool_handler.tool_calls,
                "duration_ms": duration_ms,
                "timestamp": start_time.isoformat(),
                "error": error_msg,
            }
            _session_interactions.append(interaction)
            
            # Update artifact
            _session_artifact.inputs = {"interactions": [i["input"] for i in _session_interactions]}
            _session_artifact.outputs = {"interactions": [i["output"] for i in _session_interactions]}
            
            all_tool_calls = []
            for interaction in _session_interactions:
                all_tool_calls.extend(interaction["tool_calls"])
            _session_artifact.tool_calls = all_tool_calls
            
            # Set error if any interaction had an error
            if any(i.get("error") for i in _session_interactions):
                _session_artifact.error = "One or more interactions failed"
        
        raise
    
    # Stop timing
    duration_ms = int(time.time() * 1000 - start_ms)
    
    # Extract LLM config
    llm_config = extract_llm_config_from_langchain(extracted_llm) if extracted_llm else ModelConfig(
        model_name="unknown",
        provider="unknown",
        parameters=LLMParameters(temperature=0.0),
    )
    
    # Extract prompt
    prompt = extract_resolved_prompt(agent_executor, user_input)
    
    # Compute graph version
    graph_version = compute_graph_version(tools, prompt) if tools else None
    
    # Prepare outputs
    outputs = _sanitize_for_serialization(result)
    
    # Append to session artifact instead of creating a new one
    if auto_export:
        # Check if we have a session artifact (created by decorator)
        if _session_artifact is None:
            # First interaction - create the artifact
            run_id = f"local_agent_{int(start_time.timestamp())}"
            _session_artifact = artifact_generator.generate(
                run_id=run_id,
                tenant_id=tenant_id,
                inputs={"interactions": []},  # Will accumulate interactions
                outputs={"interactions": []},  # Will accumulate interactions
                llm_config=llm_config,
                resolved_prompt=prompt,
                tool_calls=[],  # Will accumulate all tool calls
                duration_ms=0,  # Will be updated at the end
            )
            
            # Set graph_version after artifact creation
            if graph_version:
                _session_artifact.graph_version = graph_version
        
        # Append this interaction to the session
        interaction = {
            "input": _sanitize_for_serialization(input_data),
            "output": outputs,
            "tool_calls": tool_handler.tool_calls,
            "duration_ms": duration_ms,
            "timestamp": start_time.isoformat(),
        }
        _session_interactions.append(interaction)
        
        # Update artifact with accumulated data
        _session_artifact.inputs = {"interactions": [i["input"] for i in _session_interactions]}
        _session_artifact.outputs = {"interactions": [i["output"] for i in _session_interactions]}
        
        # Accumulate all tool calls
        all_tool_calls = []
        for interaction in _session_interactions:
            all_tool_calls.extend(interaction["tool_calls"])
        _session_artifact.tool_calls = all_tool_calls
        
        # Update total duration
        total_duration = sum(i["duration_ms"] for i in _session_interactions)
        _session_artifact.duration_ms = total_duration
    
    return result


def trace_agent(
    tenant_id: str = "default",
    environment: str = "production",
    auto_export: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for tracing LangChain agent execution and generating artifacts
    
    Usage:
        @trace_agent()
        def main():
            # Your agent code here
            agent_executor = AgentExecutor(...)
            # Replace agent_executor.invoke() with trace_agent_invoke()
            from kurral.agent_decorator import trace_agent_invoke
            result = trace_agent_invoke(agent_executor, {"input": user_input})
            return result
    
    The decorator sets up the artifacts directory. You still need to use
    trace_agent_invoke() instead of agent_executor.invoke() for minimal changes.
    
    Args:
        tenant_id: Tenant identifier
        environment: Environment name (production, staging, etc.)
        auto_export: Whether to automatically save artifacts
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            global _current_context, _session_artifact, _session_interactions, _session_start_time
            
            # Determine artifacts directory from function location
            agent_folder = _get_agent_folder_path(func)
            artifacts_dir = agent_folder / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize session
            _session_start_time = datetime.utcnow()
            _session_artifact = None
            _session_interactions = []
            
            # Set current context
            _current_context = {
                "artifacts_dir": artifacts_dir,
                "tenant_id": tenant_id,
                "environment": environment,
            }
            
            # Pass agent folder for config loading
            artifact_manager = ArtifactManager(storage_path=artifacts_dir, agent_dir=agent_folder)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                return result
            finally:
                # Save the accumulated artifact if we have interactions
                if auto_export and _session_artifact is not None and len(_session_interactions) > 0:
                    try:
                        # Update final duration
                        if _session_start_time:
                            total_duration = int((datetime.utcnow() - _session_start_time).total_seconds() * 1000)
                            _session_artifact.duration_ms = total_duration
                        
                        # Update time_env
                        _session_artifact.time_env = TimeEnvironment(
                            timestamp=_session_start_time,
                            timezone="UTC",
                            wall_clock_time=_session_start_time.isoformat(),
                        )
                        
                        artifact_path = artifact_manager.save(_session_artifact)
                        print(f"\n[Kurral] Session artifact saved: {artifact_path}")
                        print(f"[Kurral] Run ID: {_session_artifact.run_id}")
                        print(f"[Kurral] Kurral ID: {_session_artifact.kurral_id}")
                        print(f"[Kurral] Total interactions: {len(_session_interactions)}")
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        print(f"\n[Kurral] ERROR: Failed to save session artifact: {e}")
                        print(f"[Kurral] Error details:\n{error_details}")
                        # Try to save error details to a file for debugging
                        try:
                            error_log_path = artifacts_dir / "artifact_save_error.log"
                            with open(error_log_path, "a") as f:
                                f.write(f"\n=== {datetime.utcnow().isoformat()} ===\n")
                                f.write(f"Failed to save artifact: {e}\n")
                                f.write(f"{error_details}\n")
                            print(f"[Kurral] Error details saved to: {error_log_path}")
                        except:
                            pass
                
                # Clear context
                _current_context = None
                _session_artifact = None
                _session_interactions = []
                _session_start_time = None
        
        return wrapper
    
    return decorator

