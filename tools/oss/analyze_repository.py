"""
Analyze Repository Tool

Perform deep codebase analysis to understand repository structure.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.repository import RepositoryManager


class AnalyzeRepositoryParams(BaseModel):
    """Parameters for repository analysis"""

    path: str | None = Field(
        None,
        description="Path to repository (defaults to current working directory)",
    )
    force: bool = Field(
        False, description="Force re-analysis even if cache exists (default: False)"
    )


class AnalyzeRepositoryTool(Tool):
    """Tool for analyzing repository structure"""

    name = "analyze_repository"
    description = "Analyze repository structure to understand architecture, entry points, test strategy, and CI setup. Creates START_HERE.md if missing."
    kind = ToolKind.READ
    schema = AnalyzeRepositoryParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute repository analysis"""
        params = AnalyzeRepositoryParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            manager = RepositoryManager(repo_path)

            # Check if already analyzed (unless force)
            if not params.force and await manager.is_analyzed():
                analysis = await manager.load_analysis()
                output_lines = [
                    "Repository already analyzed (use force=true to re-analyze):",
                    "",
                    f"Project Type: {analysis.get('architecture_summary', 'Unknown').split()[2] if len(analysis.get('architecture_summary', '').split()) > 2 else 'Unknown'}",
                    f"Key Folders: {len(analysis.get('key_folders', {}))}",
                    f"Entry Points: {len(analysis.get('entry_points', []))}",
                    f"Test Strategy: {len(analysis.get('test_strategy', {}))} commands",
                    f"START_HERE.md: {'Exists' if analysis.get('start_here_exists') else 'Missing'}",
                ]
                return ToolResult.success_result("\n".join(output_lines))

            # Perform analysis
            analysis = await manager.analyze()

            # Format output
            output_lines = [
                "Repository Analysis Complete:",
                "",
                f"Project Type: {analysis['architecture_summary'].split()[2] if len(analysis['architecture_summary'].split()) > 2 else 'Unknown'}",
                "",
                "Architecture Summary:",
                analysis["architecture_summary"],
                "",
            ]

            if analysis.get("key_folders"):
                output_lines.append("Key Folders:")
                for folder, purpose in analysis["key_folders"].items():
                    output_lines.append(f"  - {folder}/: {purpose}")
                output_lines.append("")

            if analysis.get("entry_points"):
                output_lines.append("Entry Points:")
                for entry in analysis["entry_points"]:
                    output_lines.append(f"  - {entry}")
                output_lines.append("")

            if analysis.get("test_strategy"):
                output_lines.append("Test Strategy:")
                for test_type, command in analysis["test_strategy"].items():
                    output_lines.append(f"  - {test_type}: {command}")
                output_lines.append("")

            if analysis.get("ci_expectations"):
                output_lines.append("CI Expectations:")
                for expectation in analysis["ci_expectations"]:
                    output_lines.append(f"  - {expectation}")
                output_lines.append("")

            output_lines.append(
                f"START_HERE.md: {'Created' if analysis.get('start_here_exists') else 'Already exists'}"
            )

            return ToolResult.success_result("\n".join(output_lines))

        except Exception as e:
            return ToolResult.error_result(f"Failed to analyze repository: {e}")
