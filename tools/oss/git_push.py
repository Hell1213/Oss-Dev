"""
Git Push Tool

Push branches to remote with safety checks.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitPushParams(BaseModel):
    """Parameters for git push command"""

    branch: str | None = Field(
        None, description="Branch to push (defaults to current branch)"
    )
    remote: str = Field("origin", description="Remote name (default: origin)")
    force: bool = Field(
        False, description="Force push (use with caution, requires approval)"
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitPushTool(Tool):
    """Tool for pushing git branches"""

    name = "git_push"
    description = "Push a branch to remote. Supports force push with safety checks."
    kind = ToolKind.SHELL
    schema = GitPushParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation for push operations"""
        params = GitPushParams(**invocation.params)

        if params.force:
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Force push branch '{params.branch or 'current'}' to {params.remote}",
                is_dangerous=True,
                command=f"git push --force {params.remote} {params.branch or 'HEAD'}",
            )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Push branch '{params.branch or 'current'}' to {params.remote}",
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git push command"""
        params = GitPushParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        # CRITICAL: Check if user has confirmed push/PR operations
        # The agent MUST call user_confirm tool first and wait for confirmation
        if hasattr(invocation, 'session') and invocation.session:
            if not invocation.session.user_confirmed_push_pr:
                return ToolResult.error_result(
                    "❌ User confirmation required before pushing.\n\n"
                    "You MUST call 'user_confirm' tool first and wait for user to confirm 'YES' before calling git_push.\n\n"
                    "Correct sequence:\n"
                    "1. Call: user_confirm(message='Ready to push changes and create PR. Proceed?', default=True)\n"
                    "2. Wait for user response\n"
                    "3. Only if response is 'User confirmed: YES', then call git_push\n"
                    "4. DO NOT call git_push before user confirmation"
                )

        try:
            import git

            repo = git.Repo(repo_path)

            # Determine branch
            branch_name = params.branch or repo.active_branch.name

            # Safety check: don't force push to main/master
            if params.force and branch_name in ["main", "master"]:
                return ToolResult.error_result(
                    f"Cannot force push to protected branch '{branch_name}'"
                )

            # Check if remote exists
            if params.remote not in repo.remotes:
                return ToolResult.error_result(f"Remote '{params.remote}' does not exist")

            # Push
            if params.force:
                repo.git.push(params.remote, branch_name, force=True)
                return ToolResult.success_result(
                    f"Force pushed branch '{branch_name}' to {params.remote}"
                )
            else:
                repo.git.push(params.remote, branch_name)
                return ToolResult.success_result(
                    f"Pushed branch '{branch_name}' to {params.remote}"
                )

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            error_msg = str(e)
            if "force" in error_msg.lower() or "non-fast-forward" in error_msg.lower():
                return ToolResult.error_result(
                    f"Push failed: {error_msg}\n"
                    f"Hint: You may need to pull first or use force push (with approval)"
                )
            return ToolResult.error_result(f"Git push failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to push: {e}")
