"""
Git Commit Tool

Create commits with proper messages.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class GitCommitParams(BaseModel):
    """Parameters for git commit command"""

    message: str = Field(..., description="Commit message")
    files: list[str] | None = Field(
        None,
        description="Specific files to commit (defaults to all staged files). Use empty list to commit all.",
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GitCommitTool(Tool):
    """Tool for creating git commits"""

    name = "git_commit"
    description = "Create a git commit with a message. Follows conventional commit format: type(scope): subject"
    kind = ToolKind.SHELL
    schema = GitCommitParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation before committing"""
        params = GitCommitParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]

            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Create commit: {params.message}",
                affected_paths=[repo_path / f for f in staged_files] if staged_files else [],
            )

        except Exception:
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Create commit: {params.message}",
            )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute git commit command"""
        params = GitCommitParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            import git

            repo = git.Repo(repo_path)

            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                return ToolResult.error_result("No changes to commit")

            # Stage files if specified
            if params.files is not None:
                if params.files:
                    # Stage specific files
                    for file_path in params.files:
                        full_path = repo_path / file_path
                        if full_path.exists():
                            repo.index.add([file_path])
                        else:
                            return ToolResult.error_result(f"File not found: {file_path}")
                # If empty list, stage all (already handled by commit)

            # Create commit
            commit = repo.index.commit(params.message)

            return ToolResult.success_result(
                f"Created commit: {commit.hexsha[:8]}\n"
                f"Message: {params.message}\n"
                f"Files: {len(commit.stats.files)} files changed"
            )

        except git.exc.InvalidGitRepositoryError:
            return ToolResult.error_result(f"Not a git repository: {repo_path}")

        except git.exc.GitCommandError as e:
            return ToolResult.error_result(f"Git commit failed: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to create commit: {e}")
