"""
Git Rebase Tool

Rebase branches with safety checks.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitRebaseParams(BaseModel):
    """Parameters for git rebase command"""

    branch: str = Field(..., description="Branch or commit to rebase onto")
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitRebaseTool(Tool):
    """Tool for rebasing git branches"""

    name = "git_rebase"
    description = "Rebase current branch onto another branch. Use with caution as it rewrites history."
    kind = ToolKind.SHELL
    schema = GitRebaseParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation for rebase operation"""
        params = GitRebaseParams(**invocation.params)

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Rebase current branch onto '{params.branch}'",
            is_dangerous=True,
            command=f"git rebase {params.branch}",
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git rebase command"""
        params = GitRebaseParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            # Safety check: don't rebase main/master
            current_branch = repo.active_branch.name
            if current_branch in ["main", "master"]:
                return ToolResult.error_result(
                    f"Cannot rebase protected branch '{current_branch}'"
                )

            # Check if target branch exists
            try:
                repo.git.show_ref(params.branch)
            except git.exc.GitCommandError:
                return ToolResult.error_result(f"Branch or commit '{params.branch}' does not exist")

            # Perform rebase
            try:
                repo.git.rebase(params.branch)
                return ToolResult.success_result(
                    f"Successfully rebased '{current_branch}' onto '{params.branch}'"
                )
            except git.exc.GitCommandError as e:
                error_msg = str(e)
                if "conflict" in error_msg.lower():
                    return ToolResult.error_result(
                        f"Rebase conflict detected: {error_msg}\n"
                        f"Resolve conflicts manually, then run 'git rebase --continue'"
                    )
                raise

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git rebase failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to rebase: {e}")
