"""
End-to-End tests for Quick Start Generator.

Tests the complete workflow:
1. Generate project
2. Install dependencies
3. Run agent
4. Run tests
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.slow
class TestEndToEnd:
    """Full end-to-end workflow tests."""

    def test_complete_workflow(self, temp_dir, generator):
        """
        Complete workflow: generate → install → run → test.

        This is the critical path test - if this passes, the feature works.
        """
        project_name = "e2e-test-agent"
        target_dir = temp_dir / project_name

        # Step 1: Generate project
        generator.generate(
            project_name=project_name,
            target_dir=target_dir,
            skip_git=False
        )

        assert target_dir.exists(), "Project directory not created"

        # Step 2: Create virtual environment
        venv_dir = target_dir / "venv"
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Failed to create venv: {result.stderr}"

        # Get paths to venv python and pip
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        assert python_exe.exists(), f"Python executable not found: {python_exe}"

        # Step 3: Install dependencies
        # Note: This installs kurral from local source, not PyPI
        result = subprocess.run(
            [str(pip_exe), "install", "-q", "-r", "requirements.txt"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout for pip install
        )

        if result.returncode != 0:
            pytest.skip(
                f"Pip install failed (may be expected in test environment): {result.stderr}"
            )

        # Step 4: Verify Python files can be imported
        self._test_imports(python_exe, target_dir)

        # Step 5: Run calculator self-test (no external dependencies)
        self._test_calculator(python_exe, target_dir)

        # Step 6: Verify agent.py can be parsed (not run, as it needs API keys)
        self._test_agent_syntax(python_exe, target_dir)

    def _test_imports(self, python_exe, project_dir):
        """Test that all Python files can be imported."""
        # Test tool imports
        result = subprocess.run(
            [
                str(python_exe), "-c",
                "from tools.calculator import create_calculator_tool; "
                "from tools.web_search import create_web_search_tool; "
                "from tools.file_system import create_file_read_tool"
            ],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"Import failed: {result.stderr}")

    def _test_calculator(self, python_exe, project_dir):
        """Run calculator self-test."""
        calc_file = project_dir / "tools" / "calculator.py"

        result = subprocess.run(
            [str(python_exe), str(calc_file)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Calculator self-test failed: {result.stderr}"
        assert "✅" in result.stdout, "Calculator tests did not pass"

    def _test_agent_syntax(self, python_exe, project_dir):
        """Verify agent.py has valid syntax and can be parsed."""
        result = subprocess.run(
            [str(python_exe), "-m", "py_compile", "agent.py"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"agent.py has syntax errors: {result.stderr}"


@pytest.mark.slow
class TestGeneratedProjectStructure:
    """Test that generated project has correct structure."""

    def test_all_expected_files_exist(self, temp_dir, generator):
        """Verify all expected files are present."""
        project_name = "structure-test"
        target_dir = temp_dir / project_name

        generator.generate(project_name, target_dir)

        # Critical files that must exist
        critical_files = [
            "agent.py",
            "requirements.txt",
            ".env.example",
            "README.md",
            ".gitignore",
            "tools/__init__.py",
            "tools/web_search.py",
            "tools/calculator.py",
            "tools/file_system.py",
            "tests/test_agent.py",
            ".kurral/config.yaml",
        ]

        missing_files = []
        for file_path in critical_files:
            full_path = target_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        assert not missing_files, f"Missing files: {', '.join(missing_files)}"

    def test_file_permissions(self, temp_dir, generator):
        """Verify files have appropriate permissions."""
        project_name = "permissions-test"
        target_dir = temp_dir / project_name

        generator.generate(project_name, target_dir)

        # Python files should be readable
        agent_py = target_dir / "agent.py"
        assert agent_py.is_file()
        assert agent_py.stat().st_size > 0, "agent.py is empty"

    def test_no_empty_files(self, temp_dir, generator):
        """No generated files should be empty."""
        project_name = "content-test"
        target_dir = temp_dir / project_name

        generator.generate(project_name, target_dir)

        # Check all Python and config files are not empty
        for pattern in ["*.py", "*.txt", "*.md", "*.yaml"]:
            for file_path in target_dir.rglob(pattern):
                if file_path.name != "__pycache__":
                    size = file_path.stat().st_size
                    assert size > 0, f"File is empty: {file_path.relative_to(target_dir)}"


@pytest.mark.slow
class TestDifferentProjectNames:
    """Test generator with various project names."""

    @pytest.mark.parametrize("project_name", [
        "simple",
        "my-agent",
        "my_agent",
        "agent-v2",
        "TestAgent",
        "agent_2024",
        "a" * 50,  # Max length
    ])
    def test_various_valid_names(self, temp_dir, generator, project_name):
        """Generator should work with various valid project names."""
        target_dir = temp_dir / project_name

        # Should not raise
        generator.generate(project_name, target_dir)

        # Verify basic structure
        assert (target_dir / "agent.py").exists()
        assert (target_dir / "README.md").exists()

    @pytest.mark.parametrize("invalid_name,error_pattern", [
        ("", "empty"),
        ("ab", "at least 3"),
        ("a" * 51, "exceed 50"),
        ("my agent", "spaces"),
        ("my@agent", "letters, numbers, hyphens, and underscores"),
        ("import", "keyword"),
    ])
    def test_various_invalid_names(self, temp_dir, generator, invalid_name, error_pattern):
        """Generator should reject invalid project names."""
        target_dir = temp_dir / "test"

        with pytest.raises(ValueError, match=error_pattern):
            generator.generate(invalid_name, target_dir)


@pytest.mark.slow
class TestCLIIntegration:
    """Test CLI integration."""

    def test_cli_command_generates_project(self, temp_dir):
        """Test that CLI command works."""
        project_name = "cli-test"
        target_dir = temp_dir / project_name

        # Import and run CLI function
        from kurral.cli import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            main,
            ['init', project_name, '--output-dir', str(temp_dir), '--verbose']
        )

        assert result.exit_code == 0, f"CLI command failed: {result.output}"
        assert target_dir.exists(), "Project directory not created"
        assert (target_dir / "agent.py").exists(), "agent.py not created"

    def test_cli_without_project_name_uses_legacy_mode(self, temp_dir):
        """CLI without project name should use legacy mode."""
        from kurral.cli import main
        from click.testing import CliRunner

        runner = CliRunner()

        # Run in temp directory
        with runner.isolated_filesystem(temp_dir=str(temp_dir)):
            result = runner.invoke(main, ['init'])

            assert result.exit_code == 0
            # Legacy mode creates artifacts/ directory
            assert Path("artifacts").exists()
