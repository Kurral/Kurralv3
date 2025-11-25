"""
In-memory storage backend for Kurral artifacts.
Useful for testing, development, and high-speed replay scenarios.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import threading
from ..models.kurral import KurralArtifact


class MemoryStorage:
    """
    In-memory storage for Kurral artifacts.
    
    Features:
    - Thread-safe operations
    - Fast read/write with no I/O overhead
    - Optional size limits to prevent memory exhaustion
    - LRU eviction policy when size limit is reached
    """

    def __init__(self, max_artifacts: int = 1000, max_size_mb: int = 500):
        """
        Initialize in-memory storage.
        
        Args:
            max_artifacts: Maximum number of artifacts to store (default: 1000)
            max_size_mb: Maximum total size in MB (default: 500MB)
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._max_artifacts = max_artifacts
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._total_size_bytes = 0
        self._access_times: Dict[str, datetime] = {}

    def upload(self, artifact: KurralArtifact, artifact_id: str) -> str:
        """
        Store an artifact in memory.
        
        Args:
            artifact: The KurralArtifact to store
            artifact_id: Unique identifier for the artifact
            
        Returns:
            str: URI in format "memory://<artifact_id>"
        """
        with self._lock:
            # Serialize artifact to estimate size
            artifact_json = artifact.model_dump_json()
            artifact_size = len(artifact_json.encode('utf-8'))
            
            # Evict if necessary
            self._evict_if_needed(artifact_size)
            
            # Store artifact and metadata
            self._store[artifact_id] = {
                'artifact': artifact,
                'artifact_json': artifact_json,
                'size': artifact_size,
                'stored_at': datetime.utcnow(),
            }
            self._access_times[artifact_id] = datetime.utcnow()
            self._total_size_bytes += artifact_size
            
            return f"memory://{artifact_id}"

    def download(self, artifact_id: str) -> Optional[KurralArtifact]:
        """
        Retrieve an artifact from memory.
        
        Args:
            artifact_id: Unique identifier for the artifact
            
        Returns:
            KurralArtifact if found, None otherwise
        """
        with self._lock:
            if artifact_id not in self._store:
                return None
            
            # Update access time for LRU
            self._access_times[artifact_id] = datetime.utcnow()
            return self._store[artifact_id]['artifact']

    def list_artifacts(self, prefix: Optional[str] = None) -> list[str]:
        """
        List all artifact IDs in memory, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter artifact IDs
            
        Returns:
            List of artifact IDs
        """
        with self._lock:
            if prefix:
                return [aid for aid in self._store.keys() if aid.startswith(prefix)]
            return list(self._store.keys())

    def delete(self, artifact_id: str) -> bool:
        """
        Remove an artifact from memory.
        
        Args:
            artifact_id: Unique identifier for the artifact
            
        Returns:
            True if artifact was deleted, False if not found
        """
        with self._lock:
            if artifact_id not in self._store:
                return False
            
            # Free up size
            artifact_size = self._store[artifact_id]['size']
            self._total_size_bytes -= artifact_size
            
            # Remove from storage
            del self._store[artifact_id]
            del self._access_times[artifact_id]
            
            return True

    def clear(self) -> None:
        """Clear all artifacts from memory."""
        with self._lock:
            self._store.clear()
            self._access_times.clear()
            self._total_size_bytes = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current storage statistics.
        
        Returns:
            Dictionary with count, total_size_mb, and utilization metrics
        """
        with self._lock:
            return {
                'artifact_count': len(self._store),
                'max_artifacts': self._max_artifacts,
                'total_size_mb': round(self._total_size_bytes / (1024 * 1024), 2),
                'max_size_mb': round(self._max_size_bytes / (1024 * 1024), 2),
                'utilization_percent': round(
                    (self._total_size_bytes / self._max_size_bytes) * 100, 2
                ) if self._max_size_bytes > 0 else 0,
            }

    def _evict_if_needed(self, new_artifact_size: int) -> None:
        """
        Evict least recently used artifacts if limits are exceeded.
        
        Args:
            new_artifact_size: Size of the artifact being added
        """
        # Check if we need to evict by count
        while len(self._store) >= self._max_artifacts:
            self._evict_lru()
        
        # Check if we need to evict by size
        while (self._total_size_bytes + new_artifact_size) > self._max_size_bytes:
            if not self._store:  # No more artifacts to evict
                break
            self._evict_lru()

    def _evict_lru(self) -> None:
        """Evict the least recently used artifact."""
        if not self._access_times:
            return
        
        # Find artifact with oldest access time
        lru_id = min(self._access_times.items(), key=lambda x: x[1])[0]
        self.delete(lru_id)


# Global singleton instance for easy access
_global_memory_storage: Optional[MemoryStorage] = None


def get_memory_storage() -> MemoryStorage:
    """
    Get or create the global memory storage instance.
    
    Returns:
        Global MemoryStorage singleton
    """
    global _global_memory_storage
    if _global_memory_storage is None:
        _global_memory_storage = MemoryStorage()
    return _global_memory_storage

