"""
LangChain integration helpers for Kurral
Provides utilities for capturing tool calls, extracting LLM configs, and computing graph versions
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Optional, List, Dict
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from kurral.models.kurral import (
    ModelConfig,
    LLMParameters,
    ResolvedPrompt,
    ToolCall,
    ToolCallStatus,
    GraphVersion,
)


class ToolCallCaptureHandler(BaseCallbackHandler):
    """Callback handler to capture tool calls from LangChain AgentExecutor"""
    
    def __init__(self):
        super().__init__()
        self.tool_calls: List[ToolCall] = []
        self.current_tool_start: Optional[datetime] = None
        self.current_tool_name: Optional[str] = None
        self.current_tool_input: Optional[dict] = None
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Called when a tool starts executing"""
        tool_name = serialized.get("name", "unknown")
        self.current_tool_start = datetime.utcnow()
        self.current_tool_name = tool_name
        
        # Parse input_str to dict if possible
        try:
            # Try to parse as JSON
            if input_str.strip().startswith("{"):
                self.current_tool_input = json.loads(input_str)
            else:
                # For simple string inputs, wrap in dict
                self.current_tool_input = {"input": input_str}
        except:
            self.current_tool_input = {"input": input_str}
    
    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Called when a tool finishes executing"""
        if not self.current_tool_start or not self.current_tool_name:
            return
        
        end_time = datetime.utcnow()
        latency_ms = int((end_time - self.current_tool_start).total_seconds() * 1000)
        
        # Parse output to dict if possible
        try:
            if output.strip().startswith("{"):
                tool_output = json.loads(output)
            else:
                tool_output = {"output": output}
        except:
            tool_output = {"output": output}
        
        # Create ToolCall
        tool_call = ToolCall(
            tool_name=self.current_tool_name,
            input=self.current_tool_input or {},
            output=tool_output,
            start_time=self.current_tool_start,
            end_time=end_time,
            latency_ms=latency_ms,
            status=ToolCallStatus.OK,
        )
        
        # Generate cache key
        tool_call.cache_key = ToolCall.generate_cache_key(
            self.current_tool_name,
            self.current_tool_input or {}
        )
        
        self.tool_calls.append(tool_call)
        
        # Reset current tool state
        self.current_tool_start = None
        self.current_tool_name = None
        self.current_tool_input = None
    
    def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Called when a tool execution fails"""
        if not self.current_tool_start or not self.current_tool_name:
            return
        
        end_time = datetime.utcnow()
        latency_ms = int((end_time - self.current_tool_start).total_seconds() * 1000)
        
        tool_call = ToolCall(
            tool_name=self.current_tool_name,
            input=self.current_tool_input or {},
            output={},
            start_time=self.current_tool_start,
            end_time=end_time,
            latency_ms=latency_ms,
            status=ToolCallStatus.ERROR,
            error_flag=True,
            error_text=str(error),
        )
        
        tool_call.cache_key = ToolCall.generate_cache_key(
            self.current_tool_name,
            self.current_tool_input or {}
        )
        
        self.tool_calls.append(tool_call)
        
        # Reset current tool state
        self.current_tool_start = None
        self.current_tool_name = None
        self.current_tool_input = None


def extract_llm_config_from_langchain(llm: Any) -> ModelConfig:
    """
    Extract ModelConfig from a LangChain LLM object
    
    Args:
        llm: LangChain LLM object (ChatOpenAI, ChatGoogleGenerativeAI, etc.)
        
    Returns:
        ModelConfig with extracted information
    """
    # Get model name
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
    
    # Get temperature
    temperature = getattr(llm, "temperature", 0.0)
    
    # Determine provider from class name
    class_name = llm.__class__.__name__.lower()
    provider = "unknown"
    
    if "openai" in class_name or "chatopenai" in class_name:
        provider = "openai"
        # Check if it's Groq (has base_url)
        if hasattr(llm, "base_url") and "groq" in str(getattr(llm, "base_url", "")).lower():
            provider = "groq"
    elif "google" in class_name or "gemini" in class_name or "generativeai" in class_name:
        provider = "google"
    elif "anthropic" in class_name or "claude" in class_name:
        provider = "anthropic"
    elif "ollama" in class_name:
        provider = "ollama"
    
    # Extract additional parameters
    params = LLMParameters(
        temperature=temperature,
        top_p=getattr(llm, "top_p", None),
        top_k=getattr(llm, "top_k", None),
        max_tokens=getattr(llm, "max_tokens", None),
        frequency_penalty=getattr(llm, "frequency_penalty", None),
        presence_penalty=getattr(llm, "presence_penalty", None),
        seed=getattr(llm, "seed", None),
    )
    
    return ModelConfig(
        model_name=str(model_name),
        provider=provider,
        parameters=params,
    )


def extract_resolved_prompt(agent_executor: AgentExecutor, user_input: str) -> ResolvedPrompt:
    """
    Extract resolved prompt from AgentExecutor
    
    Args:
        agent_executor: The AgentExecutor instance
        user_input: The user input that was provided
        
    Returns:
        ResolvedPrompt with template and variables
    """
    # Try to get prompt from agent
    prompt_template = ""
    variables = {"input": user_input}
    prompt_obj = None
    
    if hasattr(agent_executor, "agent"):
        agent = agent_executor.agent
        
        # For ReAct agents created with create_react_agent, the prompt is in agent.middle[0]
        # The agent itself is a RunnableSequence
        try:
            # Method 1: Check if agent.middle[0] is a PromptTemplate
            if hasattr(agent, "middle") and len(agent.middle) > 0:
                first_middle = agent.middle[0]
                if isinstance(first_middle, PromptTemplate):
                    prompt_obj = first_middle
                    prompt_template = prompt_obj.template
                    # Get input variables
                    if hasattr(prompt_obj, "input_variables"):
                        for var in prompt_obj.input_variables:
                            if var not in variables:
                                variables[var] = ""
        except:
            pass
        
        # Method 2: Try to extract from the agent's runnable (for other agent types)
        if not prompt_template and hasattr(agent, "runnable"):
            try:
                if hasattr(agent.runnable, "prompt"):
                    prompt = agent.runnable.prompt
                    if isinstance(prompt, PromptTemplate):
                        prompt_obj = prompt
                        prompt_template = prompt.template
                        # Try to get variables
                        if hasattr(prompt, "input_variables"):
                            for var in prompt.input_variables:
                                if var not in variables:
                                    variables[var] = ""
            except:
                pass
        
        # Method 3: Try to find prompt recursively in the runnable structure
        if not prompt_template and hasattr(agent, "runnable"):
            def find_prompt_recursive(obj, depth=0, max_depth=5):
                if depth > max_depth:
                    return None
                if obj is None:
                    return None
                
                # Check if this object is a PromptTemplate
                if isinstance(obj, PromptTemplate):
                    return obj
                
                # Check common attributes
                for attr in ['first', 'middle', 'last', 'runnables', 'steps', 'bound', 'prompt']:
                    if hasattr(obj, attr):
                        value = getattr(obj, attr)
                        if value and not isinstance(value, (str, int, float, bool)):
                            result = find_prompt_recursive(value, depth+1, max_depth)
                            if result:
                                return result
                
                # Check if it's iterable
                if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                    try:
                        for item in obj:
                            result = find_prompt_recursive(item, depth+1, max_depth)
                            if result:
                                return result
                    except:
                        pass
                
                return None
            
            prompt_obj = find_prompt_recursive(agent.runnable)
            if prompt_obj:
                prompt_template = prompt_obj.template
                if hasattr(prompt_obj, "input_variables"):
                    for var in prompt_obj.input_variables:
                        if var not in variables:
                            variables[var] = ""
    
    # If we couldn't extract, use a default
    if not prompt_template:
        prompt_template = "ReAct agent prompt (template not extractable)"
    
    # Build final text - only format if we have the template and can safely format it
    final_text = prompt_template
    if prompt_template and variables:
        try:
            # Try to format, but handle missing variables gracefully
            final_text = prompt_template.format(**variables)
        except (KeyError, ValueError):
            # If formatting fails (missing variables), just use the template
            # This can happen if the template has variables we don't have values for
            final_text = prompt_template
    
    # Create resolved prompt
    resolved = ResolvedPrompt(
        template=prompt_template,
        variables=variables,
        final_text=final_text,
    )
    
    # Compute hashes
    resolved = resolved.compute_hashes()
    
    return resolved


def compute_tool_schemas_hash(tools: List[BaseTool]) -> str:
    """
    Compute hash of tool schemas (name + description + input schema)
    
    Args:
        tools: List of LangChain tools
        
    Returns:
        SHA256 hash of combined tool schemas
    """
    schemas = []
    
    for tool in tools:
        tool_name = getattr(tool, "name", "unknown")
        tool_desc = getattr(tool, "description", "")
        
        # Get input schema
        input_schema = {}
        if hasattr(tool, "args_schema"):
            try:
                if tool.args_schema:
                    input_schema = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, "model_json_schema") else {}
            except:
                pass
        
        # Create schema representation
        schema_repr = {
            "name": tool_name,
            "description": tool_desc,
            "input_schema": input_schema,
        }
        schemas.append(schema_repr)
    
    # Sort for deterministic hashing
    schemas_str = json.dumps(schemas, sort_keys=True)
    return hashlib.sha256(schemas_str.encode()).hexdigest()


def compute_graph_version(tools: List[BaseTool], prompt: ResolvedPrompt) -> GraphVersion:
    """
    Compute graph version from tool schemas and prompt template
    
    Args:
        tools: List of LangChain tools
        prompt: ResolvedPrompt with template
        
    Returns:
        GraphVersion with computed hashes
    """
    # Compute tool schemas hash
    tool_schemas_hash = compute_tool_schemas_hash(tools)
    
    # Get prompt template hash
    prompt_hash = prompt.template_hash or prompt.final_text_hash or ""
    
    # Combine for graph hash
    combined = f"{tool_schemas_hash}:{prompt_hash}"
    graph_hash = hashlib.sha256(combined.encode()).hexdigest()
    
    return GraphVersion(
        graph_hash=graph_hash,
        tool_schemas_hash=tool_schemas_hash,
    )


def capture_tool_calls_from_executor(
    agent_executor: AgentExecutor,
    user_input: str,
) -> List[ToolCall]:
    """
    Capture tool calls from AgentExecutor execution using callbacks
    
    Note: This function doesn't execute the agent, it just sets up the callback.
    The actual execution should be done separately, and this handler will capture
    the tool calls during that execution.
    
    Args:
        agent_executor: The AgentExecutor instance
        user_input: The user input (for context)
        
    Returns:
        ToolCallCaptureHandler instance that will capture tool calls
    """
    handler = ToolCallCaptureHandler()
    return handler

