"""
Pydantic models for LangSmith API integration
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LangSmithRun(BaseModel):
    """LangSmith run/trace data structure"""

    id: str = Field(..., description="LangSmith run ID")
    name: str = Field(..., description="Run name")
    run_type: str = Field(..., description="Type: llm, chain, tool, etc.")
    start_time: datetime
    end_time: Optional[datetime] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    serialized: Optional[dict[str, Any]] = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    dotted_order: Optional[str] = None
    parent_run_id: Optional[str] = None
    child_runs: list["LangSmithRun"] = Field(default_factory=list)

    # LLM-specific fields
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate duration in milliseconds"""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None


class LangSmithTrace(BaseModel):
    """Complete trace from LangSmith"""

    trace_id: str
    project_id: str
    project_name: str
    root_run: LangSmithRun
    all_runs: list[LangSmithRun] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def llm_runs(self) -> list[LangSmithRun]:
        """Get all LLM runs from trace"""
        return [run for run in self.all_runs if run.run_type == "llm"]

    @property
    def tool_runs(self) -> list[LangSmithRun]:
        """Get all tool runs from trace"""
        return [run for run in self.all_runs if run.run_type == "tool"]


class LangSmithProject(BaseModel):
    """LangSmith project metadata"""

    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tenant_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

