"""
Storage backends for Kurral artifacts
"""

from pathlib import Path
from typing import Optional

from kurral.storage.storage_backend import StorageBackend, StorageResult
from kurral.storage.local_storage import LocalStorage
from kurral.storage.r2_storage import R2Storage
from kurral.config import StorageConfig, get_agent_name

__all__ = [
    "StorageBackend",
    "StorageResult",
    "LocalStorage",
    "R2Storage",
    "create_storage_backend",
]


def create_storage_backend(
    config: StorageConfig,
    default_storage_path: Optional[Path] = None,
    agent_dir: Optional[Path] = None,
    path_prefix: str = "artifacts"
) -> StorageBackend:
    """
    Create appropriate storage backend based on configuration
    
    Args:
        config: StorageConfig instance
        default_storage_path: Default path for local storage if not in config
        agent_dir: Optional agent directory for determining agent name
        path_prefix: Path prefix for R2 storage ("artifacts" or "replay_runs")
        
    Returns:
        StorageBackend instance (LocalStorage or R2Storage)
    """
    # Determine local storage path
    local_path = config.local_storage_path or default_storage_path or Path("./artifacts")
    
    # R2-only mode if credentials are provided
    if config.has_r2_credentials():
        agent_name = get_agent_name(agent_dir)
        
        return R2Storage(
            account_id=config.r2_account_id,
            access_key_id=config.r2_access_key_id,
            secret_access_key=config.r2_secret_access_key,
            bucket_name=config.r2_bucket_name,
            tenant_id=config.tenant_id,
            agent_name=agent_name,
            path_prefix=path_prefix,
            local_backup_path=None  # R2-only, no local backup
        )
    
    # Local only (default when R2 not configured)
    return LocalStorage(storage_path=local_path)

