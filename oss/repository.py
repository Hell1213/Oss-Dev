"""
Repository State Management

Manages repository understanding, START_HERE.md creation,
and repository knowledge caching.
"""

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from config.config import Config


@dataclass
class RepositoryAnalysis:
    """Repository analysis results"""

    repo_path: Path
    architecture_summary: str
    key_folders: dict[str, str]
    entry_points: list[str]
    test_strategy: dict[str, str]
    ci_expectations: list[str]
    start_here_exists: bool
    start_here_path: Optional[Path] = None
    analyzed_at: datetime = None

    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.now()


class RepositoryManager:
    """
    Manages repository state and understanding.

    Handles:
    - Repository analysis
    - START_HERE.md creation and management
    - Repository knowledge caching
    """

    def __init__(self, repository_path: Path):
        """
        Initialize repository manager.

        Args:
            repository_path: Path to the repository
        """
        self.repository_path = Path(repository_path).resolve()
        self.analysis_cache_path = self.repository_path / ".oss-dev" / "repository_analysis.json"
        self.start_here_path = self.repository_path / "START_HERE.md"

        # Ensure .oss-dev directory exists
        self.analysis_cache_path.parent.mkdir(parents=True, exist_ok=True)

    async def is_analyzed(self) -> bool:
        """
        Check if repository has been analyzed.

        Returns:
            True if analysis exists and is recent
        """
        if not self.analysis_cache_path.exists():
            return False

        # Check if analysis is recent (within 30 days)
        analysis = self._load_analysis_from_cache()
        if not analysis:
            return False

        analyzed_at = datetime.fromisoformat(analysis.get("analyzed_at", ""))
        days_old = (datetime.now() - analyzed_at).days
        return days_old < 30

    async def analyze(self) -> dict[str, Any]:
        """
        Analyze repository structure and create START_HERE.md if needed.

        Returns:
            Analysis results dictionary
        """
        # Check if START_HERE.md exists
        start_here_exists = self.start_here_path.exists()

        # Perform actual codebase analysis
        analysis = await self._perform_analysis()

        # Create START_HERE.md if it doesn't exist
        if not start_here_exists:
            await self._create_start_here(analysis)
            analysis.start_here_exists = True
            analysis.start_here_path = self.start_here_path

        # Save analysis to cache
        self._save_analysis_to_cache(analysis)

        return asdict(analysis)

    async def _perform_analysis(self) -> RepositoryAnalysis:
        """
        Perform actual repository analysis.

        Returns:
            RepositoryAnalysis object
        """
        # Detect project type
        project_type = self._detect_project_type()

        # Identify key folders
        key_folders = self._identify_key_folders()

        # Find entry points
        entry_points = self._find_entry_points(project_type)

        # Understand test strategy
        test_strategy = self._identify_test_strategy(project_type)

        # Identify CI/CD setup
        ci_expectations = self._identify_ci_expectations()

        # Generate architecture summary
        architecture_summary = self._generate_architecture_summary(
            project_type, key_folders, entry_points
        )

        return RepositoryAnalysis(
            repo_path=self.repository_path,
            architecture_summary=architecture_summary,
            key_folders=key_folders,
            entry_points=entry_points,
            test_strategy=test_strategy,
            ci_expectations=ci_expectations,
            start_here_exists=self.start_here_path.exists(),
            start_here_path=self.start_here_path if self.start_here_path.exists() else None,
        )

    def _detect_project_type(self) -> str:
        """Detect the type of project (Python, Node, etc.)."""
        # Check for common project files
        if (self.repository_path / "package.json").exists():
            return "Node.js"
        elif (self.repository_path / "requirements.txt").exists() or (
            self.repository_path / "pyproject.toml"
        ).exists() or (self.repository_path / "setup.py").exists():
            return "Python"
        elif (self.repository_path / "Cargo.toml").exists():
            return "Rust"
        elif (self.repository_path / "go.mod").exists():
            return "Go"
        elif (self.repository_path / "pom.xml").exists():
            return "Java"
        elif (self.repository_path / "Gemfile").exists():
            return "Ruby"
        else:
            return "Unknown"

    def _identify_key_folders(self) -> dict[str, str]:
        """Identify key folders and their purposes."""
        folders = {}
        common_patterns = {
            "src": "Source code",
            "lib": "Library code",
            "app": "Application code",
            "tests": "Test files",
            "test": "Test files",
            "docs": "Documentation",
            "scripts": "Utility scripts",
            "config": "Configuration files",
            "tools": "Development tools",
        }

        for item in self.repository_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                if item.name in common_patterns:
                    folders[item.name] = common_patterns[item.name]
                elif item.name in ["__pycache__", "node_modules", ".git", ".venv"]:
                    continue
                else:
                    # Try to infer purpose from contents
                    purpose = self._infer_folder_purpose(item)
                    if purpose:
                        folders[item.name] = purpose

        return folders

    def _infer_folder_purpose(self, folder: Path) -> str | None:
        """Infer the purpose of a folder from its contents."""
        # Check for common file patterns
        if any(folder.glob("*.py")):
            return "Python code"
        elif any(folder.glob("*.js")) or any(folder.glob("*.ts")):
            return "JavaScript/TypeScript code"
        elif any(folder.glob("*.md")):
            return "Documentation"
        elif any(folder.glob("*.json")):
            return "Configuration/data"
        return None

    def _find_entry_points(self, project_type: str) -> list[str]:
        """Find entry points for the project."""
        entry_points = []

        # Common entry point files
        common_entry_points = [
            "main.py",
            "app.py",
            "index.js",
            "index.ts",
            "main.rs",
            "main.go",
            "main.java",
        ]

        for entry_file in common_entry_points:
            if (self.repository_path / entry_file).exists():
                entry_points.append(entry_file)

        # Check package.json for scripts
        if project_type == "Node.js":
            package_json = self.repository_path / "package.json"
            if package_json.exists():
                try:
                    import json

                    data = json.loads(package_json.read_text())
                    if "scripts" in data:
                        for script_name, script_cmd in data["scripts"].items():
                            if script_name in ["start", "dev", "serve"]:
                                entry_points.append(f"npm run {script_name}")
                except (json.JSONDecodeError, KeyError):
                    pass

        # Check for setup.py or pyproject.toml entry points
        if project_type == "Python":
            setup_py = self.repository_path / "setup.py"
            pyproject_toml = self.repository_path / "pyproject.toml"
            if setup_py.exists() or pyproject_toml.exists():
                entry_points.append("python -m <module> or pip install -e .")

        return entry_points

    def _identify_test_strategy(self, project_type: str) -> dict[str, str]:
        """Identify test strategy and commands."""
        test_strategy = {}

        # Check for test directories
        test_dirs = ["tests", "test", "__tests__", "spec"]
        for test_dir in test_dirs:
            if (self.repository_path / test_dir).exists():
                if project_type == "Python":
                    test_strategy["Unit tests"] = "pytest"
                    test_strategy["All tests"] = "pytest tests/"
                elif project_type == "Node.js":
                    test_strategy["Unit tests"] = "npm test"
                    test_strategy["All tests"] = "npm test"

        # Check for specific test files
        if project_type == "Python":
            if any(self.repository_path.rglob("test_*.py")):
                test_strategy["Python tests"] = "pytest"
            if (self.repository_path / "pytest.ini").exists() or (
                self.repository_path / "pyproject.toml"
            ).exists():
                test_strategy["Configured tests"] = "pytest"

        elif project_type == "Node.js":
            package_json = self.repository_path / "package.json"
            if package_json.exists():
                try:
                    import json

                    data = json.loads(package_json.read_text())
                    if "scripts" in data and "test" in data["scripts"]:
                        test_strategy["Tests"] = data["scripts"]["test"]
                except (json.JSONDecodeError, KeyError):
                    pass

        return test_strategy

    def _identify_ci_expectations(self) -> list[str]:
        """Identify CI/CD expectations."""
        expectations = []

        # Check for CI config files
        ci_files = {
            ".github/workflows": "GitHub Actions",
            ".gitlab-ci.yml": "GitLab CI",
            ".circleci": "CircleCI",
            ".travis.yml": "Travis CI",
            "Jenkinsfile": "Jenkins",
            ".azure-pipelines.yml": "Azure Pipelines",
        }

        for ci_path, ci_name in ci_files.items():
            ci_file = self.repository_path / ci_path
            if ci_file.exists():
                expectations.append(f"{ci_name} configured")

        # Check for common CI expectations
        if (self.repository_path / ".github/workflows").exists():
            expectations.append("Tests run on push/PR")
            expectations.append("Code quality checks")

        return expectations

    def _generate_architecture_summary(
        self, project_type: str, key_folders: dict[str, str], entry_points: list[str]
    ) -> str:
        """Generate architecture summary."""
        lines = [f"This is a {project_type} project."]

        if key_folders:
            lines.append("\nKey components:")
            for folder, purpose in list(key_folders.items())[:5]:  # Limit to 5
                lines.append(f"- {folder}/: {purpose}")

        if entry_points:
            lines.append("\nEntry points:")
            for entry in entry_points[:3]:  # Limit to 3
                lines.append(f"- {entry}")

        return "\n".join(lines)

    async def load_analysis(self) -> dict[str, Any]:
        """
        Load cached repository analysis.

        Returns:
            Analysis results dictionary
        """
        analysis = self._load_analysis_from_cache()
        if not analysis:
            # If no cache, perform fresh analysis
            return await self.analyze()

        return analysis

    async def _create_start_here(self, analysis: RepositoryAnalysis) -> None:
        """
        Create START_HERE.md file.

        Args:
            analysis: Repository analysis results
        """
        content = self._generate_start_here_content(analysis)
        self.start_here_path.write_text(content, encoding="utf-8")

    def _generate_start_here_content(self, analysis: RepositoryAnalysis) -> str:
        """
        Generate START_HERE.md content.

        Args:
            analysis: Repository analysis results

        Returns:
            START_HERE.md content
        """
        lines = [
            "# START_HERE.md",
            "",
            "> This file was generated by OSS Dev Agent to help understand this repository.",
            "> It serves as a persistent knowledge base for contributing to this project.",
            "",
            "## Architecture Overview",
            "",
            analysis.architecture_summary or "Architecture analysis pending.",
            "",
            "## Key Folders & Responsibilities",
            "",
        ]

        if analysis.key_folders:
            for folder, description in analysis.key_folders.items():
                lines.append(f"- `{folder}/`: {description}")
        else:
            lines.append("Folder structure analysis pending.")

        lines.extend([
            "",
            "## Entry Points",
            "",
        ])

        if analysis.entry_points:
            for entry_point in analysis.entry_points:
                lines.append(f"- {entry_point}")
        else:
            lines.append("Entry points analysis pending.")

        lines.extend([
            "",
            "## Test Strategy",
            "",
        ])

        if analysis.test_strategy:
            for test_type, command in analysis.test_strategy.items():
                lines.append(f"- {test_type}: `{command}`")
        else:
            lines.append("Test strategy analysis pending.")

        lines.extend([
            "",
            "## CI Expectations",
            "",
        ])

        if analysis.ci_expectations:
            for expectation in analysis.ci_expectations:
                lines.append(f"- {expectation}")
        else:
            lines.append("CI expectations analysis pending.")

        lines.extend([
            "",
            "## Contribution Guidelines",
            "",
            "- Commit style: Short, thread-style commits, no emojis",
            "- Code style: Follow existing patterns in repository",
            "- PR process: Reference issue in PR description",
            "",
        ])

        return "\n".join(lines)

    def _save_analysis_to_cache(self, analysis: RepositoryAnalysis) -> None:
        """Save analysis to cache file."""
        data = asdict(analysis)
        # Convert Path objects to strings
        data["repo_path"] = str(data["repo_path"])
        if data.get("start_here_path"):
            data["start_here_path"] = str(data["start_here_path"])
        data["analyzed_at"] = analysis.analyzed_at.isoformat()

        self.analysis_cache_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def _load_analysis_from_cache(self) -> Optional[dict[str, Any]]:
        """Load analysis from cache file."""
        if not self.analysis_cache_path.exists():
            return None

        try:
            content = self.analysis_cache_path.read_text(encoding="utf-8")
            data = json.loads(content)
            # Convert string paths back to Path objects
            data["repo_path"] = Path(data["repo_path"])
            if data.get("start_here_path"):
                data["start_here_path"] = Path(data["start_here_path"])
            return data
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
