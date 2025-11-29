"""
Artifact manager for storing and retrieving kurral artifacts
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from Kurral_tester.models.kurral import KurralArtifact


class ArtifactManager:
    """
    Manages storage and retrieval of kurral artifacts
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize artifact manager
        
        Args:
            storage_path: Path to store artifacts (defaults to ./artifacts)
        """
        if storage_path is None:
            storage_path = Path("./artifacts")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, artifact: KurralArtifact) -> Path:
        """
        Save artifact to storage
        
        Args:
            artifact: KurralArtifact to save
            
        Returns:
            Path where artifact was saved
        """
        filename = f"{artifact.kurral_id}.kurral"
        filepath = self.storage_path / filename
        
        try:
            artifact.save(filepath)
            
            # Verify file was written successfully
            if not filepath.exists() or filepath.stat().st_size == 0:
                raise RuntimeError(f"Artifact file was not written or is empty: {filepath}")
            
            # Also save metadata index for quick lookup
            self._update_index(artifact)
            
            return filepath
        except Exception as e:
            # Clean up empty file if it exists
            if filepath.exists() and filepath.stat().st_size == 0:
                filepath.unlink()
            raise RuntimeError(f"Failed to save artifact {artifact.kurral_id}: {e}") from e
    
    def load(self, kurral_id: UUID) -> Optional[KurralArtifact]:
        """
        Load artifact by ID
        
        Args:
            kurral_id: Artifact UUID
            
        Returns:
            KurralArtifact or None if not found
        """
        filename = f"{kurral_id}.kurral"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return None
        
        return KurralArtifact.load(filepath)
    
    def load_by_run_id(self, run_id: str) -> Optional[KurralArtifact]:
        """
        Load artifact by run_id
        
        Args:
            run_id: Run ID string
            
        Returns:
            KurralArtifact or None if not found
        """
        index = self._load_index()
        
        # Search index for run_id
        for entry in index.get("artifacts", []):
            if entry.get("run_id") == run_id:
                kurral_id = UUID(entry["kurral_id"])
                return self.load(kurral_id)
        
        # Fallback: search all artifacts
        for filepath in self.storage_path.glob("*.kurral"):
            try:
                artifact = KurralArtifact.load(filepath)
                if artifact.run_id == run_id:
                    return artifact
            except Exception:
                continue
        
        return None
    
    def load_latest(self) -> Optional[KurralArtifact]:
        """
        Load the most recently created artifact
        
        Returns:
            KurralArtifact or None if no artifacts found
        """
        artifacts = []
        
        for filepath in self.storage_path.glob("*.kurral"):
            try:
                artifact = KurralArtifact.load(filepath)
                artifacts.append((artifact.created_at, artifact))
            except Exception:
                continue
        
        if not artifacts:
            return None
        
        # Sort by created_at, most recent first
        artifacts.sort(key=lambda x: x[0], reverse=True)
        return artifacts[0][1]
    
    def list_artifacts(self, limit: Optional[int] = None) -> list[KurralArtifact]:
        """
        List all artifacts
        
        Args:
            limit: Maximum number of artifacts to return
            
        Returns:
            List of KurralArtifact, sorted by created_at (most recent first)
        """
        artifacts = []
        
        for filepath in self.storage_path.glob("*.kurral"):
            try:
                artifact = KurralArtifact.load(filepath)
                artifacts.append(artifact)
            except Exception as e:
                # Log but continue - don't fail on corrupted artifacts
                import warnings
                warnings.warn(f"Failed to load artifact {filepath.name}: {e}")
                continue
        
        # Sort by created_at, most recent first
        artifacts.sort(key=lambda x: x.created_at, reverse=True)
        
        if limit:
            artifacts = artifacts[:limit]
        
        return artifacts
    
    def _update_index(self, artifact: KurralArtifact) -> None:
        """Update metadata index"""
        index_path = self.storage_path / "index.json"
        
        # Load existing index
        index = self._load_index()
        
        # Add or update entry
        entry = {
            "kurral_id": str(artifact.kurral_id),
            "run_id": artifact.run_id,
            "created_at": artifact.created_at.isoformat(),
            "tenant_id": artifact.tenant_id,
            "semantic_buckets": artifact.semantic_buckets,
        }
        
        # Remove existing entry if present
        artifacts = index.get("artifacts", [])
        artifacts = [a for a in artifacts if a.get("kurral_id") != str(artifact.kurral_id)]
        
        # Add new entry
        artifacts.append(entry)
        
        # Update index
        index["artifacts"] = artifacts
        index["updated_at"] = datetime.utcnow().isoformat()
        
        # Save index
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
    
    def _load_index(self) -> dict:
        """Load metadata index"""
        index_path = self.storage_path / "index.json"
        
        if not index_path.exists():
            return {"artifacts": [], "updated_at": None}
        
        try:
            with open(index_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"artifacts": [], "updated_at": None}

