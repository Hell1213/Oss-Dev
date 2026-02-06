"""
Check START_HERE.md Tool

Check if START_HERE.md exists and show its contents.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class CheckStartHereParams(BaseModel):
    """Parameters for checking START_HERE.md"""

    path: str | None = Field(
        None,
        description="Path to repository (defaults to current working directory)",
    )


class CheckStartHereTool(Tool):
    """Tool for checking START_HERE.md"""

    name = "check_start_here"
    description = "Check if START_HERE.md exists in the repository and display its contents."
    kind = ToolKind.READ
    schema = CheckStartHereParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute check START_HERE.md command"""
        params = CheckStartHereParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        start_here_path = repo_path / "START_HERE.md"

        if not start_here_path.exists():
            return ToolResult.success_result(
                "START_HERE.md does not exist.\n"
                "Use 'create_start_here' tool to generate it."
            )

        try:
            content = start_here_path.read_text(encoding="utf-8")
            return ToolResult.success_result(
                f"START_HERE.md exists at: {start_here_path}\n\n"
                f"Contents:\n{content}"
            )
        except Exception as e:
            return ToolResult.error_result(f"Failed to read START_HERE.md: {e}")
