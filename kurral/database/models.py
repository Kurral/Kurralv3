"""
SQLAlchemy models for artifact metadata
"""

import warnings
from datetime import datetime
from typing import Optional
import uuid

try:
    from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ARRAY, Index, Text
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Dummy classes for when SQLAlchemy is not available
    Column = String = Boolean = DateTime = Integer = Float = ARRAY = Index = Text = None
    PG_UUID = JSONB = None

# Create Base here to avoid circular imports
if SQLALCHEMY_AVAILABLE:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
else:
    Base = None


if SQLALCHEMY_AVAILABLE and Base:
    class ArtifactMetadata(Base):
        """
        Artifact metadata model for PostgreSQL
        
        Stores metadata about artifacts while full artifacts are stored in R2 or local storage.
        """
        
        __tablename__ = "kurral_artifacts"
        
        # Identity
        kurral_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        run_id = Column(String(255), nullable=False, index=True)
        tenant_id = Column(String(255), nullable=False, index=True)
        
        # Classification
        semantic_buckets = Column(ARRAY(String), default=list, nullable=False)
        environment = Column(String(50), default="production", index=True)
        
        # Determinism
        deterministic = Column(Boolean, nullable=False, default=False, index=True)
        replay_level = Column(String(1), nullable=True, index=True)  # A, B, or None
        determinism_score = Column(Float, nullable=True)
        
        # LLM Configuration
        model_name = Column(String(255), nullable=True, index=True)
        model_provider = Column(String(50), nullable=True)
        temperature = Column(Float, nullable=True)
        
        # Execution Metadata
        duration_ms = Column(Integer, nullable=True)
        cost_usd = Column(Float, nullable=True)
        error_message = Column(Text, nullable=True)
        
        # Token Usage
        prompt_tokens = Column(Integer, default=0)
        completion_tokens = Column(Integer, default=0)
        total_tokens = Column(Integer, default=0)
        cached_tokens = Column(Integer, nullable=True)
        
        # Tool Calls
        tool_call_count = Column(Integer, default=0)
        tool_call_summary = Column(JSONB, default=dict, nullable=False)  # {tool_name: count}
        
        # Storage
        object_storage_uri = Column(String, nullable=True)  # R2 URI or local path
        artifact_size_bytes = Column(Integer, default=0)
        storage_backend = Column(String(50), default="local")  # "local" or "r2"
        
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
            return f"<ArtifactMetadata {self.kurral_id} ({self.semantic_buckets})>"
else:
    # Dummy class when SQLAlchemy is not available
    class ArtifactMetadata:
        """Dummy class when SQLAlchemy is not available"""
        pass

