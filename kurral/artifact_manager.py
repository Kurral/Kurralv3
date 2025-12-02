"""
Artifact manager for storing and retrieving kurral artifacts
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import UUID

from kurral.models.kurral import KurralArtifact
from kurral.storage import StorageBackend, create_storage_backend
from kurral.storage.local_storage import LocalStorage
from kurral.config import StorageConfig, get_storage_config
from kurral.database.metadata_service import MetadataService


class ArtifactManager:
    """
    Manages storage and retrieval of kurral artifacts
    Supports multiple storage backends (local, R2) with smart fallback
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        config: Optional[StorageConfig] = None,
        agent_dir: Optional[Path] = None
    ):
        """
        Initialize artifact manager
        
        Args:
            storage_path: Path to store artifacts (defaults to ./artifacts)
            config: Optional StorageConfig instance (if not provided, will try to load from agent_dir)
            agent_dir: Optional path to agent directory for loading .env configuration
        """
        # Load configuration if not provided
        if config is None:
            config = get_storage_config(agent_dir)
        
        self.config = config
        
        # Determine storage path
        if storage_path is None:
            storage_path = config.local_storage_path or Path("./artifacts")
        
        self.storage_path = Path(storage_path)
        self.agent_dir = agent_dir
        
        # Create storage backend
        self.backend = create_storage_backend(
            config, 
            self.storage_path, 
            agent_dir=agent_dir,
            path_prefix="artifacts"
        )
        
        # Keep reference to local storage for migration purposes (but don't use for R2-only mode)
        self.local_backend = LocalStorage(storage_path=self.storage_path)
        self.using_r2 = not isinstance(self.backend, LocalStorage)
        
        # Initialize metadata service if database is configured
        self.metadata_service = None
        if config.database_url:
            try:
                self.metadata_service = MetadataService(database_url=config.database_url)
                # Ensure tables are created
                if self.metadata_service.is_available():
                    from kurral.database.connection import create_tables
                    create_tables(config.database_url)
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to initialize metadata service: {e}")
        
        # Track if migration has been attempted for this instance
        self._migration_checked = False
    
    def save(self, artifact: KurralArtifact) -> Path:
        """
        Save artifact to storage
        
        R2-only mode: Saves only to R2 (no local backup)
        Local mode: Saves only to local storage
        
        Automatically migrates existing local artifacts to R2 on first save
        when R2 is configured.
        
        Args:
            artifact: KurralArtifact to save
            
        Returns:
            Path (for backward compatibility - may be None for R2-only)
        """
        # Auto-migrate on first save if using R2
        if self.using_r2 and not self._migration_checked:
            self._migration_checked = True
            try:
                # Migrate existing artifacts
                artifacts_stats = self.migrate_local_to_r2()
                
                # Migrate existing replay artifacts
                if self.agent_dir:
                    replay_runs_dir = self.agent_dir / "replay_runs"
                    if replay_runs_dir.exists():
                        replay_stats = self.migrate_replay_artifacts_to_r2(replay_runs_dir)
                        total_migrated = artifacts_stats["migrated"] + replay_stats["migrated"]
                        if total_migrated > 0:
                            print(f"[Kurral] Migrated {total_migrated} artifacts to R2")
            except Exception as e:
                # Don't fail save if migration fails
                import warnings
                warnings.warn(f"Migration warning: {e}")
        
        # Save to configured backend
        result = self.backend.save(artifact)
        
        if not result.success:
            raise RuntimeError(
                f"Failed to save artifact: {result.error}"
            )
        
        # Update artifact with storage URI if R2
        if result.storage_uri:
            artifact.object_storage_uri = result.storage_uri
        
        # Save metadata to PostgreSQL if configured
        if self.metadata_service and self.metadata_service.is_available():
            storage_uri = result.storage_uri or (f"file://{result.local_path}" if result.local_path else None)
            storage_backend = "r2" if self.using_r2 else "local"
            try:
                self.metadata_service.save_metadata(
                    artifact=artifact,
                    storage_uri=storage_uri,
                    storage_backend=storage_backend
                )
            except Exception as e:
                # Don't fail artifact save if metadata save fails
                import warnings
                warnings.warn(f"Failed to save artifact metadata to database: {e}")
        
        # Return path for backward compatibility
        if result.local_path:
            return result.local_path
        elif self.using_r2:
            # For R2-only mode, return a dummy path (for backward compatibility)
            return self.storage_path / f"{artifact.kurral_id}.kurral"
        else:
            return result.local_path or self.storage_path / f"{artifact.kurral_id}.kurral"
    
    def load(self, kurral_id: UUID) -> Optional[KurralArtifact]:
        """
        Load artifact by ID
        
        For R2 mode: Loads from R2 only
        For local mode: Loads from local storage only
        
        Args:
            kurral_id: Artifact UUID
            
        Returns:
            KurralArtifact or None if not found
        """
        return self.backend.load(kurral_id)
    
    def load_by_run_id(self, run_id: str) -> Optional[KurralArtifact]:
        """
        Load artifact by run_id
        
        For R2 mode: Loads from R2 only
        For local mode: Loads from local storage only
        
        Args:
            run_id: Run ID string
            
        Returns:
            KurralArtifact or None if not found
        """
        return self.backend.load_by_run_id(run_id)
    
    def load_latest(self) -> Optional[KurralArtifact]:
        """
        Load the most recently created artifact
        
        Returns:
            KurralArtifact or None if no artifacts found
        """
        artifacts = self.list_artifacts(limit=1)
        return artifacts[0] if artifacts else None
    
    def list_artifacts(self, limit: Optional[int] = None) -> list[KurralArtifact]:
        """
        List all artifacts
        
        Args:
            limit: Maximum number of artifacts to return
            
        Returns:
            List of KurralArtifact, sorted by created_at (most recent first)
        """
        return self.backend.list_artifacts(limit=limit)
    
    def migrate_local_to_r2(self) -> dict:
        """
        Migrate existing local artifacts to R2
        
        Scans local artifacts and replay_runs directories and uploads
        all artifacts to R2. Only migrates if R2 is configured.
        
        Returns:
            Dictionary with migration statistics
        """
        if not self.using_r2:
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "message": "R2 not configured, no migration needed"
            }
        
        stats = {
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "errors_detail": []
        }
        
        # Migrate artifacts from artifacts/ directory
        artifacts_dir = self.storage_path
        if artifacts_dir.exists():
            for artifact_file in artifacts_dir.glob("*.kurral"):
                try:
                    artifact = KurralArtifact.load(artifact_file)
                    # Check if already in R2
                    if self.backend.exists(artifact.kurral_id):
                        stats["skipped"] += 1
                        continue
                    
                    # Upload to R2
                    result = self.backend.save(artifact)
                    if result.success:
                        stats["migrated"] += 1
                    else:
                        stats["errors"] += 1
                        stats["errors_detail"].append(f"Failed to migrate {artifact.kurral_id}: {result.error}")
                except Exception as e:
                    stats["errors"] += 1
                    stats["errors_detail"].append(f"Error processing {artifact_file.name}: {e}")
        
        return stats
    
    def migrate_replay_artifacts_to_r2(self, replay_runs_dir: Path) -> dict:
        """
        Migrate existing replay artifacts to R2
        
        Args:
            replay_runs_dir: Path to replay_runs directory
            
        Returns:
            Dictionary with migration statistics
        """
        if not self.using_r2:
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "message": "R2 not configured, no migration needed"
            }
        
        # Create replay storage backend with replay_runs path prefix
        from kurral.storage import create_storage_backend
        replay_backend = create_storage_backend(
            self.config,
            replay_runs_dir,
            agent_dir=self.agent_dir,
            path_prefix="replay_runs"
        )
        
        stats = {
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "errors_detail": []
        }
        
        if not replay_runs_dir.exists():
            return stats
        
        for artifact_file in replay_runs_dir.glob("*.kurral"):
            try:
                artifact = KurralArtifact.load(artifact_file)
                # Check if already in R2
                if replay_backend.exists(artifact.kurral_id):
                    stats["skipped"] += 1
                    continue
                
                # Upload to R2
                result = replay_backend.save(artifact)
                if result.success:
                    stats["migrated"] += 1
                else:
                    stats["errors"] += 1
                    stats["errors_detail"].append(f"Failed to migrate replay {artifact.kurral_id}: {result.error}")
            except Exception as e:
                    stats["errors"] += 1
                    stats["errors_detail"].append(f"Error processing replay {artifact_file.name}: {e}")
        
        return stats
    
    def ensure_r2_migration(self, show_message: bool = True) -> dict:
        """
        Ensure all local artifacts are migrated to R2 before proceeding.
        
        This method checks if R2 is configured and if there are local artifacts
        that need migration. If so, it migrates them with user feedback.
        
        This is idempotent - safe to call multiple times. Artifacts already in R2
        will be skipped.
        
        Args:
            show_message: Whether to print migration progress messages (default: True)
            
        Returns:
            Dictionary with migration statistics including:
            - migrated: Number of artifacts migrated
            - skipped: Number of artifacts skipped (already in R2)
            - errors: Number of errors during migration
            - message: Status message
        """
        # Check if R2 is configured
        if not self.using_r2:
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "message": "R2 not configured, no migration needed"
            }
        
        # Check if migration was already done in this instance
        if self._migration_checked:
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "message": "Migration already checked in this session"
            }
        
        # Check if there are any local artifacts to migrate
        local_artifacts_exist = False
        if self.storage_path.exists():
            local_artifacts_exist = any(self.storage_path.glob("*.kurral"))
        
        replay_artifacts_exist = False
        if self.agent_dir:
            replay_runs_dir = self.agent_dir / "replay_runs"
            if replay_runs_dir.exists():
                replay_artifacts_exist = any(replay_runs_dir.glob("*.kurral"))
        
        if not local_artifacts_exist and not replay_artifacts_exist:
            self._migration_checked = True
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "message": "No local artifacts to migrate"
            }
        
        # Show loading message
        if show_message:
            print("Loading R2...")
        
        # Mark as checked to prevent duplicate migrations
        self._migration_checked = True
        
        try:
            total_migrated = 0
            total_skipped = 0
            total_errors = 0
            error_details = []
            
            # Migrate artifacts from artifacts/ directory
            if local_artifacts_exist:
                artifacts_stats = self.migrate_local_to_r2()
                total_migrated += artifacts_stats.get("migrated", 0)
                total_skipped += artifacts_stats.get("skipped", 0)
                total_errors += artifacts_stats.get("errors", 0)
                if "errors_detail" in artifacts_stats:
                    error_details.extend(artifacts_stats["errors_detail"])
            
            # Migrate replay artifacts
            if replay_artifacts_exist and self.agent_dir:
                replay_runs_dir = self.agent_dir / "replay_runs"
                if replay_runs_dir.exists():
                    replay_stats = self.migrate_replay_artifacts_to_r2(replay_runs_dir)
                    total_migrated += replay_stats.get("migrated", 0)
                    total_skipped += replay_stats.get("skipped", 0)
                    total_errors += replay_stats.get("errors", 0)
                    if "errors_detail" in replay_stats:
                        error_details.extend(replay_stats["errors_detail"])
            
            # Build summary message
            if total_migrated > 0:
                message = f"Migrated {total_migrated} artifact(s) to R2"
                if total_skipped > 0:
                    message += f", skipped {total_skipped} (already in R2)"
                if total_errors > 0:
                    message += f", {total_errors} error(s)"
                    if show_message and error_details:
                        for error in error_details[:5]:  # Show first 5 errors
                            print(f"  Warning: {error}")
            elif total_skipped > 0:
                message = f"All artifacts already in R2 ({total_skipped} skipped)"
            else:
                message = "No artifacts to migrate"
            
            if show_message and total_migrated > 0:
                print(message)
            
            return {
                "migrated": total_migrated,
                "skipped": total_skipped,
                "errors": total_errors,
                "errors_detail": error_details,
                "message": message
            }
        except Exception as e:
            # Don't fail replay if migration fails
            error_msg = f"Migration error: {e}"
            if show_message:
                import warnings
                warnings.warn(error_msg)
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "errors_detail": [error_msg],
                "message": error_msg
            }

