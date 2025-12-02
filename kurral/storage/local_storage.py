"""
Local file system storage backend
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from kurral.models.kurral import KurralArtifact
from kurral.storage.storage_backend import StorageBackend, StorageResult


class LocalStorage(StorageBackend):
    """Local file system storage backend"""
    
    def __init__(self, storage_path: Path):
        """
        Initialize local storage
        
        Args:
            storage_path: Path to store artifacts (defaults to ./artifacts)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, artifact: KurralArtifact) -> StorageResult:
        """Save artifact to local file system"""
        filename = f"{artifact.kurral_id}.kurral"
        filepath = self.storage_path / filename
        
        try:
            artifact.save(filepath)
            
            # Verify file was written successfully
            if not filepath.exists() or filepath.stat().st_size == 0:
                return StorageResult(
                    success=False,
                    error=f"Artifact file was not written or is empty: {filepath}"
                )
            
            # Update index
            self._update_index(artifact)
            
            # Create file URI
            storage_uri = f"file://{filepath.absolute()}"
            
            return StorageResult(
                success=True,
                storage_uri=storage_uri,
                local_path=filepath
            )
        except Exception as e:
            # Clean up empty file if it exists
            if filepath.exists() and filepath.stat().st_size == 0:
                filepath.unlink()
            return StorageResult(
                success=False,
                error=f"Failed to save artifact {artifact.kurral_id}: {e}"
            )
    
    def load(self, kurral_id: UUID) -> Optional[KurralArtifact]:
        """Load artifact by ID"""
        filename = f"{kurral_id}.kurral"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return None
        
        return KurralArtifact.load(filepath)
    
    def load_by_run_id(self, run_id: str) -> Optional[KurralArtifact]:
        """Load artifact by run_id"""
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
    
    def exists(self, kurral_id: UUID) -> bool:
        """Check if artifact exists"""
        filename = f"{kurral_id}.kurral"
        filepath = self.storage_path / filename
        return filepath.exists()
    
    def list_artifacts(self, limit: Optional[int] = None) -> list[KurralArtifact]:
        """List all artifacts"""
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

