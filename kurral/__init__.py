"""
Kurral - Deterministic Testing and Replay for AI Agents
"""

__version__ = "0.2.0"
__author__ = "Kurral Team"
__email__ = "team@kurral.com"

# Core decorators and functions
from kurral.agent_decorator import trace_agent, trace_agent_invoke

# Replay functionality
from kurral.agent_replay import replay_agent_artifact as replay_artifact

# ARS Scoring
from kurral.ars_scorer import calculate_ars

__all__ = [
    "__version__",
    "trace_agent",
    "trace_agent_invoke",
    "replay_artifact",
    "calculate_ars",
]