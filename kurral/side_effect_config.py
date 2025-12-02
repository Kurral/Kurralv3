"""
Side Effect Configuration Manager
Manages YAML-based side effect configuration for agents
"""
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Set
from kurral.models.kurral import KurralArtifact


class SideEffectConfig:
    """Manages side effect configuration for agents"""
    
    @staticmethod
    def get_config_path(agent_folder: Path) -> Path:
        """Get the path to side_effects.yaml for an agent folder"""
        side_effect_dir = agent_folder / "side_effect"
        return side_effect_dir / "side_effects.yaml"
    
    @staticmethod
    def load(agent_folder: Path) -> Dict[str, Any]:
        """
        Load side effect configuration from YAML file.
        Returns default config if file doesn't exist.
        
        Args:
            agent_folder: Path to the agent folder
            
        Returns:
            Configuration dictionary with 'tools' and 'done' keys
        """
        config_path = SideEffectConfig.get_config_path(agent_folder)
        
        if not config_path.exists():
            # Return default config (all true, done=false - requires manual review)
            return {
                "tools": {},
                "done": False
            }
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # Ensure required keys exist with defaults
            if "tools" not in config:
                config["tools"] = {}
            if "done" not in config:
                config["done"] = False  # Default to False for safety
            
            # Default missing tool entries to True
            # (This ensures backward compatibility)
            return config
        except Exception as e:
            print(f"Warning: Could not load side effect config from {config_path}: {e}")
            return {
                "tools": {},
                "done": False  # Default to False for safety
            }
    
    @staticmethod
    def save(agent_folder: Path, config: Dict[str, Any]) -> None:
        """
        Save side effect configuration to YAML file.
        Removes 'suggestions' field before saving (only used for display).
        
        Args:
            agent_folder: Path to the agent folder
            config: Configuration dictionary
        """
        config_path = SideEffectConfig.get_config_path(agent_folder)
        side_effect_dir = config_path.parent
        
        # Create side_effect directory if it doesn't exist
        side_effect_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure config has required structure
        if "tools" not in config:
            config["tools"] = {}
        if "done" not in config:
            config["done"] = False
        
        # Create a copy for saving (remove suggestions - they're only for display)
        config_to_save = config.copy()
        if "suggestions" in config_to_save:
            del config_to_save["suggestions"]
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, sort_keys=False)
            print(f"Side effect config saved to: {config_path}")
        except Exception as e:
            print(f"Error: Could not save side effect config to {config_path}: {e}")
            raise
    
    @staticmethod
    def _has_side_effect_keywords(text: str) -> bool:
        """
        Check if text contains side effect keywords (case-insensitive).
        
        Args:
            text: Text to check (tool name, description, or docstring)
            
        Returns:
            True if keywords found, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        keywords = ["update", "send", "write"]
        
        for keyword in keywords:
            if keyword in text_lower:
                return True
        
        return False
    
    @staticmethod
    def _get_tool_docstring(tool: Any) -> str:
        """
        Extract docstring from tool function.
        
        Args:
            tool: Tool object (LangChain Tool or function)
            
        Returns:
            Docstring as string, empty if not found
        """
        try:
            # Try to get function from LangChain Tool
            if hasattr(tool, 'func'):
                func = tool.func
                if hasattr(func, '__doc__') and func.__doc__:
                    return func.__doc__
        except Exception:
            pass
        
        return ""
    
    @staticmethod
    def generate_config(artifact: KurralArtifact, agent_module: Any) -> Dict[str, Any]:
        """
        Auto-generate side effect configuration by discovering tools and analyzing them.
        Suggests side effects based on tool names and descriptions containing keywords:
        "update", "send", "write" (case-insensitive).
        
        Args:
            artifact: The Kurral artifact containing tool calls
            agent_module: The agent module (should have create_tools() function)
            
        Returns:
            Configuration dictionary with discovered tools and intelligent suggestions
        """
        tool_info: Dict[str, Dict[str, Any]] = {}  # tool_name -> {suggested_value, reason}
        
        # Extract tool names from artifact's tool calls
        if artifact.tool_calls:
            for tool_call in artifact.tool_calls:
                if tool_call.tool_name:
                    tool_name = tool_call.tool_name
                    if tool_name not in tool_info:
                        # Analyze tool name for keywords
                        if SideEffectConfig._has_side_effect_keywords(tool_name):
                            tool_info[tool_name] = {
                                "suggested_value": False,
                                "reason": f"Tool name contains side effect keywords"
                            }
                        else:
                            tool_info[tool_name] = {
                                "suggested_value": True,
                                "reason": "No side effect keywords found in tool name"
                            }
        
        # Extract tools from agent module's create_tools() for better analysis
        try:
            if hasattr(agent_module, 'create_tools'):
                tools = agent_module.create_tools()
                if tools:
                    for tool in tools:
                        tool_name = None
                        description = ""
                        docstring = ""
                        
                        # Handle LangChain Tool objects
                        if hasattr(tool, 'name'):
                            tool_name = tool.name
                            if hasattr(tool, 'description'):
                                description = str(tool.description) or ""
                            docstring = SideEffectConfig._get_tool_docstring(tool)
                        # Handle dict-like tools
                        elif isinstance(tool, dict) and 'name' in tool:
                            tool_name = tool['name']
                            description = str(tool.get('description', ''))
                        # Handle string tools
                        elif isinstance(tool, str):
                            tool_name = tool
                        
                        if tool_name:
                            # Analyze for side effect keywords
                            combined_text = f"{tool_name} {description} {docstring}".strip()
                            
                            if SideEffectConfig._has_side_effect_keywords(combined_text):
                                tool_info[tool_name] = {
                                    "suggested_value": False,
                                    "reason": f"Contains side effect keywords in name/description/docstring"
                                }
                            else:
                                if tool_name not in tool_info:
                                    tool_info[tool_name] = {
                                        "suggested_value": True,
                                        "reason": "No side effect keywords found"
                                    }
        except Exception as e:
            print(f"Warning: Could not extract tools from agent module: {e}")
        
        # Create config with suggested values
        tools_config = {}
        suggestions = {}
        
        for tool_name in sorted(tool_info.keys()):
            info = tool_info[tool_name]
            tools_config[tool_name] = info["suggested_value"]
            suggestions[tool_name] = info["reason"]
        
        return {
            "tools": tools_config,
            "suggestions": suggestions,  # Store suggestions for display
            "done": False  # Default to False - user must manually set to True after reviewing
        }
    
    @staticmethod
    def is_side_effect(config: Dict[str, Any], tool_name: str) -> bool:
        """
        Check if a tool is marked as a side effect.
        Missing tools default to False (not side effect).
        
        Args:
            config: Configuration dictionary
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is a side effect (value is False), False otherwise
        """
        if not config or "tools" not in config:
            return False
        
        tools = config.get("tools", {})
        # If tool is not in config, default to False (not side effect)
        if tool_name not in tools:
            return False
        
        # Side effect is marked as False (inverted logic: False = side effect)
        return tools[tool_name] is False
    
    @staticmethod
    def is_done(config: Dict[str, Any]) -> bool:
        """
        Check if replay is allowed (done field is True).
        Defaults to True if missing.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if replay is allowed, False otherwise
        """
        if not config:
            return True
        
        return config.get("done", True)

