"""
Git Fetch Tool

Fetch from remote repositories.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitFetchParams(BaseModel):
    """Parameters for git fetch command"""

    remote: str = Field("origin", description="Remote name (default: origin)")
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitFetchTool(Tool):
    """Tool for fetching from git remotes"""

    name = "git_fetch"
    description = "Fetch latest changes from a remote repository without merging."
    kind = ToolKind.READ
    schema = GitFetchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git fetch command"""
        params = GitFetchParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            # Check if remote exists
            if params.remote not in repo.remotes:
                return ToolResult.error_result(f"Remote '{params.remote}' does not exist")

            # Fetch
            repo.remote(params.remote).fetch()

            # Get info about what was fetched
            remote_refs = [ref.name for ref in repo.remote(params.remote).refs]

            return ToolResult.success_result(
                f"Fetched from {params.remote}\n"
                f"Remote branches: {len(remote_refs)}"
            )

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git fetch failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to fetch: {e}")
