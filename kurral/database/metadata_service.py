"""
Metadata service for saving and querying artifact metadata in PostgreSQL
"""

import warnings
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import and_, or_, func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from kurral.models.kurral import KurralArtifact
from kurral.database.connection import get_db_connection, DatabaseConnection
from kurral.database.models import ArtifactMetadata


class MetadataService:
    """Service for managing artifact metadata in PostgreSQL"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize metadata service
        
        Args:
            database_url: Optional PostgreSQL connection string
        """
        self.database_url = database_url
        self._db_conn: Optional[DatabaseConnection] = None
        
        if database_url:
            self._db_conn = get_db_connection(database_url)
    
    def is_available(self) -> bool:
        """Check if metadata service is available (database configured)"""
        return self._db_conn is not None and SQLALCHEMY_AVAILABLE
    
    def save_metadata(self, artifact: KurralArtifact, storage_uri: Optional[str] = None, storage_backend: str = "local") -> bool:
        """
        Save artifact metadata to PostgreSQL
        
        Args:
            artifact: KurralArtifact instance
            storage_uri: Optional storage URI (R2 URI or local file path)
            storage_backend: Storage backend type ("local" or "r2")
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Extract metadata from artifact
            token_usage = artifact.token_usage
            determinism_report = artifact.determinism_report
            
            # Extract tool call summary
            tool_call_summary = {}
            for tool_call in artifact.tool_calls:
                tool_name = tool_call.tool_name if hasattr(tool_call, 'tool_name') else tool_call.get('tool_name', 'unknown')
                tool_call_summary[tool_name] = tool_call_summary.get(tool_name, 0) + 1
            
            # Extract graph and prompt hashes
            graph_hash = None
            prompt_hash = None
            if artifact.graph_version:
                graph_hash = artifact.graph_version.graph_hash if hasattr(artifact.graph_version, 'graph_hash') else None
            
            if artifact.resolved_prompt:
                prompt_hash = artifact.resolved_prompt.final_text_hash if hasattr(artifact.resolved_prompt, 'final_text_hash') else None
            
            # Get artifact size (estimate if not available)
            artifact_size = 0
            if storage_uri and storage_backend == "r2":
                # For R2, we'd need to check object size
                # For now, estimate from JSON size
                artifact_size = len(artifact.to_json().encode('utf-8'))
            elif storage_uri:
                # For local files, we could check file size
                from pathlib import Path
                try:
                    path = Path(storage_uri)
                    if path.exists():
                        artifact_size = path.stat().st_size
                except Exception:
                    pass
            
            with self._db_conn.get_session() as session:
                # Check if metadata already exists
                existing = session.query(ArtifactMetadata).filter(
                    ArtifactMetadata.kurral_id == artifact.kurral_id
                ).first()
                
                if existing:
                    # Update existing metadata
                    existing.run_id = artifact.run_id
                    existing.tenant_id = artifact.tenant_id
                    existing.semantic_buckets = artifact.semantic_buckets
                    existing.environment = artifact.environment
                    existing.deterministic = artifact.deterministic
                    existing.replay_level = artifact.replay_level.value if artifact.replay_level else None
                    existing.determinism_score = determinism_report.overall_score if determinism_report else None
                    existing.model_name = artifact.llm_config.model_name if artifact.llm_config else None
                    existing.model_provider = artifact.llm_config.provider if artifact.llm_config else None
                    existing.temperature = artifact.llm_config.parameters.temperature if artifact.llm_config and artifact.llm_config.parameters else None
                    existing.duration_ms = artifact.duration_ms
                    existing.cost_usd = artifact.cost_usd
                    existing.error_message = artifact.error
                    existing.prompt_tokens = token_usage.prompt_tokens if token_usage else 0
                    existing.completion_tokens = token_usage.completion_tokens if token_usage else 0
                    existing.total_tokens = token_usage.total_tokens if token_usage else 0
                    existing.cached_tokens = token_usage.cached_tokens if token_usage else None
                    existing.tool_call_count = len(artifact.tool_calls)
                    existing.tool_call_summary = tool_call_summary
                    existing.object_storage_uri = storage_uri or artifact.object_storage_uri
                    existing.artifact_size_bytes = artifact_size
                    existing.storage_backend = storage_backend
                    existing.created_at = artifact.created_at
                    existing.created_by = artifact.created_by
                    existing.tags = artifact.tags or {}
                    existing.graph_hash = graph_hash
                    existing.prompt_hash = prompt_hash
                else:
                    # Create new metadata record
                    metadata = ArtifactMetadata(
                        kurral_id=artifact.kurral_id,
                        run_id=artifact.run_id,
                        tenant_id=artifact.tenant_id,
                        semantic_buckets=artifact.semantic_buckets,
                        environment=artifact.environment,
                        deterministic=artifact.deterministic,
                        replay_level=artifact.replay_level.value if artifact.replay_level else None,
                        determinism_score=determinism_report.overall_score if determinism_report else None,
                        model_name=artifact.llm_config.model_name if artifact.llm_config else None,
                        model_provider=artifact.llm_config.provider if artifact.llm_config else None,
                        temperature=artifact.llm_config.parameters.temperature if artifact.llm_config and artifact.llm_config.parameters else None,
                        duration_ms=artifact.duration_ms,
                        cost_usd=artifact.cost_usd,
                        error_message=artifact.error,
                        prompt_tokens=token_usage.prompt_tokens if token_usage else 0,
                        completion_tokens=token_usage.completion_tokens if token_usage else 0,
                        total_tokens=token_usage.total_tokens if token_usage else 0,
                        cached_tokens=token_usage.cached_tokens if token_usage else None,
                        tool_call_count=len(artifact.tool_calls),
                        tool_call_summary=tool_call_summary,
                        object_storage_uri=storage_uri or artifact.object_storage_uri,
                        artifact_size_bytes=artifact_size,
                        storage_backend=storage_backend,
                        created_at=artifact.created_at,
                        created_by=artifact.created_by,
                        tags=artifact.tags or {},
                        graph_hash=graph_hash,
                        prompt_hash=prompt_hash,
                    )
                    session.add(metadata)
                
                session.commit()
                return True
        except Exception as e:
            warnings.warn(f"Failed to save artifact metadata to database: {e}")
            return False
    
    def get_metadata(self, kurral_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get artifact metadata by ID
        
        Args:
            kurral_id: Artifact UUID
            
        Returns:
            Metadata dictionary or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            with self._db_conn.get_session() as session:
                metadata = session.query(ArtifactMetadata).filter(
                    ArtifactMetadata.kurral_id == kurral_id
                ).first()
                
                if metadata:
                    return self._metadata_to_dict(metadata)
                return None
        except Exception as e:
            warnings.warn(f"Failed to get artifact metadata from database: {e}")
            return None
    
    def _metadata_to_dict(self, metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Convert SQLAlchemy model to dictionary"""
        return {
            "kurral_id": str(metadata.kurral_id),
            "run_id": metadata.run_id,
            "tenant_id": metadata.tenant_id,
            "semantic_buckets": metadata.semantic_buckets,
            "environment": metadata.environment,
            "deterministic": metadata.deterministic,
            "replay_level": metadata.replay_level,
            "determinism_score": metadata.determinism_score,
            "model_name": metadata.model_name,
            "model_provider": metadata.model_provider,
            "temperature": metadata.temperature,
            "duration_ms": metadata.duration_ms,
            "cost_usd": metadata.cost_usd,
            "error_message": metadata.error_message,
            "object_storage_uri": metadata.object_storage_uri,
            "storage_backend": metadata.storage_backend,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
        }

