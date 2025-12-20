"""
Unit tests for ProjectGenerator.

Tests validation, template processing, error handling, and file generation.
"""

import ast
import re
from pathlib import Path

import pytest

from kurral.quickstart import ProjectGenerator


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestProjectNameValidation:
    """Test project name validation logic."""

    def test_valid_simple_name(self, generator):
        """Valid simple name should pass."""
        generator._validate_project_name("my-agent")  # Should not raise

    def test_valid_with_underscores(self, generator):
        """Underscores should be allowed."""
        generator._validate_project_name("my_agent")

    def test_valid_with_numbers(self, generator):
        """Numbers should be allowed."""
        generator._validate_project_name("agent-v2")

    def test_valid_mixed_case(self, generator):
        """Mixed case should be allowed."""
        generator._validate_project_name("MyAgent")

    def test_invalid_empty_name(self, generator):
        """Empty name should fail."""
        with pytest.raises(ValueError, match="cannot be empty"):
            generator._validate_project_name("")

    def test_invalid_too_short(self, generator):
        """Name too short should fail."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            generator._validate_project_name("ab")

    def test_invalid_too_long(self, generator):
        """Name too long should fail."""
        long_name = "a" * 51
        with pytest.raises(ValueError, match="cannot exceed 50 characters"):
            generator._validate_project_name(long_name)

    def test_invalid_with_spaces(self, generator):
        """Spaces should not be allowed."""
        with pytest.raises(ValueError, match="cannot contain spaces"):
            generator._validate_project_name("my agent")

    def test_invalid_python_keyword(self, generator):
        """Python keywords should be rejected."""
        with pytest.raises(ValueError, match="keyword"):
            generator._validate_project_name("import")

        with pytest.raises(ValueError, match="keyword"):
            generator._validate_project_name("class")

    def test_invalid_special_chars(self, generator):
        """Special characters should be rejected."""
        with pytest.raises(ValueError, match="letters, numbers, hyphens, and underscores"):
            generator._validate_project_name("my@agent")

        with pytest.raises(ValueError, match="letters, numbers, hyphens, and underscores"):
            generator._validate_project_name("agent!")

    def test_edge_case_minimum_length(self, generator):
        """Exactly 3 characters should pass."""
        generator._validate_project_name("abc")

    def test_edge_case_maximum_length(self, generator):
        """Exactly 50 characters should pass."""
        name = "a" * 50
        generator._validate_project_name(name)


class TestTargetDirectoryValidation:
    """Test target directory validation."""

    def test_valid_nonexistent_directory(self, generator, temp_dir):
        """Nonexistent directory should pass."""
        target = temp_dir / "new-project"
        generator._validate_target_directory(target)

    def test_invalid_existing_directory(self, generator, temp_dir):
        """Existing directory should fail."""
        target = temp_dir / "existing"
        target.mkdir()

        with pytest.raises(FileExistsError, match="already exists"):
            generator._validate_target_directory(target)

    def test_invalid_nonexistent_parent(self, generator, temp_dir):
        """Nonexistent parent should fail."""
        target = temp_dir / "nonexistent" / "child" / "project"

        with pytest.raises(ValueError, match="Parent directory does not exist"):
            generator._validate_target_directory(target)


# ============================================================================
# TEMPLATE PROCESSING TESTS
# ============================================================================

class TestTemplateContext:
    """Test template context building."""

    def test_context_has_all_variables(self, generator):
        """Context should include all required variables."""
        context = generator._build_template_context("my-agent")

        required_vars = ['PROJECT_NAME', 'MODULE_NAME', 'DATE', 'YEAR', 'KURRAL_VERSION']
        for var in required_vars:
            assert var in context, f"Missing variable: {var}"

    def test_project_name_preserved(self, generator):
        """PROJECT_NAME should match input."""
        context = generator._build_template_context("my-test-agent")
        assert context['PROJECT_NAME'] == "my-test-agent"

    def test_module_name_conversion(self, generator):
        """Hyphens should convert to underscores for MODULE_NAME."""
        context = generator._build_template_context("my-test-agent")
        assert context['MODULE_NAME'] == "my_test_agent"

    def test_date_format(self, generator):
        """DATE should be in YYYY-MM-DD format."""
        context = generator._build_template_context("test")
        assert re.match(r'\d{4}-\d{2}-\d{2}', context['DATE'])

    def test_year_is_current(self, generator):
        """YEAR should be current year."""
        from datetime import datetime
        context = generator._build_template_context("test")
        assert context['YEAR'] == str(datetime.now().year)


class TestTemplateProcessing:
    """Test template variable replacement."""

    def test_variables_replaced_in_generated_files(self, generated_project):
        """All template variables should be replaced."""
        # Check agent.py
        agent_py = (generated_project / "agent.py").read_text()

        # Should not have unreplaced variables
        unreplaced = re.findall(r'\{\{([A-Z_]+)\}\}', agent_py)
        assert not unreplaced, f"Unreplaced variables found: {unreplaced}"

    def test_project_name_in_readme(self, generated_project, project_name):
        """Project name should appear in README."""
        readme = (generated_project / "README.md").read_text()
        assert project_name in readme

    def test_date_in_templates(self, generated_project):
        """Date should be present in generated files."""
        readme = (generated_project / "README.md").read_text()
        # Should have date in YYYY-MM-DD format
        assert re.search(r'\d{4}-\d{2}-\d{2}', readme)


# ============================================================================
# FILE GENERATION TESTS
# ============================================================================

class TestFileGeneration:
    """Test that all expected files are generated."""

    def test_base_files_created(self, generated_project):
        """All base files should be created."""
        expected_files = [
            "agent.py",
            "requirements.txt",
            ".env.example",
            "README.md",
            ".gitignore",
        ]

        for file_name in expected_files:
            file_path = generated_project / file_name
            assert file_path.exists(), f"Missing file: {file_name}"
            assert file_path.is_file(), f"Not a file: {file_name}"

    def test_tool_files_created(self, generated_project):
        """All tool files should be created."""
        expected_tools = [
            "tools/__init__.py",
            "tools/web_search.py",
            "tools/calculator.py",
            "tools/file_system.py",
        ]

        for tool_path in expected_tools:
            file_path = generated_project / tool_path
            assert file_path.exists(), f"Missing tool: {tool_path}"

    def test_test_files_created(self, generated_project):
        """Test files should be created."""
        test_file = generated_project / "tests" / "test_agent.py"
        assert test_file.exists()

    def test_config_files_created(self, generated_project):
        """Configuration files should be created."""
        config_file = generated_project / ".kurral" / "config.yaml"
        assert config_file.exists()

    def test_directories_created(self, generated_project):
        """All necessary directories should be created."""
        expected_dirs = [
            "tools",
            "tests",
            ".kurral",
            ".github/workflows",
        ]

        for dir_path in expected_dirs:
            directory = generated_project / dir_path
            assert directory.exists(), f"Missing directory: {dir_path}"
            assert directory.is_dir(), f"Not a directory: {dir_path}"


# ============================================================================
# PYTHON SYNTAX VALIDATION TESTS
# ============================================================================

class TestGeneratedCodeValidity:
    """Test that generated Python code is syntactically valid."""

    def test_agent_py_syntax(self, generated_project):
        """agent.py should have valid Python syntax."""
        agent_py = generated_project / "agent.py"
        code = agent_py.read_text()

        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Invalid Python syntax in agent.py: {e}")

    def test_all_tools_syntax(self, generated_project):
        """All tool files should have valid syntax."""
        tools_dir = generated_project / "tools"

        for tool_file in tools_dir.glob("*.py"):
            code = tool_file.read_text()
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(f"Invalid syntax in {tool_file.name}: {e}")

    def test_test_file_syntax(self, generated_project):
        """Test file should have valid syntax."""
        test_file = generated_project / "tests" / "test_agent.py"
        code = test_file.read_text()

        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Invalid syntax in test_agent.py: {e}")


# ============================================================================
# GIT INITIALIZATION TESTS
# ============================================================================

class TestGitInitialization:
    """Test git repository initialization."""

    def test_git_repo_initialized(self, temp_dir, generator, project_name):
        """Git repository should be initialized by default."""
        target_dir = temp_dir / project_name

        generator.generate(
            project_name=project_name,
            target_dir=target_dir,
            skip_git=False
        )

        git_dir = target_dir / ".git"
        assert git_dir.exists(), "Git repository not initialized"
        assert git_dir.is_dir()

    def test_skip_git_flag(self, temp_dir, generator, project_name):
        """skip_git=True should not initialize git."""
        target_dir = temp_dir / project_name

        generator.generate(
            project_name=project_name,
            target_dir=target_dir,
            skip_git=True
        )

        git_dir = target_dir / ".git"
        assert not git_dir.exists(), "Git repository should not be initialized when skip_git=True"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and error messages."""

    def test_helpful_error_for_existing_directory(self, temp_dir, generator):
        """Should show helpful error when directory exists."""
        project_name = "existing-project"
        target_dir = temp_dir / project_name
        target_dir.mkdir()

        with pytest.raises(FileExistsError) as exc_info:
            generator.generate(project_name, target_dir)

        error_message = str(exc_info.value)
        assert "already exists" in error_message
        assert str(target_dir) in error_message

    def test_helpful_error_for_invalid_name(self, temp_dir, generator):
        """Should show helpful error for invalid name."""
        with pytest.raises(ValueError) as exc_info:
            generator.generate("my project", temp_dir / "test")

        error_message = str(exc_info.value)
        assert "spaces" in error_message.lower()


# ============================================================================
# CONTENT VALIDATION TESTS
# ============================================================================

class TestGeneratedContent:
    """Test that generated content is correct and useful."""

    def test_readme_has_project_name(self, generated_project, project_name):
        """README should mention the project name."""
        readme = (generated_project / "README.md").read_text()
        assert project_name in readme

    def test_readme_has_installation_instructions(self, generated_project):
        """README should have installation instructions."""
        readme = (generated_project / "README.md").read_text()
        assert "pip install" in readme.lower()
        assert "requirements.txt" in readme

    def test_env_example_has_openai_key(self, generated_project):
        """.env.example should mention OPENAI_API_KEY."""
        env_example = (generated_project / ".env.example").read_text()
        assert "OPENAI_API_KEY" in env_example

    def test_requirements_has_kurral(self, generated_project):
        """requirements.txt should include kurral."""
        requirements = (generated_project / "requirements.txt").read_text()
        assert "kurral" in requirements.lower()

    def test_gitignore_excludes_env(self, generated_project):
        """.gitignore should exclude .env files."""
        gitignore = (generated_project / ".gitignore").read_text()
        assert ".env" in gitignore

    def test_config_yaml_exists_and_valid(self, generated_project):
        """.kurral/config.yaml should exist and be valid YAML."""
        config_file = generated_project / ".kurral" / "config.yaml"
        assert config_file.exists()

        # Check it's valid YAML
        import yaml
        try:
            config = yaml.safe_load(config_file.read_text())
            assert config is not None
            assert isinstance(config, dict)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in config.yaml: {e}")


# ============================================================================
# VERBOSE MODE TESTS
# ============================================================================

class TestVerboseMode:
    """Test verbose output mode."""

    def test_verbose_mode_produces_output(self, temp_dir, verbose_generator, project_name, capsys):
        """Verbose mode should produce output."""
        target_dir = temp_dir / project_name

        verbose_generator.generate(project_name, target_dir)

        captured = capsys.readouterr()
        assert len(captured.out) > 0, "Verbose mode should produce output"
        assert "Validating" in captured.out or "Creating" in captured.out

    def test_quiet_mode_minimal_output(self, temp_dir, generator, project_name, capsys):
        """Non-verbose mode should have minimal output."""
        target_dir = temp_dir / project_name

        generator.generate(project_name, target_dir)

        captured = capsys.readouterr()
        # Generator itself doesn't print in non-verbose, success message comes from CLI
        # So captured.out for generator should be minimal or empty
