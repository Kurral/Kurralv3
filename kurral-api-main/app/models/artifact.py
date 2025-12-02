"""
Artifact metadata database model
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ARRAY, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class Artifact(Base):
    """Artifact metadata model - full artifacts stored in R2"""
    
    __tablename__ = "artifacts"
    
    # Identity
    kurral_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Classification
    semantic_buckets = Column(ARRAY(String), default=list, nullable=False)
    environment = Column(String(50), default="production", index=True)
    
    # Determinism
    deterministic = Column(Boolean, nullable=False, index=True)
    replay_level = Column(String(1), nullable=False, index=True)  # A, B, or C
    determinism_score = Column(Float, nullable=False)
    
    # LLM Configuration
    model_name = Column(String(255), index=True)
    model_provider = Column(String(50))
    temperature = Column(Float)
    
    # Execution Metadata
    duration_ms = Column(Integer)
    cost_usd = Column(Float)
    error_message = Column(Text, nullable=True)
    
    # Token Usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cached_tokens = Column(Integer, nullable=True)
    
    # Tool Calls
    tool_call_count = Column(Integer, default=0)
    tool_call_summary = Column(JSONB, default=dict)  # {tool_name: count}

    # Storage
    object_storage_uri = Column(String, nullable=False)  # R2 URI
    artifact_size_bytes = Column(Integer, default=0)

    # Provenance
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(255), nullable=True)

    # Tags and metadata
    tags = Column(JSONB, default=dict, nullable=False)
    extra_metadata = Column(JSONB, default=dict, nullable=False)
    
    # Versioning
    graph_hash = Column(String(64), nullable=True, index=True)
    prompt_hash = Column(String(64), nullable=True, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_tenant_env", "tenant_id", "environment"),
        Index("idx_created_desc", "created_at"),
        Index("idx_deterministic_level", "deterministic", "replay_level"),
        Index("idx_semantic_buckets", "semantic_buckets", postgresql_using="gin"),
        Index("idx_model_provider", "model_name", "model_provider"),
        Index("idx_tags", "tags", postgresql_using="gin"),
    )
    
    def __repr__(self):
        return f"<Artifact {self.kurral_id} ({self.semantic_buckets})>"

