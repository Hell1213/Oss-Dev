"""
Git Status Tool

Check the status of a git repository.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitStatusParams(BaseModel):
    """Parameters for git status command"""

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitStatusTool(Tool):
    """Tool for checking git repository status"""

    name = "git_status"
    description = "Check the status of a git repository. Shows modified, staged, and untracked files."
    kind = ToolKind.READ
    schema = GitStatusParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git status command"""
        params = GitStatusParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)
            status = repo.git.status()

            # Get additional info
            is_dirty = repo.is_dirty()
            untracked_files = repo.untracked_files
            modified_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]

            output_lines = [status]
            output_lines.append("\n--- Detailed Status ---")
            output_lines.append(f"Dirty: {is_dirty}")
            output_lines.append(f"Modified files: {len(modified_files)}")
            output_lines.append(f"Staged files: {len(staged_files)}")
            output_lines.append(f"Untracked files: {len(untracked_files)}")

            if modified_files:
                output_lines.append("\nModified:")
                for file in modified_files[:10]:  # Limit to 10
                    output_lines.append(f"  - {file}")
                if len(modified_files) > 10:
                    output_lines.append(f"  ... and {len(modified_files) - 10} more")

            if staged_files:
                output_lines.append("\nStaged:")
                for file in staged_files[:10]:
                    output_lines.append(f"  - {file}")
                if len(staged_files) > 10:
                    output_lines.append(f"  ... and {len(staged_files) - 10} more")

            if untracked_files:
                output_lines.append("\nUntracked:")
                for file in untracked_files[:10]:
                    output_lines.append(f"  - {file}")
                if len(untracked_files) > 10:
                    output_lines.append(f"  ... and {len(untracked_files) - 10} more")

            return ToolResult.success_result("\n".join(output_lines))

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to get git status: {e}")
