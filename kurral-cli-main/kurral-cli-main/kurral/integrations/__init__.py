"""External integrations for Kurral"""

from kurral.integrations.langsmith import LangSmithIntegration

# LangGraph integration is optional (requires langchain-core)
try:
    from kurral.integrations.langgraph_callback import (
        KurralToolTracker,
        set_tool_calls_context,
        get_tool_calls_context,
        clear_tool_calls_context,
        set_llm_metadata_context,
        get_llm_metadata_context,
        clear_llm_metadata_context,
    )
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False
    # Provide stub functions that raise helpful error
    def _require_langgraph():
        raise ImportError(
            "LangGraph integration requires langchain-core. "
            "Install with: pip install langchain-core"
        )
    
    KurralToolTracker = lambda: _require_langgraph()
    set_tool_calls_context = lambda *a, **k: _require_langgraph()
    get_tool_calls_context = lambda: _require_langgraph()
    clear_tool_calls_context = lambda: _require_langgraph()
    set_llm_metadata_context = lambda *a, **k: _require_langgraph()
    get_llm_metadata_context = lambda: _require_langgraph()
    clear_llm_metadata_context = lambda: _require_langgraph()

__all__ = [
    "LangSmithIntegration",
    "KurralToolTracker",
    "set_tool_calls_context",
    "get_tool_calls_context",
    "clear_tool_calls_context",
    "set_llm_metadata_context",
    "get_llm_metadata_context",
    "clear_llm_metadata_context",
]

