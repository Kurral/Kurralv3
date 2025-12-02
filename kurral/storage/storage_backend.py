"""
Storage backend interface and base classes
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime

from kurral.models.kurral import KurralArtifact


@dataclass
class StorageResult:
    """Result of a storage operation"""
    
    success: bool
    storage_uri: Optional[str] = None  # URI like "r2://bucket/key" or "file://path"
    local_path: Optional[Path] = None  # Local file path if applicable
    error: Optional[str] = None


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save(self, artifact: KurralArtifact) -> StorageResult:
        """
        Save artifact to storage
        
        Args:
            artifact: KurralArtifact to save
            
        Returns:
            StorageResult with success status and URI/path
        """
        pass
    
    @abstractmethod
    def load(self, kurral_id: UUID) -> Optional[KurralArtifact]:
        """
        Load artifact by ID
        
        Args:
            kurral_id: Artifact UUID
            
        Returns:
            KurralArtifact or None if not found
        """
        pass
    
    @abstractmethod
    def load_by_run_id(self, run_id: str) -> Optional[KurralArtifact]:
        """
        Load artifact by run_id
        
        Args:
            run_id: Run ID string
            
        Returns:
            KurralArtifact or None if not found
        """
        pass
    
    @abstractmethod
    def exists(self, kurral_id: UUID) -> bool:
        """
        Check if artifact exists
        
        Args:
            kurral_id: Artifact UUID
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    def list_artifacts(self, limit: Optional[int] = None) -> list[KurralArtifact]:
        """
        List all artifacts
        
        Args:
            limit: Maximum number of artifacts to return
            
        Returns:
            List of KurralArtifact, sorted by created_at (most recent first)
        """
        pass

