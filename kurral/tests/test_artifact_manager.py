"""
Tests for artifact manager
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from kurral.artifact_manager import ArtifactManager


class TestArtifactManager:
    """Test suite for ArtifactManager"""

    def test_save_and_load_by_id(self, test_artifact, temp_storage_path):
        """Test saving and loading artifact by ID"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        # Save artifact
        saved_path = manager.save(test_artifact)
        assert saved_path.exists(), "Artifact file should exist"
        
        # Load by ID
        loaded = manager.load(test_artifact.kurral_id)
        assert loaded is not None, "Should load artifact by ID"
        assert loaded.kurral_id == test_artifact.kurral_id, "IDs should match"
        assert loaded.run_id == test_artifact.run_id, "Run IDs should match"

    def test_load_by_run_id(self, test_artifact, temp_storage_path):
        """Test loading artifact by run_id"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        # Save artifact
        manager.save(test_artifact)
        
        # Load by run_id
        loaded = manager.load_by_run_id(test_artifact.run_id)
        assert loaded is not None, "Should load artifact by run_id"
        assert loaded.run_id == test_artifact.run_id, "Run IDs should match"
        assert loaded.kurral_id == test_artifact.kurral_id, "IDs should match"

    def test_load_latest(self, test_artifact, temp_storage_path):
        """Test loading latest artifact"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        # Save artifact
        manager.save(test_artifact)
        
        # Load latest
        latest = manager.load_latest()
        assert latest is not None, "Should load latest artifact"
        assert latest.kurral_id == test_artifact.kurral_id, "Should be the same artifact"

    def test_list_artifacts(self, test_artifact, temp_storage_path):
        """Test listing artifacts"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        # Save artifact
        manager.save(test_artifact)
        
        # List artifacts
        artifacts = manager.list_artifacts()
        assert len(artifacts) == 1, "Should have one artifact"
        assert artifacts[0].kurral_id == test_artifact.kurral_id, "Should match saved artifact"

    def test_list_artifacts_with_limit(self, test_artifact, temp_storage_path):
        """Test listing artifacts with limit"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        # Save artifact
        manager.save(test_artifact)
        
        # List with limit
        artifacts = manager.list_artifacts(limit=1)
        assert len(artifacts) <= 1, "Should respect limit"

    def test_load_nonexistent_artifact(self, temp_storage_path):
        """Test loading non-existent artifact"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        from uuid import uuid4
        loaded = manager.load(uuid4())
        assert loaded is None, "Should return None for non-existent artifact"

    def test_load_nonexistent_run_id(self, temp_storage_path):
        """Test loading non-existent run_id"""
        manager = ArtifactManager(storage_path=temp_storage_path)
        
        loaded = manager.load_by_run_id("nonexistent_run_id")
        assert loaded is None, "Should return None for non-existent run_id"

