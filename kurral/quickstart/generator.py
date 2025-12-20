"""
Project Generator for Kurral Quick Start

Generates production-ready agent projects from templates.
"""

import keyword
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Kurral version - will be populated from package
try:
    from kurral import __version__ as KURRAL_VERSION
except:
    KURRAL_VERSION = "0.3.1"


class ProjectGenerator:
    """
    Generates Kurral agent projects from templates.

    Handles:
    - Input validation
    - Directory creation
    - Template processing
    - Git initialization
    - User feedback
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize generator.

        Args:
            verbose: Show detailed progress output
        """
        self.verbose = verbose
        self.template_dir = Path(__file__).parent / "templates"

    def generate(
        self,
        project_name: str,
        target_dir: Path,
        skip_git: bool = False,
        framework: str = "vanilla"
    ) -> None:
        """
        Generate a new Kurral agent project.

        Args:
            project_name: Name of the project
            target_dir: Directory to create project in
            skip_git: Skip git initialization
            framework: Framework to use ("vanilla" or "langchain")

        Raises:
            ValueError: If inputs are invalid
            FileExistsError: If target directory exists
            RuntimeError: If generation fails
        """
        # Step 0: Validate framework
        if framework not in ["vanilla", "langchain"]:
            raise ValueError(f"Unknown framework: {framework}. Must be 'vanilla' or 'langchain'")

        # Step 1: Validate inputs
        self._log(f"Generating {framework} project...")
        self._validate_project_name(project_name)
        self._validate_target_directory(target_dir)

        # Step 2: Create directory structure
        self._log("Creating directory structure...")
        self._create_directories(target_dir)

        # Step 3: Build template context
        context = self._build_template_context(project_name, framework)

        # Step 4: Process templates
        self._log("Generating files from templates...")
        self._process_templates(target_dir, context, framework)

        # Step 5: Initialize git
        if not skip_git:
            self._log("Initializing git repository...")
            self._init_git(target_dir)

        # Step 6: Print success message
        self._print_success(project_name, target_dir, framework)

    def _validate_project_name(self, name: str) -> None:
        """
        Validate project name.

        Rules:
        - Not empty
        - No spaces (use hyphens or underscores)
        - Not a Python keyword
        - Alphanumeric + hyphens/underscores only
        - Length 3-50 characters
        """
        if not name:
            raise ValueError("Project name cannot be empty")

        if len(name) < 3:
            raise ValueError("Project name must be at least 3 characters")

        if len(name) > 50:
            raise ValueError("Project name cannot exceed 50 characters")

        if ' ' in name:
            raise ValueError(
                "Project name cannot contain spaces. "
                "Use hyphens (-) or underscores (_) instead."
            )

        # Check if it's a Python keyword
        module_name = name.replace('-', '_')
        if keyword.iskeyword(module_name):
            raise ValueError(
                f"'{name}' converts to Python keyword '{module_name}'. "
                f"Please choose a different name."
            )

        # Check alphanumeric + hyphens/underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                "Project name must contain only letters, numbers, "
                "hyphens, and underscores"
            )

    def _validate_target_directory(self, target_dir: Path) -> None:
        """Validate target directory doesn't exist."""
        if target_dir.exists():
            raise FileExistsError(
                f"Directory already exists: {target_dir}\n"
                f"Please choose a different name or remove the existing directory."
            )

        # Check parent exists
        if not target_dir.parent.exists():
            raise ValueError(
                f"Parent directory does not exist: {target_dir.parent}"
            )

    def _create_directories(self, target_dir: Path) -> None:
        """Create project directory structure."""
        # Main directories
        directories = [
            target_dir,
            target_dir / "tools",
            target_dir / "tests",
            target_dir / ".kurral",
            target_dir / ".github" / "workflows",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self._log(f"  Created: {directory.relative_to(target_dir.parent)}")

    def _build_template_context(self, project_name: str, framework: str) -> Dict[str, str]:
        """
        Build template variable context.

        Variables available in templates:
        - PROJECT_NAME: "my-agent"
        - MODULE_NAME: "my_agent"
        - DATE: "2024-12-19"
        - YEAR: "2024"
        - KURRAL_VERSION: "0.3.1"
        - FRAMEWORK: "vanilla" or "langchain"
        """
        now = datetime.now()

        return {
            'PROJECT_NAME': project_name,
            'MODULE_NAME': project_name.replace('-', '_'),
            'DATE': now.strftime('%Y-%m-%d'),
            'YEAR': str(now.year),
            'KURRAL_VERSION': KURRAL_VERSION,
            'FRAMEWORK': framework,
        }

    def _process_templates(self, target_dir: Path, context: Dict[str, str], framework: str) -> None:
        """
        Process all templates and write to target directory.

        Template variable syntax: {{VARIABLE_NAME}}
        """
        # Template mappings: source -> destination
        # Framework-specific templates (from vanilla/ or langchain/)
        framework_templates = {
            f'{framework}/agent.py.template': 'agent.py',
            f'{framework}/requirements.txt.template': 'requirements.txt',
            f'{framework}/tools/__init__.py.template': 'tools/__init__.py',
            f'{framework}/tools/web_search.py.template': 'tools/web_search.py',
            f'{framework}/tools/calculator.py.template': 'tools/calculator.py',
            f'{framework}/tools/file_system.py.template': 'tools/file_system.py',
        }

        # Shared templates (framework-agnostic)
        shared_templates = {
            'shared/.env.example.template': '.env.example',
            'shared/README.md.template': 'README.md',
            'shared/.gitignore.template': '.gitignore',
            'shared/tests/test_agent.py.template': 'tests/test_agent.py',
            'kurral_config/config.yaml.template': '.kurral/config.yaml',
        }

        # Combine all templates
        all_templates = {**framework_templates, **shared_templates}

        for template_path, output_path in all_templates.items():
            template_file = self.template_dir / template_path
            output_file = target_dir / output_path

            if not template_file.exists():
                raise RuntimeError(f"Template not found: {template_file}")

            # Read template
            template_content = template_file.read_text(encoding='utf-8')

            # Replace variables
            processed_content = template_content
            for var_name, var_value in context.items():
                placeholder = f'{{{{{var_name}}}}}'
                processed_content = processed_content.replace(placeholder, var_value)

            # Check for unreplaced variables (indicates missing context)
            unreplaced = re.findall(r'\{\{([A-Z_]+)\}\}', processed_content)
            if unreplaced:
                raise RuntimeError(
                    f"Template has unreplaced variables in {template_path}: "
                    f"{', '.join(set(unreplaced))}"
                )

            # Write output
            output_file.write_text(processed_content, encoding='utf-8')
            self._log(f"  Generated: {output_path}")

    def _init_git(self, target_dir: Path) -> None:
        """Initialize git repository."""
        try:
            subprocess.run(
                ['git', 'init'],
                cwd=target_dir,
                check=True,
                capture_output=True
            )
            self._log("  Git repository initialized")
        except subprocess.CalledProcessError as e:
            # Git init failed, but don't fail the whole generation
            self._log(f"  Warning: Git init failed: {e.stderr.decode()}")
        except FileNotFoundError:
            # Git not installed
            self._log("  Warning: Git not found. Skipping git init.")

    def _print_success(self, project_name: str, target_dir: Path, framework: str) -> None:
        """Print success message with next steps."""
        framework_label = "Vanilla Python" if framework == "vanilla" else "LangChain"

        print()
        print("=" * 60)
        print(f"✨ Project created successfully! ({framework_label})")
        print("=" * 60)
        print()
        print(f"📁 Location: {target_dir}")
        print()
        print("🚀 Next steps:")
        print()
        print(f"  1. cd {project_name}")
        print("  2. pip install -r requirements.txt")
        print("  3. cp .env.example .env")
        print("     (Edit .env and add your OPENAI_API_KEY)")
        print("  4. python agent.py")
        print()
        print("📖 See README.md for detailed documentation")
        print()
        print("💡 Pro tip: Run 'kurral replay --latest' after first execution")
        print("   to replay with zero API costs!")
        print()

    def _log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(message)
