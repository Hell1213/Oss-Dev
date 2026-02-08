"""
Git Branch Tool

Create, switch, list, and delete git branches.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitBranchParams(BaseModel):
    """Parameters for git branch operations"""

    action: str = Field(
        ...,
        description="Action to perform: 'create', 'switch', 'list', 'delete', or 'current'",
    )
    branch_name: str | None = Field(
        None, description="Branch name (required for create, switch, delete)"
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitBranchTool(Tool):
    """Tool for git branch operations"""

    name = "git_branch"
    description = "Create, switch, list, or delete git branches. Supports branch management operations."
    kind = ToolKind.SHELL
    schema = GitBranchParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation for destructive operations"""
        params = GitBranchParams(**invocation.params)

        if params.action == "delete":
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Delete branch '{params.branch_name}'",
                is_dangerous=True,
            )

        return None

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git branch operation"""
        params = GitBranchParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            if params.action == "create":
                if not params.branch_name:
                    return ToolResult.error_result("Branch name required for create action")

                # Safety check: don't create branches with dangerous names
                if params.branch_name in ["main", "master", "HEAD"]:
                    return ToolResult.error_result(
                        f"Cannot create branch '{params.branch_name}': protected branch name"
                    )

                # Check if branch already exists
                if params.branch_name in [ref.name for ref in repo.branches]:
                    return ToolResult.error_result(f"Branch '{params.branch_name}' already exists")

                new_branch = repo.create_head(params.branch_name)
                # Switch to the new branch after creating it
                repo.git.checkout(params.branch_name)
                return ToolResult.success_result(
                    f"Created and switched to branch '{params.branch_name}'\n"
                    f"Current branch: {repo.active_branch.name}"
                )

            elif params.action == "switch":
                if not params.branch_name:
                    return ToolResult.error_result("Branch name required for switch action")

                # Check if branch exists
                if params.branch_name not in [ref.name for ref in repo.branches]:
                    return ToolResult.error_result(f"Branch '{params.branch_name}' does not exist")

                repo.git.checkout(params.branch_name)
                return ToolResult.success_result(
                    f"Switched to branch '{params.branch_name}'"
                )

            elif params.action == "list":
                branches = [ref.name for ref in repo.branches]
                current = repo.active_branch.name

                output_lines = ["Branches:"]
                for branch in branches:
                    marker = "* " if branch == current else "  "
                    output_lines.append(f"{marker}{branch}")

                return ToolResult.success_result("\n".join(output_lines))

            elif params.action == "delete":
                if not params.branch_name:
                    return ToolResult.error_result("Branch name required for delete action")

                # Safety check: don't delete main/master
                if params.branch_name in ["main", "master"]:
                    return ToolResult.error_result(
                        f"Cannot delete branch '{params.branch_name}': protected branch"
                    )

                # Check if branch exists
                if params.branch_name not in [ref.name for ref in repo.branches]:
                    return ToolResult.error_result(f"Branch '{params.branch_name}' does not exist")

                # Don't delete current branch
                if params.branch_name == repo.active_branch.name:
                    return ToolResult.error_result(
                        f"Cannot delete current branch '{params.branch_name}'. Switch to another branch first."
                    )

                repo.delete_head(params.branch_name, force=False)
                return ToolResult.success_result(f"Deleted branch '{params.branch_name}'")

            elif params.action == "current":
                current = repo.active_branch.name
                return ToolResult.success_result(f"Current branch: {current}")

            else:
                return ToolResult.error_result(
                    f"Unknown action: {params.action}. "
                    f"Valid actions: create, switch, list, delete, current"
                )

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git command failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to perform branch operation: {e}")
