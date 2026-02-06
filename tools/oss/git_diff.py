"""
Git Diff Tool

Show differences in git repository.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitDiffParams(BaseModel):
    """Parameters for git diff command"""

    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )
    file: str | None = Field(
        None, description="Specific file to show diff for (optional)"
    )
    staged: bool = Field(False, description="Show staged changes (default: unstaged)")


class GitDiffTool(Tool):
    """Tool for showing git diffs"""

    name = "git_diff"
    description = "Show differences in git repository. Shows changes between working directory and index or HEAD."
    kind = ToolKind.READ
    schema = GitDiffParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git diff command"""
        params = GitDiffParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            if params.staged:
                # Show staged changes
                if params.file:
                    diff = repo.git.diff("--cached", params.file)
                else:
                    diff = repo.git.diff("--cached")
            else:
                # Show unstaged changes
                if params.file:
                    diff = repo.git.diff(params.file)
                else:
                    diff = repo.git.diff()

            if not diff:
                change_type = "staged" if params.staged else "unstaged"
                return ToolResult.success_result(f"No {change_type} changes")

            return ToolResult.success_result(diff)

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git diff failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to show diff: {e}")
