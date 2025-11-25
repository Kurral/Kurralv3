"""
LangGraph callback handler for capturing tool calls in Kurral traces
"""

from typing import Any, Optional
from datetime import datetime
from contextvars import ContextVar

from langchain_core.callbacks import AsyncCallbackHandler
from kurral.models.kurral import ToolCall, EffectType, ToolCallStatus


# Context variables to store tool calls and LLM metadata during execution
_tool_calls_context: ContextVar[list[ToolCall]] = ContextVar("tool_calls", default=[])
_llm_metadata_context: ContextVar[dict[str, Any]] = ContextVar("llm_metadata", default={})


class KurralToolTracker(AsyncCallbackHandler):
    """
    Callback handler that tracks tool calls for Kurral artifacts
    
    Usage:
        tracker = KurralToolTracker()
        config = {"callbacks": [tracker]}
        await graph.astream(input, config=config)
        tool_calls = tracker.get_tool_calls()
    """
    
    def __init__(self):
        super().__init__()
        self.tool_calls: list[ToolCall] = []
        self._current_tool: dict[str, Any] = {}
        self._tool_start_time: Optional[float] = None
    
    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list],
        **kwargs: Any,
    ) -> None:
        """Called when chat model starts - we don't need to track this"""
        pass
    
    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts - we don't need to track this"""
        pass
    
    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing"""
        import time
        
        self._tool_start_time = time.time()
        self._current_tool = {
            "tool_name": serialized.get("name", "unknown"),
            "namespace": serialized.get("namespace"),
            "input_str": input_str,
            "inputs": kwargs.get("inputs", {}),
        }
    
    async def on_tool_end(
        self,
        output: Any,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes successfully"""
        import time
        
        if not self._current_tool:
            return
        
        try:
            latency_ms = None
            if self._tool_start_time:
                latency_ms = int((time.time() - self._tool_start_time) * 1000)
            
            # Determine effect type from tool name
            tool_name = self._current_tool.get("tool_name", "unknown")
            effect_type = self._determine_effect_type(tool_name)
            
            # Parse inputs and outputs
            inputs = self._current_tool.get("inputs", {})
            if not inputs and self._current_tool.get("input_str"):
                try:
                    import json
                    inputs = json.loads(self._current_tool["input_str"])
                except:
                    inputs = {"input": self._current_tool["input_str"]}
            
            # Sanitize output (convert ToolMessage and other objects to serializable format)
            outputs = self._sanitize_output(output)
            
            # Create enhanced tool call
            tool_call = ToolCall(
                tool_name=tool_name,
                namespace=self._current_tool.get("namespace"),
                input=inputs,
                output=outputs,
                effect_type=effect_type,
                latency_ms=latency_ms,
                status=ToolCallStatus.OK,
                error_flag=False,
                # Legacy fields
                inputs=inputs,
                outputs=outputs,
                duration_ms=latency_ms,
            )
            
            self.tool_calls.append(tool_call)
        except Exception as e:
            # Log error but don't crash
            print(f"Error in KurralToolTracker.on_tool_end callback: {e!r}")
        finally:
            self._current_tool = {}
            self._tool_start_time = None
    
    async def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        """Called when a tool execution fails"""
        import time
        
        if not self._current_tool:
            return
        
        latency_ms = None
        if self._tool_start_time:
            latency_ms = int((time.time() - self._tool_start_time) * 1000)
        
        tool_name = self._current_tool.get("tool_name", "unknown")
        effect_type = self._determine_effect_type(tool_name)
        
        inputs = self._current_tool.get("inputs", {})
        error_text = str(error)
        
        # Create tool call with error
        tool_call = ToolCall(
            tool_name=tool_name,
            namespace=self._current_tool.get("namespace"),
            input=inputs,
            output={"error": error_text},
            effect_type=effect_type,
            latency_ms=latency_ms,
            status=ToolCallStatus.ERROR,
            error_flag=True,
            error_text=error_text,
            # Legacy fields
            inputs=inputs,
            outputs={"error": error_text},
            error=error_text,
            duration_ms=latency_ms,
        )
        
        self.tool_calls.append(tool_call)
        self._current_tool = {}
        self._tool_start_time = None
    
    def get_tool_calls(self) -> list[ToolCall]:
        """Get all captured tool calls"""
        return self.tool_calls.copy()
    
    @staticmethod
    def _sanitize_output(output: Any) -> dict[str, Any]:
        """
        Convert output to a JSON-serializable dict.
        Handles LangChain ToolMessage and other objects.
        """
        import json
        
        # Handle None
        if output is None:
            return {"result": None}
        
        # Handle string
        if isinstance(output, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(output)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return {"result": parsed}
            except:
                return {"result": output}
        
        # Handle dict
        if isinstance(output, dict):
            return output
        
        # Handle LangChain ToolMessage
        if hasattr(output, "content"):
            content = output.content
            # Try to parse content if it's a string
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        return parsed
                    else:
                        return {"result": parsed}
                except:
                    return {"result": content}
            return {"result": content}
        
        # Handle list/tuple
        if isinstance(output, (list, tuple)):
            return {"result": list(output)}
        
        # Try JSON serialization test
        try:
            json.dumps(output)
            return {"result": output}
        except (TypeError, ValueError):
            # Not serializable - convert to string
            return {"result": str(output)}
    
    @staticmethod
    def _determine_effect_type(tool_name: str) -> EffectType:
        """Determine effect type from tool name"""
        tool_lower = tool_name.lower()
        
        # Check MCP tools first (more specific patterns)
        if any(x in tool_lower for x in ["mcp", "slack_", "github_", "jira_", "notion_", "slack","jira","github","gitlab","bitbucket","notion"]):
            return EffectType.MCP
        elif any(x in tool_lower for x in ["email", "send_email", "mail","mailer","smtp"]):
            return EffectType.EMAIL
        elif any(x in tool_lower for x in ["file_", "fs_", "write_file", "read_file", "filesystem","file","fs","upload","s3","r2"]):
            return EffectType.FS
        elif any(x in tool_lower for x in ["db_", "database", "sql", "insert", "update", "delete", "db_write", "db_query","postgres","mysql","sqlite","db","database","sql","insert","update","delete","db_write","db_query"]):
            return EffectType.DB_WRITE
        elif any(x in tool_lower for x in ["http", "api", "request", "fetch","http","api","request","fetch"]):
            return EffectType.HTTP
        else:
            return EffectType.OTHER


def set_tool_calls_context(tool_calls: list[ToolCall]) -> None:
    """Set tool calls in context for the current trace"""
    _tool_calls_context.set(tool_calls)


def get_tool_calls_context() -> list[ToolCall]:
    """Get tool calls from context"""
    try:
        return _tool_calls_context.get()
    except LookupError:
        return []


def clear_tool_calls_context() -> None:
    """Clear tool calls context"""
    _tool_calls_context.set([])


def set_llm_metadata_context(metadata: dict[str, Any]) -> None:
    """Set LLM metadata in context for the current trace"""
    _llm_metadata_context.set(metadata)


def get_llm_metadata_context() -> dict[str, Any]:
    """Get LLM metadata from context"""
    try:
        return _llm_metadata_context.get()
    except LookupError:
        return {}


def clear_llm_metadata_context() -> None:
    """Clear LLM metadata context"""
    _llm_metadata_context.set({})

