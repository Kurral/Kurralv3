"""
Artifact schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ArtifactBase(BaseModel):
    """Base artifact schema"""
    run_id: str
    tenant_id: str
    semantic_buckets: List[str] = Field(default_factory=list)
    environment: str = "production"


class ArtifactUpload(BaseModel):
    """Schema for uploading an artifact"""
    artifact_data: Dict[str, Any]  # Full kurral artifact JSON


class ArtifactMetadata(ArtifactBase):
    """Artifact metadata (without full content)"""
    kurral_id: UUID
    deterministic: bool
    replay_level: str
    determinism_score: float
    model_name: Optional[str]
    model_provider: Optional[str]
    temperature: Optional[float]
    duration_ms: Optional[int]
    cost_usd: Optional[float]
    error_message: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: Optional[int]
    tool_call_count: int = 0
    tool_call_summary: Dict[str, int] = Field(default_factory=dict)
    object_storage_uri: str
    artifact_size_bytes: int = 0
    created_at: datetime
    created_by: Optional[str]
    tags: Dict[str, Any] = Field(default_factory=dict)
    graph_hash: Optional[str]
    prompt_hash: Optional[str]

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ArtifactQuery(BaseModel):
    """Schema for querying artifacts"""
    tenant_id: Optional[str] = None
    environment: Optional[str] = None
    semantic_bucket: Optional[str] = None
    deterministic: Optional[bool] = None
    replay_level: Optional[str] = None
    model_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[Dict[str, Any]] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)

    model_config = {"protected_namespaces": ()}


class ArtifactList(BaseModel):
    """Schema for paginated artifact list"""
    items: List[ArtifactMetadata]
    total: int
    page: int
    page_size: int
    pages: int


class ArtifactStats(BaseModel):
    """Schema for artifact statistics"""
    total_artifacts: int
    total_size_gb: float
    by_environment: Dict[str, int]
    by_replay_level: Dict[str, int]
    by_semantic_bucket: Dict[str, int]
    by_model: Dict[str, int]
    total_cost_usd: float
    total_tokens: int
    avg_duration_ms: float
    error_rate: float
    deterministic_rate: float


class UploadResponse(BaseModel):
    """Schema for artifact upload response"""
    kurral_id: UUID
    object_storage_uri: str
    message: str = "Artifact uploaded successfully"

