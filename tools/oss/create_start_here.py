"""
Create START_HERE.md Tool

Generate START_HERE.md file for the repository.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.repository import RepositoryManager


class CreateStartHereParams(BaseModel):
    """Parameters for creating START_HERE.md"""

    path: str | None = Field(
        None,
        description="Path to repository (defaults to current working directory)",
    )
    force: bool = Field(
        False,
        description="Overwrite existing START_HERE.md if it exists (default: False)",
    )


class CreateStartHereTool(Tool):
    """Tool for creating START_HERE.md"""

    name = "create_start_here"
    description = "Generate START_HERE.md file for the repository. Analyzes the repository and creates a knowledge base file."
    kind = ToolKind.WRITE
    schema = CreateStartHereParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation before creating START_HERE.md"""
        params = CreateStartHereParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd
        start_here_path = repo_path / "START_HERE.md"

        if start_here_path.exists() and not params.force:
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"START_HERE.md already exists. Use force=true to overwrite.",
                affected_paths=[start_here_path],
            )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description="Create START_HERE.md file",
            affected_paths=[start_here_path],
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute create START_HERE.md command"""
        params = CreateStartHereParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            manager = RepositoryManager(repo_path)

            # Check if START_HERE.md exists
            if manager.start_here_path.exists() and not params.force:
                return ToolResult.error_result(
                    "START_HERE.md already exists. Use force=true to overwrite."
                )

            # Perform analysis and create START_HERE.md
            analysis = await manager.analyze()

            if manager.start_here_path.exists():
                return ToolResult.success_result(
                    f"Created START_HERE.md at: {manager.start_here_path}\n"
                    f"Repository analyzed and knowledge base generated."
                )
            else:
                return ToolResult.error_result("Failed to create START_HERE.md")

        except Exception as e:
            return ToolResult.error_result(f"Failed to create START_HERE.md: {e}")
