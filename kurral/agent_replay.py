"""
Simple agent replay function
Usage: from kurral.agent_replay import replay_agent_artifact
       replay_agent_artifact("810c48c1-fc9c-4ec4-a4f5-7fb7ed86506d")
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path if running as module from agent directory
if __name__ == "__main__":
    current_file = Path(__file__).resolve()
    # If we're in kurral, add parent to path
    if "kurral" in current_file.parts:
        project_root = current_file.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

from kurral.models.kurral import KurralArtifact
from kurral.artifact_manager import ArtifactManager
from kurral.replay_detector import ReplayDetector
from kurral.replay_executor import ReplayExecutor
from kurral.artifact_generator import ArtifactGenerator
from kurral.tool_stubber import ToolStubber, create_stubbed_tool
from kurral.ars_scorer import calculate_ars
from kurral.side_effect_config import SideEffectConfig


def _import_agent_module_with_optional_deps(agent_folder, verbose=True):
    """
    Import agent module while handling missing optional dependencies.
    
    Args:
        agent_folder: Path to the agent folder
        verbose: Whether to print warnings
        
    Returns:
        agent_module or None if import fails
    """
    import importlib
    import importlib.util
    
    # Add paths to sys.path
    project_root = agent_folder.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(agent_folder) not in sys.path:
        sys.path.insert(0, str(agent_folder))
    
    # First, try normal import
    try:
        agent_module = importlib.import_module(f"{agent_folder.name}.agent")
        return agent_module
    except ImportError as e:
        # Check if it's an optional dependency issue
        error_msg = str(e).lower()
        optional_deps = ['langchain_google_genai', 'langchain_anthropic', 'langchain_cohere']
        is_optional_dep_error = any(dep in error_msg for dep in optional_deps)
        
        if is_optional_dep_error:
            # Try using importlib.util to load with tolerant import
            try:
                agent_path = agent_folder / "agent.py"
                if not agent_path.exists():
                    if verbose:
                        print(f"Warning: Agent file not found: {agent_path}")
                    return None
                
                # Create a tolerant import wrapper
                import builtins
                original_import = builtins.__import__
                
                def tolerant_import(name, globals=None, locals=None, fromlist=(), level=0):
                    """Import that allows optional dependencies to fail silently"""
                    # Check if this is an optional dependency
                    optional_deps = ['langchain_google_genai', 'langchain_anthropic', 'langchain_cohere']
                    if any(name == dep or name.startswith(f"{dep}.") for dep in optional_deps):
                        try:
                            return original_import(name, globals, locals, fromlist, level)
                        except ImportError:
                            # Return a dummy module that handles attribute access
                            class DummyModule:
                                def __getattr__(self, name):
                                    return DummyModule()
                                def __call__(self, *args, **kwargs):
                                    return DummyModule()
                            return DummyModule()
                    return original_import(name, globals, locals, fromlist, level)
                
                # Temporarily replace __import__
                builtins.__import__ = tolerant_import
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"{agent_folder.name}.agent",
                        agent_path,
                        submodule_search_locations=[str(agent_folder)]
                    )
                    if spec and spec.loader:
                        agent_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(agent_module)
                        return agent_module
                finally:
                    # Restore original import
                    builtins.__import__ = original_import
            except Exception as e2:
                if verbose:
                    print(f"Warning: Could not import agent module with tolerant import: {e2}")
                return None
        else:
            # Not an optional dependency error, re-raise
            if verbose:
                print(f"Warning: Could not import agent module: {e}")
            return None
    
    return None


def replay_agent_artifact(
    kurral_id: Optional[str] = None,
    run_id: Optional[str] = None,
    latest: bool = False,
    artifacts_dir: Optional[Path] = None,
    verbose: bool = True,
) -> dict:
    """
    Replay an agent artifact - simple interface
    
    Args:
        kurral_id: Kurral ID (UUID string) of artifact to replay
        run_id: Run ID of artifact to replay
        latest: If True, replay the latest artifact
        artifacts_dir: Path to artifacts directory (defaults to ./artifacts)
        verbose: Print detailed output
        
    Returns:
        dict with replay results
    """
    # Determine artifacts directory
    if artifacts_dir is None:
        # Smart auto-detection: prioritize current directory (when running from agent folder)
        cwd = Path.cwd()
        
        # Priority 1: Current directory has artifacts/ folder (most common - running from agent directory)
        if (cwd / "artifacts").exists():
            artifacts_dir = cwd / "artifacts"
        # Priority 2: Check if we're in an agent folder (has agent.py) - create artifacts if needed
        elif (cwd / "agent.py").exists():
            artifacts_dir = cwd / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
        # Priority 3: Check parent directory (in case we're one level deeper)
        elif (cwd.parent / "artifacts").exists():
            artifacts_dir = cwd.parent / "artifacts"
        # Priority 4: Search for agent folders with artifacts in current directory
        else:
            found = False
            for path in cwd.iterdir():
                if path.is_dir() and "agent" in path.name.lower() and (path / "artifacts").exists():
                    artifacts_dir = path / "artifacts"
                    found = True
                    break
            
            if not found:
                # Default to current directory
                artifacts_dir = cwd / "artifacts"
    else:
        artifacts_dir = Path(artifacts_dir)
    
    if not artifacts_dir.exists():
        print(f"Error: Artifacts directory not found: {artifacts_dir}")
        print(f"Current working directory: {Path.cwd()}")
        print(f"Please run replay from the agent directory or specify --artifacts-dir")
        return {}
    
    # Print which artifacts directory we're using (for debugging)
    if verbose:
        print(f"[Kurral] Using artifacts directory: {artifacts_dir}")
    
    # Try to determine agent directory (parent of artifacts_dir)
    agent_dir = artifacts_dir.parent if artifacts_dir.name == "artifacts" else None
    
    # Create ArtifactManager with config support
    artifact_manager = ArtifactManager(
        storage_path=artifacts_dir,
        agent_dir=agent_dir
    )
    
    # Ensure R2 migration before loading artifacts
    if artifact_manager.using_r2:
        print("Loading R2...")
        migration_stats = artifact_manager.ensure_r2_migration(show_message=False)
        if migration_stats["migrated"] > 0:
            print(f"Migrated {migration_stats['migrated']} artifact(s) to R2")
            if migration_stats["skipped"] > 0:
                print(f"Skipped {migration_stats['skipped']} (already in R2)")
        elif migration_stats.get("message"):
            print(migration_stats["message"])
    
    # Load artifact
    artifact = None
    if latest:
        artifact = artifact_manager.load_latest()
    elif run_id:
        artifact = artifact_manager.load_by_run_id(run_id)
    elif kurral_id:
        from uuid import UUID
        try:
            # Try as full UUID first
            uuid_obj = UUID(kurral_id)
            artifact = artifact_manager.load(uuid_obj)
            # Check if artifact was found
            if artifact is None:
                # UUID was valid but artifact not found - try partial match
                all_artifacts = artifact_manager.list_artifacts()
                if not all_artifacts:
                    print(f"Error: No artifacts found in {artifacts_dir}")
                    print(f"Looking for artifact: {kurral_id}")
                    return {}
                print(f"Error: Artifact '{kurral_id}' not found in {artifacts_dir}")
                print(f"Available artifacts ({len(all_artifacts)}):")
                for a in all_artifacts[:5]:  # Show first 5
                    print(f"  - {a.kurral_id}")
                if len(all_artifacts) > 5:
                    print(f"  ... and {len(all_artifacts) - 5} more")
                return {}
        except ValueError:
            # If not a valid UUID, try to find by partial match
            all_artifacts = artifact_manager.list_artifacts()
            if not all_artifacts:
                print(f"Error: No artifacts found in {artifacts_dir}")
                print(f"Looking for artifact matching: {kurral_id}")
                return {}
            
            matching = [a for a in all_artifacts if str(a.kurral_id).startswith(kurral_id)]
            if len(matching) == 1:
                artifact = matching[0]
            elif len(matching) > 1:
                print(f"Error: Multiple artifacts match '{kurral_id}'. Please use full UUID.")
                print(f"Found {len(matching)} matching artifacts:")
                for a in matching:
                    print(f"  - {a.kurral_id}")
                return {}
            else:
                print(f"Error: No artifact found matching '{kurral_id}'")
                print(f"Searched in: {artifacts_dir}")
                print(f"Available artifacts ({len(all_artifacts)}):")
                for a in all_artifacts[:5]:  # Show first 5
                    print(f"  - {a.kurral_id}")
                if len(all_artifacts) > 5:
                    print(f"  ... and {len(all_artifacts) - 5} more")
                return {}
    else:
        print("Error: Must provide kurral_id, run_id, or set latest=True")
        return {}
    
    if not artifact:
        print(f"Error: Artifact not found")
        return {}
    
    print(f"\n{'='*60}")
    print(f"Replaying Artifact: {artifact.kurral_id}")
    print(f"Original Run ID: {artifact.run_id}")
    print(f"{'='*60}\n")
    
    # Extract current LLM config, prompt, and graph version from agent
    current_llm_config = None
    current_prompt = None
    current_graph_version = None
    agent_module = None  # Initialize agent_module for use in side effect config generation
    
    try:
        # Try to import agent module to get current config
        agent_folder = artifacts_dir.parent
        if agent_folder.name.startswith("level") and "agent" in agent_folder.name:
            try:
                # Import agent module with optional dependency handling
                agent_module = _import_agent_module_with_optional_deps(agent_folder, verbose=verbose)
                
                if agent_module is None:
                    raise ImportError("Could not import agent module")
                
                # Get current LLM
                llm = agent_module.get_llm()
                tools = agent_module.create_tools()
                
                # Extract LLM config (may fail if LLM uses optional deps or has issues)
                try:
                    from kurral.langchain_integration import extract_llm_config_from_langchain
                    current_llm_config = extract_llm_config_from_langchain(llm)
                except (AttributeError, TypeError, ValueError, Exception) as e:
                    # LLM config extraction failed (likely due to missing optional deps or dummy modules)
                    if verbose:
                        print(f"Warning: Could not extract LLM config: {e}")
                    current_llm_config = None
                
                # Extract prompt - use artifact's prompt directly, don't create agent executor
                # Creating agent executor with real tools could trigger tool invocations
                from langchain_core.prompts import PromptTemplate
                from kurral.langchain_integration import compute_graph_version
                from kurral.models.kurral import ResolvedPrompt
                
                # Use artifact's prompt directly instead of extracting from executor
                # This avoids creating an agent executor that might invoke tools
                prompt_template_str = artifact.resolved_prompt.template
                prompt = PromptTemplate.from_template(prompt_template_str)
                
                # Create ResolvedPrompt from artifact (no agent execution needed)
                current_prompt = ResolvedPrompt(
                    template=artifact.resolved_prompt.template,
                    template_hash=artifact.resolved_prompt.template_hash,
                    variables={"input": "dummy_input", "agent_scratchpad": ""},
                    variables_hash="",  # Not needed for comparison
                    final_text=artifact.resolved_prompt.template,
                    final_text_hash=artifact.resolved_prompt.template_hash
                )
                
                # Compute graph version
                current_graph_version = compute_graph_version(tools, current_prompt)
                
            except Exception as e:
                if verbose:
                    print(f"Warning: Could not extract current config: {e}")
                    import traceback
                    traceback.print_exc()
                    print("Will assume no changes (A replay)")
    except Exception as e:
        if verbose:
            print(f"Warning: Could not extract current config: {e}")
            print("Will assume no changes (A replay)")
    
    # Load or generate side effect configuration
    side_effect_config = None
    try:
        agent_folder = artifacts_dir.parent
        config_path = SideEffectConfig.get_config_path(agent_folder)
        
        if not config_path.exists():
            # Auto-generate config if it doesn't exist
            if agent_module is not None:
                print(f"Auto-generating side effect config at: {config_path}")
                side_effect_config = SideEffectConfig.generate_config(artifact, agent_module)
                SideEffectConfig.save(agent_folder, side_effect_config)
            else:
                # Can't generate without agent module, use defaults
                side_effect_config = SideEffectConfig.load(agent_folder)
        else:
            # Load existing config
            side_effect_config = SideEffectConfig.load(agent_folder)
        
        # Check if replay is allowed (done field)
        if not SideEffectConfig.is_done(side_effect_config):
            print(f"\n{'='*60}")
            print("REPLAY BLOCKED: Side Effect Configuration Required")
            print(f"{'='*60}")
            print("The side effect configuration file has been auto-generated or needs review.")
            print("Please manually review and configure the side effects before replay:")
            print()
            print(f"Config file: {config_path}")
            print()
            
            # Show suggestions if available
            suggestions = side_effect_config.get("suggestions", {})
            tools = side_effect_config.get("tools", {})
            
            if tools:
                print("Tool Analysis & Suggestions:")
                print("-" * 60)
                for tool_name in sorted(tools.keys()):
                    suggested_value = tools[tool_name]
                    reason = suggestions.get(tool_name, "No analysis available")
                    status = "SIDE EFFECT" if not suggested_value else "SAFE"
                    value_str = "false" if not suggested_value else "true"
                    print(f"  {tool_name}: {value_str}  [{status}]")
                    print(f"    → {reason}")
                print("-" * 60)
                print()
            
            print("Instructions:")
            print("1. Review each tool above - tools marked as SIDE EFFECT should be set to 'false'")
            print("2. Tools marked as SAFE can remain 'true' (unless you know they have side effects)")
            print("3. Manually edit the YAML file to adjust any values if needed")
            print("4. Set 'done: true' when you have finished configuring")
            print()
            print("Example YAML structure:")
            print("  tools:")
            print("    send_email: false    # Side effect - blocks execution during replay")
            print("    tavily_search: true  # No side effect - allows execution")
            print("  done: true             # Set to true after review")
            print()
            print("Once you have set 'done: true', run the replay again.")
            print(f"{'='*60}\n")
            return {
                "replay_type": "BLOCKED",
                "error": "Replay blocked: done=false in side_effects.yaml - manual configuration required",
            }
    except Exception as e:
        if verbose:
            print(f"Warning: Could not load side effect config: {e}")
        # Default to allowing replay if config can't be loaded
        side_effect_config = {"tools": {}, "done": True}
    
    # Detect replay type and changes
    detector = ReplayDetector()
    detection_result = detector.determine_replay_type(
        artifact=artifact,
        current_llm_config=current_llm_config,
        current_prompt=current_prompt,
        current_graph_version=current_graph_version,
    )
    
    replay_type = detection_result.replay_type
    determinism_score = detection_result.changes.get("determinism_score", 0.0)
    
    print(f"Replay Type: {replay_type}")
    print(f"Determinism Score: {determinism_score:.2f}\n")
    
    # Print changes detected
    display_changes = {k: v for k, v in detection_result.changes.items() 
                      if k not in ["determinism_score", "determinism_threshold"]}
    
    if display_changes:
        print("Changes Detected:")
        for key, change in display_changes.items():
            if isinstance(change, dict):
                print(f"  - {key}:")
                for sub_key, sub_value in change.items():
                    print(f"      {sub_key}: {sub_value}")
            else:
                print(f"  - {key}: {change}")
    else:
        print("No changes detected - using deterministic A replay")
    
    print()
    
    # Execute replay
    executor = ReplayExecutor()
    
    # For A replay, we just return the outputs directly
    if replay_type == "A":
        print("Executing A Replay (Deterministic - returning cached outputs)...\n")
        
        # Check if this is a session artifact with multiple interactions
        if isinstance(artifact.inputs, dict) and "interactions" in artifact.inputs:
            interactions = artifact.outputs.get("interactions", [])
            print(f"Replaying {len(interactions)} interactions:\n")
            
            for i, interaction in enumerate(interactions, 1):
                print(f"{'='*60}")
                print(f"Interaction {i}:")
                print(f"{'='*60}")
                
                # Get input
                input_data = artifact.inputs["interactions"][i-1] if i-1 < len(artifact.inputs["interactions"]) else {}
                user_input = input_data.get("input", "N/A")
                print(f"\nYou: {user_input}")
                
                # Get output
                output_data = interaction
                if isinstance(output_data, dict):
                    if "output" in output_data:
                        print(f"Agent: {output_data['output']}")
                    elif "error" in output_data:
                        print(f"Error: {output_data['error']}")
                    else:
                        print(f"Agent: {output_data}")
                else:
                    print(f"Agent: {output_data}")
                
                print()
        else:
            # Single interaction artifact
            if isinstance(artifact.outputs, dict) and "output" in artifact.outputs:
                print(f"You: {artifact.inputs.get('input', 'N/A')}")
                print(f"Agent: {artifact.outputs['output']}")
            else:
                print("Outputs:", artifact.outputs)
        
        # Calculate ARS (perfect match for A replay)
        ars_result = calculate_ars(
            original_outputs=artifact.outputs,
            replayed_outputs=artifact.outputs,  # Same outputs in A replay
            original_tool_calls=artifact.tool_calls,
            replayed_tool_calls=artifact.tool_calls,  # Same tool calls
            new_tool_calls=[],
            unused_tool_calls=[],
        )
        
        # Create replay result
        result = {
            "replay_type": "A",
            "determinism_score": determinism_score,
            "outputs": artifact.outputs,
            "match": True,
            "cache_hits": len(artifact.tool_calls),
            "cache_misses": 0,
            "duration_ms": 0,
            "tool_calls": artifact.tool_calls,
            "new_tool_calls": [],
            "unused_tool_calls": [],
            "ars": ars_result,
        }
        
        # Print ARS
        print(f"\n{'='*60}")
        print(f"ARS (Agent Regression Score): {ars_result['ars_score']:.4f}")
        print(f"  Output Similarity: {ars_result['output_similarity']:.4f}")
        print(f"  Tool Accuracy: {ars_result['tool_accuracy']:.4f}")
        print(f"{'='*60}\n")
    else:
        # B replay - re-execute agent with cached tool calls
        print("Executing B Replay (Re-executing agent with cached tool calls)...\n")
        
        # Import agent components
        try:
            # Try to import from level1agentK (or detect agent folder)
            agent_folder = artifacts_dir.parent
            if agent_folder.name.startswith("level") and "agent" in agent_folder.name:
                # Import agent module with optional dependency handling
                agent_module = _import_agent_module_with_optional_deps(agent_folder, verbose=verbose)
                
                # Try to import tools module (optional)
                tools_module = None
                try:
                    import importlib
                    tools_module = importlib.import_module(f"{agent_folder.name}.tools")
                except ImportError:
                    tools_module = None  # Tools module is optional
            else:
                agent_module = None
                tools_module = None
            
            if agent_module is None:
                print("Error: Could not import agent module for B replay")
                result = {
                    "replay_type": "B",
                    "error": "Could not import agent module",
                }
            else:
                # Get LLM and tools from agent
                llm = agent_module.get_llm()
                tools = agent_module.create_tools()
                
                # Create tool stubber with artifact tool calls and side effect config
                stubber = ToolStubber(artifact.tool_calls, side_effect_config=side_effect_config)
                
                # Stub the tools
                stubbed_tools = []
                for tool in tools:
                    # Get original function
                    original_func = tool.func
                    tool_name = tool.name
                    
                    # Create stubbed version with side effect config
                    stubbed_func = create_stubbed_tool(original_func, stubber, tool_name, side_effect_config=side_effect_config)
                    
                    # Create new tool with stubbed function
                    from langchain.tools import Tool
                    stubbed_tool = Tool(
                        name=tool.name,
                        func=stubbed_func,
                        description=tool.description
                    )
                    stubbed_tools.append(stubbed_tool)
                
                # Create agent executor with stubbed tools
                from langchain.agents import AgentExecutor, create_react_agent
                from langchain_core.prompts import PromptTemplate
                
                # Extract prompt template from artifact
                prompt_template_str = artifact.resolved_prompt.template
                prompt = PromptTemplate.from_template(prompt_template_str)
                
                agent = create_react_agent(llm, stubbed_tools, prompt)
                agent_executor = AgentExecutor(agent=agent, tools=stubbed_tools, verbose=False)
                
                # Replay each interaction
                interactions = artifact.inputs.get("interactions", [])
                replayed_outputs = []
                all_tool_calls = []
                total_duration_ms = 0
                
                print(f"Re-executing {len(interactions)} interactions with LLM...\n")
                
                for i, interaction_input in enumerate(interactions, 1):
                    print(f"{'='*60}")
                    print(f"Interaction {i}:")
                    print(f"{'='*60}")
                    
                    user_input = interaction_input.get("input", "")
                    print(f"\nYou: {user_input}")
                    
                    # Execute agent with this input
                    start_time = datetime.utcnow()
                    try:
                        result = agent_executor.invoke({"input": user_input})
                        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                        total_duration_ms += duration_ms
                        
                        output = result.get("output", "")
                        print(f"Agent: {output}")
                        
                        replayed_outputs.append({
                            "input": user_input,
                            "output": output
                        })
                    except Exception as e:
                        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                        total_duration_ms += duration_ms
                        error_msg = str(e)
                        print(f"Error: {error_msg}")
                        replayed_outputs.append({
                            "input": user_input,
                            "error": error_msg
                        })
                    
                    print()
                
                # Collect all tool calls (cached + new)
                # Get cached tool calls that were used
                used_cached_tool_calls = []
                for cache_key in stubber.used_keys:
                    if cache_key in stubber.cache:
                        tc = stubber.cache[cache_key]
                        # Mark as stubbed
                        tc.stubbed_in_replay = True
                        used_cached_tool_calls.append(tc)
                
                # Combine cached (used) and new tool calls
                all_tool_calls = used_cached_tool_calls + stubber.new_tool_calls
                
                # Get unused tool calls
                unused_tool_calls = stubber.get_unused_tool_calls()
                
                # Compare outputs
                original_outputs_list = artifact.outputs.get("interactions", [])
                match = len(replayed_outputs) == len(original_outputs_list)
                if match:
                    for orig, replayed in zip(original_outputs_list, replayed_outputs):
                        orig_output = orig.get("output", "") if isinstance(orig, dict) else str(orig)
                        replayed_output = replayed.get("output", "")
                        if orig_output != replayed_output:
                            match = False
                            break
                
                # Calculate ARS
                ars_result = calculate_ars(
                    original_outputs=artifact.outputs,
                    replayed_outputs={"interactions": replayed_outputs},
                    original_tool_calls=artifact.tool_calls,
                    replayed_tool_calls=all_tool_calls,
                    new_tool_calls=stubber.new_tool_calls,
                    unused_tool_calls=unused_tool_calls,
                )
                
                result = {
                    "replay_type": "B",
                    "determinism_score": determinism_score,
                    "outputs": {"interactions": replayed_outputs},
                    "match": match,
                    "cache_hits": len(stubber.used_keys),
                    "cache_misses": len(stubber.new_tool_calls),
                    "duration_ms": total_duration_ms,
                    "tool_calls": all_tool_calls,
                    "new_tool_calls": stubber.new_tool_calls,
                    "unused_tool_calls": unused_tool_calls,
                    "ars": ars_result,
                }
                
                # Print summary
                print(f"\n{'='*60}")
                print(f"B Replay Summary:")
                print(f"  Cache hits: {len(stubber.used_keys)}")
                print(f"  New tool calls: {len(stubber.new_tool_calls)}")
                print(f"  Unused tool calls: {len(unused_tool_calls)}")
                print(f"  Output match: {match}")
                print(f"\nARS (Agent Regression Score): {ars_result['ars_score']:.4f}")
                print(f"  Output Similarity: {ars_result['output_similarity']:.4f}")
                print(f"  Tool Accuracy: {ars_result['tool_accuracy']:.4f}")
                print(f"  Breakdown:")
                print(f"    - Used original tools: {ars_result['breakdown']['used_original_tools']}/{ars_result['breakdown']['total_original_tools']}")
                print(f"    - New tools: {ars_result['breakdown']['new_tools']}")
                print(f"    - Unused tools: {ars_result['breakdown']['unused_tools']}")
                print(f"{'='*60}\n")
                
                if stubber.new_tool_calls:
                    print(f"New Tool Calls (executed in real-time):")
                    for tc in stubber.new_tool_calls:
                        print(f"  - {tc.tool_name}({tc.input}) -> {tc.output}")
                    print()
                
                if unused_tool_calls:
                    print(f"Unused Tool Calls (from original artifact):")
                    for tc in unused_tool_calls:
                        print(f"  - {tc.tool_name}({tc.input})")
                    print()
        
        except Exception as e:
            import traceback
            print(f"Error during B replay: {e}")
            if verbose:
                traceback.print_exc()
            result = {
                "replay_type": "B",
                "error": str(e),
            }
    
    # Save replay artifact
    replay_runs_dir = artifacts_dir.parent / "replay_runs"
    replay_runs_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine agent directory for config loading
    agent_dir = artifacts_dir.parent if artifacts_dir.name == "artifacts" else None
    
    try:
        generator = ArtifactGenerator()
        replay_run_id = f"replay_{artifact.run_id}_{int(datetime.utcnow().timestamp())}"
        
        replay_inputs = {
            "original_kurral_id": str(artifact.kurral_id),
            "original_run_id": artifact.run_id,
            "replay_type": replay_type,
            "determinism_score": determinism_score,
            "changes_detected": display_changes if display_changes else "No changes detected",
        }
        
        # Include ARS in outputs
        replay_outputs = result.get("outputs", {}).copy()
        if "ars" in result:
            replay_outputs["ars"] = result["ars"]
        
        replay_artifact = generator.generate(
            run_id=replay_run_id,
            tenant_id=artifact.tenant_id,
            inputs=replay_inputs,
            outputs=replay_outputs,
            llm_config=artifact.llm_config,
            resolved_prompt=artifact.resolved_prompt,
            tool_calls=result.get("tool_calls", []),
            duration_ms=result.get("duration_ms", 0),
        )
        # Set graph_version after creation
        replay_artifact.graph_version = artifact.graph_version
        
        # Create replay storage backend with replay_runs path prefix
        from kurral.config import get_storage_config
        from kurral.storage import create_storage_backend
        
        replay_config = get_storage_config(agent_dir)
        replay_backend = create_storage_backend(
            replay_config,
            replay_runs_dir,
            agent_dir=agent_dir,
            path_prefix="replay_runs"
        )
        
        # Save replay artifact using backend directly
        replay_result = replay_backend.save(replay_artifact)
        
        if not replay_result.success:
            raise RuntimeError(f"Failed to save replay artifact: {replay_result.error}")
        
        replay_path = replay_result.local_path or replay_runs_dir / f"{replay_artifact.kurral_id}.kurral"
        print(f"\n{'='*60}")
        print(f"Replay artifact saved: {replay_path}")
        print(f"Replay Run ID: {replay_run_id}")
        print(f"{'='*60}\n")
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to save replay artifact: {e}")
    
    return result


if __name__ == "__main__":
    # Setup path before imports if running as module
    import sys
    from pathlib import Path
    
    # If kurral is not in path, try to find project root
    try:
        import kurral
    except ImportError:
        # Try to find project root by looking for kurral directory
        current_dir = Path.cwd()
        # Check current dir and parent dirs
        for check_dir in [current_dir, current_dir.parent, current_dir.parent.parent]:
            kurral_path = check_dir / "kurral"
            if kurral_path.exists() and kurral_path.is_dir():
                project_root = check_dir
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                break
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Replay a Kurral artifact")
    parser.add_argument("kurral_id", nargs="?", help="Kurral ID (UUID) or partial UUID")
    parser.add_argument("--latest", action="store_true", help="Replay the latest artifact")
    parser.add_argument("--run-id", help="Replay by run_id")
    parser.add_argument("--artifacts-dir", type=Path, help="Path to artifacts directory (defaults to ./artifacts)")
    
    args = parser.parse_args()
    
    if args.latest:
        replay_agent_artifact(latest=True, artifacts_dir=args.artifacts_dir)
    elif args.run_id:
        replay_agent_artifact(run_id=args.run_id, artifacts_dir=args.artifacts_dir)
    elif args.kurral_id:
        replay_agent_artifact(kurral_id=args.kurral_id, artifacts_dir=args.artifacts_dir)
    else:
        print("Usage: python -m kurral.agent_replay <kurral_id> [--artifacts-dir <dir>]")
        print("   or: python -m kurral.agent_replay --latest [--artifacts-dir <dir>]")
        print("   or: python -m kurral.agent_replay --run-id <run_id> [--artifacts-dir <dir>]")
        print("\nExample: python -m kurral.agent_replay 810c48c1-fc9c-4ec4-a4f5-7fb7ed86506d")
        print("   or: python -m kurral.agent_replay 810c48c1 --artifacts-dir level1agentK/artifacts")

