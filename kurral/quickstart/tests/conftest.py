"""
Pytest configuration and fixtures for Quick Start Generator tests.
"""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for testing.

    Automatically cleaned up after test completes.
    """
    tmp = tempfile.mkdtemp(prefix="kurral_test_")
    yield Path(tmp)
    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def generator():
    """Create a ProjectGenerator instance for testing."""
    from kurral.quickstart import ProjectGenerator
    return ProjectGenerator(verbose=False)


@pytest.fixture
def verbose_generator():
    """Create a verbose ProjectGenerator instance."""
    from kurral.quickstart import ProjectGenerator
    return ProjectGenerator(verbose=True)


@pytest.fixture
def project_name():
    """Default valid project name for tests."""
    return "test-agent"


@pytest.fixture
def generated_project(temp_dir, generator, project_name):
    """
    Generate a complete project for testing.

    Returns the path to the generated project directory.
    """
    target_dir = temp_dir / project_name
    generator.generate(
        project_name=project_name,
        target_dir=target_dir,
        skip_git=False
    )
    return target_dir
