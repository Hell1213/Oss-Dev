"""
Git Merge Tool

Merge branches with safety checks.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitMergeParams(BaseModel):
    """Parameters for git merge command"""

    branch: str = Field(..., description="Branch to merge into current branch")
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitMergeTool(Tool):
    """Tool for merging git branches"""

    name = "git_merge"
    description = "Merge a branch into the current branch."
    kind = ToolKind.SHELL
    schema = GitMergeParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation for merge operation"""
        params = GitMergeParams(**invocation.params)

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Merge branch '{params.branch}' into current branch",
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git merge command"""
        params = GitMergeParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            # Check if branch exists
            if params.branch not in [ref.name for ref in repo.branches]:
                return ToolResult.error_result(f"Branch '{params.branch}' does not exist")

            current_branch = repo.active_branch.name

            # Don't merge branch into itself
            if params.branch == current_branch:
                return ToolResult.error_result("Cannot merge branch into itself")

            # Perform merge
            try:
                repo.git.merge(params.branch)
                return ToolResult.success_result(
                    f"Successfully merged '{params.branch}' into '{current_branch}'"
                )
            except git.exc.GitCommandError as e:
                error_msg = str(e)
                if "conflict" in error_msg.lower():
                    return ToolResult.error_result(
                        f"Merge conflict detected: {error_msg}\n"
                        f"Resolve conflicts manually, then commit the merge"
                    )
                raise

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git merge failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to merge: {e}")
