"""
Update START_HERE.md Tool

Update existing START_HERE.md with new information.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.repository import RepositoryManager


class UpdateStartHereParams(BaseModel):
    """Parameters for updating START_HERE.md"""

    path: str | None = Field(
        None,
        description="Path to repository (defaults to current working directory)",
    )
    section: str | None = Field(
        None,
        description="Specific section to update (optional, updates all if not specified)",
    )


class UpdateStartHereTool(Tool):
    """Tool for updating START_HERE.md"""

    name = "update_start_here"
    description = "Update START_HERE.md with fresh analysis. Only updates if repository structure has changed significantly."
    kind = ToolKind.WRITE
    schema = UpdateStartHereParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation before updating START_HERE.md"""
        params = UpdateStartHereParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd
        start_here_path = repo_path / "START_HERE.md"

        if not start_here_path.exists():
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description="START_HERE.md does not exist. Will create it instead.",
                affected_paths=[start_here_path],
            )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description="Update START_HERE.md with fresh analysis",
            affected_paths=[start_here_path],
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute update START_HERE.md command"""
        params = UpdateStartHereParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            manager = RepositoryManager(repo_path)

            # Check if START_HERE.md exists
            if not manager.start_here_path.exists():
                # Create it instead
                analysis = await manager.analyze()
                return ToolResult.success_result(
                    f"Created START_HERE.md at: {manager.start_here_path}\n"
                    f"(START_HERE.md did not exist, so it was created)"
                )

            # Perform fresh analysis
            analysis = await manager._perform_analysis()

            # Update START_HERE.md
            content = manager._generate_start_here_content(analysis)
            manager.start_here_path.write_text(content, encoding="utf-8")

            # Update cache
            manager._save_analysis_to_cache(analysis)

            return ToolResult.success_result(
                f"Updated START_HERE.md at: {manager.start_here_path}\n"
                f"Repository re-analyzed and knowledge base updated."
            )

        except Exception as e:
            return ToolResult.error_result(f"Failed to update START_HERE.md: {e}")
