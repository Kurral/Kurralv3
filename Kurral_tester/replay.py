"""
Generic replay functionality for Kurral artifacts
Can be used from any agent directory
"""

import asyncio
import os
from pathlib import Path
from typing import Optional, Any
from uuid import UUID

from Kurral_tester.models.kurral import KurralArtifact, ModelConfig, LLMParameters
from Kurral_tester.artifact_manager import ArtifactManager
from Kurral_tester.replay_detector import ReplayDetector
from Kurral_tester.replay_executor import ReplayExecutor


def _auto_detect_current_model(storage_path: Optional[Path] = None) -> Optional[tuple[str, float, str]]:
    """
    Automatically detect current model configuration from agent's setup
    
    Returns:
        Tuple of (model_name, temperature, provider) or None if not found
    """
    # Try to detect from current working directory or storage path
    base_dir = storage_path.parent if storage_path else Path.cwd()
    
    # If we're in an artifacts folder, go up one level
    if base_dir.name == "artifacts":
        base_dir = base_dir.parent
    
    # Try to load from config.py
    try:
        config_path = base_dir / "config.py"
        if config_path.exists():
            # Try to import and load config
            import sys
            import importlib.util
            
            # Add base_dir to path temporarily
            if str(base_dir) not in sys.path:
                sys.path.insert(0, str(base_dir))
            
            try:
                # Try importing config module
                spec = importlib.util.spec_from_file_location("agent_config", config_path)
                if spec and spec.loader:
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    
                    if hasattr(config_module, "load_config"):
                        cfg = config_module.load_config()
                        models_cfg = cfg.get("models", {})
                        model_name = models_cfg.get("llm", None)
                        temperature = models_cfg.get("temperature", 0.0)
                        
                        if model_name:
                            # Determine provider from model name
                            provider = "unknown"
                            model_lower = str(model_name).lower()
                            if "gpt" in model_lower or "o1" in model_lower or "openai" in model_lower:
                                provider = "openai"
                            elif "claude" in model_lower or "anthropic" in model_lower:
                                provider = "anthropic"
                            elif "llama" in model_lower or "ollama" in model_lower:
                                provider = "ollama"
                            elif "gemini" in model_lower or "google" in model_lower:
                                provider = "google"
                            
                            return (model_name, temperature, provider)
            except Exception:
                pass
    except Exception:
        pass
    
    # Try to load from llm.py
    try:
        llm_path = base_dir / "llm.py"
        if llm_path.exists():
            import sys
            import importlib.util
            
            if str(base_dir) not in sys.path:
                sys.path.insert(0, str(base_dir))
            
            try:
                spec = importlib.util.spec_from_file_location("agent_llm", llm_path)
                if spec and spec.loader:
                    llm_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(llm_module)
                    
                    if hasattr(llm_module, "load_llms"):
                        # Try to get LLM object and extract model
                        llm, _ = llm_module.load_llms()
                        if hasattr(llm, "model"):
                            model_name = llm.model
                            temperature = getattr(llm, "temperature", 0.0)
                            
                            # Determine provider
                            provider = "unknown"
                            class_name = llm.__class__.__name__.lower()
                            if "ollama" in class_name or "llama" in class_name:
                                provider = "ollama"
                            elif "openai" in class_name:
                                provider = "openai"
                            elif "anthropic" in class_name or "claude" in class_name:
                                provider = "anthropic"
                            elif "google" in class_name or "gemini" in class_name:
                                provider = "google"
                            
                            return (model_name, temperature, provider)
            except Exception:
                pass
    except Exception:
        pass
    
    return None


def _create_langchain_llm(
    provider: str,
    model_name: str,
    temperature: float = 0.0,
    verbose: bool = False,
) -> Any:
    """
    Create a LangChain LLM client for the specified provider
    
    Args:
        provider: Provider name ("openai", "ollama", "anthropic", "google")
        model_name: Model name/identifier
        temperature: Temperature parameter
        verbose: Enable verbose output
        
    Returns:
        LangChain LLM object
    """
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            if verbose:
                print(f"Creating Ollama LLM: {model_name}")
            return ChatOllama(model=model_name, temperature=temperature)
        except ImportError:
            raise ImportError("langchain_ollama package not installed (required for Ollama replay)")
    
    elif provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set (required for OpenAI replay)")
            if verbose:
                print(f"Creating OpenAI LLM: {model_name}")
            return ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
        except ImportError:
            raise ImportError("langchain_openai package not installed (required for OpenAI replay)")
    
    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set (required for Anthropic replay)")
            if verbose:
                print(f"Creating Anthropic LLM: {model_name}")
            return ChatAnthropic(model=model_name, temperature=temperature, api_key=api_key)
        except ImportError:
            raise ImportError("langchain_anthropic package not installed (required for Anthropic replay)")
    
    elif provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set (required for Google replay)")
            if verbose:
                print(f"Creating Google LLM: {model_name}")
            return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=api_key)
        except ImportError:
            raise ImportError("langchain_google_genai package not installed (required for Google replay)")
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def replay_artifact(
    artifact_path: Optional[str] = None,
    kurral_id: Optional[str] = None,
    run_id: Optional[str] = None,
    latest: bool = False,
    storage_path: Optional[str] = None,
    llm_client: Optional[str] = None,
    current_model: Optional[str] = None,
    current_temperature: Optional[float] = None,
    verbose: bool = False,
) -> dict:
    """
    Replay an artifact programmatically
    
    Args:
        artifact_path: Path to artifact file (relative to storage_path or absolute)
        kurral_id: Kurral ID (UUID string)
        run_id: Run ID to replay
        latest: If True, replay the latest artifact
        storage_path: Path to artifacts directory (defaults to ./artifacts in current dir)
        llm_client: LLM client type for B replay ("openai", "anthropic", etc.)
        current_model: Current model name for change detection
        current_temperature: Current temperature for change detection
        verbose: Enable verbose output
        
    Returns:
        dict with replay results
        
    Example:
        result = replay_artifact(artifact_path="artifacts/xxx.kurral")
        print(f"Replay type: {result['replay_type']}")
    """
    # Determine storage path - default to ./artifacts in current directory
    if storage_path:
        artifacts_dir = Path(storage_path)
    else:
        artifacts_dir = Path.cwd() / "artifacts"
    
    artifact_manager = ArtifactManager(storage_path=artifacts_dir)
    
    # Load artifact
    artifact_obj = None
    
    if latest:
        artifact_obj = artifact_manager.load_latest()
        if not artifact_obj:
            raise ValueError("No artifacts found")
    elif run_id:
        artifact_obj = artifact_manager.load_by_run_id(run_id)
        if not artifact_obj:
            raise ValueError(f"Artifact with run_id '{run_id}' not found")
    elif artifact_path:
        artifact_path_obj = Path(artifact_path)
        if not artifact_path_obj.is_absolute():
            # Try relative to current directory first
            if (Path.cwd() / artifact_path_obj).exists():
                artifact_path_obj = Path.cwd() / artifact_path_obj
            # Then try relative to artifacts directory
            elif (artifacts_dir / artifact_path_obj).exists():
                artifact_path_obj = artifacts_dir / artifact_path_obj
            else:
                raise FileNotFoundError(f"Artifact file not found: {artifact_path}")
        artifact_obj = KurralArtifact.load(artifact_path_obj)
    elif kurral_id:
        artifact_obj = artifact_manager.load(UUID(kurral_id))
        if not artifact_obj:
            raise ValueError(f"Artifact with kurral_id '{kurral_id}' not found")
    else:
        raise ValueError("Must provide artifact_path, kurral_id, run_id, or set latest=True")
    
    # Build current execution context
    # Auto-detect current model if not explicitly provided
    auto_detected = None
    if not current_model:
        auto_detected = _auto_detect_current_model(artifacts_dir)
        if auto_detected:
            auto_model, auto_temp, auto_provider = auto_detected
            if not current_model:
                current_model = auto_model
            if current_temperature is None:
                current_temperature = auto_temp
    
    current_llm_config = None
    # Always create current_llm_config if we have a model (explicit or auto-detected)
    # This allows comparison even if model is the same (for proper A replay detection)
    if current_model or current_temperature is not None or auto_detected:
        params = artifact_obj.llm_config.parameters or LLMParameters()
        llm_params = LLMParameters(
            temperature=current_temperature if current_temperature is not None else (params.temperature if params else None),
            seed=params.seed if params else None,
            top_p=params.top_p if params else None,
            top_k=params.top_k if params else None,
            max_tokens=params.max_tokens if params else None,
            frequency_penalty=params.frequency_penalty if params else None,
            presence_penalty=params.presence_penalty if params else None,
        )
        
        # Use auto-detected provider if available, otherwise use artifact's provider
        provider = auto_detected[2] if auto_detected and len(auto_detected) > 2 else artifact_obj.llm_config.provider
        
        current_llm_config = ModelConfig(
            model_name=current_model or artifact_obj.llm_config.model_name,
            model_version=artifact_obj.llm_config.model_version,
            provider=provider,
            parameters=llm_params,
        )
    
    # Determine replay type
    detector = ReplayDetector()
    detection_result = detector.determine_replay_type(
        artifact=artifact_obj,
        current_llm_config=current_llm_config,
    )
    
    if verbose:
        determinism_score = detection_result.changes.get("determinism_score", 0.0)
        threshold = detection_result.changes.get("determinism_threshold", 0.8)
        print(f"Replay Type: {detection_result.replay_type}")
        print(f"Determinism Score: {determinism_score:.2f} (threshold: {threshold:.2f})")
        if detection_result.replay_type == "B":
            print(f"Note: B replay will re-execute LLM with cached tool calls")
    
    # Get LLM client if needed for B replay
    llm_client_obj = None
    if detection_result.replay_type == "B":
        # Determine provider from artifact or current model
        provider = artifact_obj.llm_config.provider if artifact_obj.llm_config else "unknown"
        if current_llm_config and current_llm_config.provider != "unknown":
            provider = current_llm_config.provider
        
        # Auto-detect provider if not specified
        if provider == "unknown" and current_model:
            model_lower = current_model.lower()
            if "gpt" in model_lower or "o1" in model_lower or "openai" in model_lower:
                provider = "openai"
            elif "claude" in model_lower or "anthropic" in model_lower:
                provider = "anthropic"
            elif "llama" in model_lower or "ollama" in model_lower:
                provider = "ollama"
            elif "gemini" in model_lower or "google" in model_lower:
                provider = "google"
        
        # Auto-detect from environment if provider still unknown
        if provider == "unknown" and not llm_client:
            if os.getenv("OPENAI_API_KEY"):
                provider = "openai"
            elif os.getenv("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST"):
                provider = "ollama"
        
        # Use provided llm_client if specified, otherwise use provider
        if llm_client:
            provider = llm_client
        
        # Create LangChain LLM client (works for all providers)
        try:
            if provider == "openai" or provider == "ollama" or provider == "anthropic" or provider == "google":
                # Use LangChain for all providers
                llm_client_obj = _create_langchain_llm(
                    provider=provider,
                    model_name=current_model or (artifact_obj.llm_config.model_name if artifact_obj.llm_config else "unknown"),
                    temperature=current_temperature if current_temperature is not None else (artifact_obj.llm_config.parameters.temperature if artifact_obj.llm_config and artifact_obj.llm_config.parameters else 0.0),
                    verbose=verbose,
                )
            else:
                # Fallback: try to create as LangChain model
                llm_client_obj = _create_langchain_llm(
                    provider=provider,
                    model_name=current_model or "unknown",
                    temperature=current_temperature if current_temperature is not None else 0.0,
                    verbose=verbose,
                )
        except Exception as e:
            if verbose:
                print(f"Warning: Failed to create LLM client for provider '{provider}': {e}")
                print(f"Falling back to A replay")
            detection_result.replay_type = "A"
            llm_client_obj = None
    
    # Execute replay
    executor = ReplayExecutor()
    
    # Execute the replay
    # Suppress the harmless Windows asyncio cleanup error by redirecting stderr to null
    # The error occurs during garbage collection after asyncio.run() completes
    import sys
    import os
    import threading
    import time
    
    # Save original stderr file descriptor
    original_stderr_fd = sys.stderr.fileno()
    saved_stderr_fd = os.dup(original_stderr_fd)
    
    # Open null device
    null_fd = os.open(os.devnull, os.O_WRONLY)
    
    # Redirect stderr to null
    os.dup2(null_fd, original_stderr_fd)
    
    def restore_stderr_delayed():
        """Restore stderr after a delay to catch cleanup errors"""
        time.sleep(0.5)  # Wait for garbage collection
        try:
            os.dup2(saved_stderr_fd, original_stderr_fd)
            os.close(saved_stderr_fd)
            os.close(null_fd)
        except Exception:
            pass
    
    try:
        result = asyncio.run(
            executor.execute_replay(
                artifact=artifact_obj,
                detection_result=detection_result,
                llm_client=llm_client_obj,
            )
        )
        
        # Start a background thread to restore stderr after delay
        restore_thread = threading.Thread(target=restore_stderr_delayed, daemon=True)
        restore_thread.start()
        
    except Exception:
        # Restore immediately on error
        os.dup2(saved_stderr_fd, original_stderr_fd)
        os.close(saved_stderr_fd)
        os.close(null_fd)
        raise
    
    # Return results as dict
    return {
        "replay_type": detection_result.replay_type,
        "determinism_score": detection_result.changes.get("determinism_score", 0.0),
        "outputs": result.outputs,
        "match": result.match,
        "cache_hits": result.cache_hits,
        "cache_misses": result.cache_misses,
        "duration_ms": result.duration_ms,
        "tool_calls": result.tool_calls,
        "new_tool_calls": result.new_tool_calls,
        "unused_tool_calls": result.unused_tool_calls,
        "validation": {
            "hash_match": result.validation.hash_match if result.validation else None,
            "structural_match": result.validation.structural_match if result.validation else None,
        } if result.validation else None,
    }
