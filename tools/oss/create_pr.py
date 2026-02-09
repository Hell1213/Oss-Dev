"""
Create PR Tool

Create a pull request on GitHub.
"""

from pathlib import Path
from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.github import GitHubClient


class CreatePRParams(BaseModel):
    """Parameters for creating a pull request"""

    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR body/description")
    head: str = Field(..., description="Source branch to create PR from")
    base: str = Field("main", description="Target branch (default: main)")
    repo: str | None = Field(
        None,
        description="Repository in format 'owner/repo' (defaults to current repo)",
    )
    issue_number: int | None = Field(
        None, description="Issue number to reference in PR (optional)"
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class CreatePRTool(Tool):
    """Tool for creating GitHub pull requests"""

    name = "create_pr"
    description = "Create a pull request on GitHub. Links to issue if issue_number is provided."
    kind = ToolKind.NETWORK
    schema = CreatePRParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        """Get confirmation before creating PR"""
        params = CreatePRParams(**invocation.params)

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Create PR: {params.title}",
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute create PR command"""
        params = CreatePRParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        # CRITICAL: Check if user has confirmed push/PR operations
        # The agent MUST call user_confirm tool first and wait for confirmation
        if hasattr(invocation, 'session') and invocation.session:
            if not invocation.session.user_confirmed_push_pr:
                return ToolResult.error_result(
                    "❌ User confirmation required before creating PR.\n\n"
                    "You MUST call 'user_confirm' tool first and wait for user to confirm 'YES' before calling create_pr.\n\n"
                    "Correct sequence:\n"
                    "1. Call: user_confirm(message='Ready to push changes and create PR. Proceed?', default=True)\n"
                    "2. Wait for user response\n"
                    "3. Only if response is 'User confirmed: YES', then call create_pr\n"
                    "4. DO NOT call create_pr before user confirmation"
                )

        try:
            github_client = GitHubClient(self.config)

            # Determine repository
            if not params.repo:
                # Try to get repo from git remote
                import subprocess
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    # Parse git URL to get owner/repo
                    url = result.stdout.strip()
                    # Handle both https://github.com/owner/repo.git and git@github.com:owner/repo.git
                    if "github.com" in url:
                        parts = url.replace(".git", "").split("github.com/")[-1].split("/")
                        if len(parts) >= 2:
                            owner, repo = parts[0], parts[1]
                            repo_str = f"{owner}/{repo}"
                        else:
                            return ToolResult.error_result(
                                "Could not determine repository. Please provide 'repo' parameter."
                            )
                    else:
                        return ToolResult.error_result(
                            "Not a GitHub repository. Please provide 'repo' parameter."
                        )
                except (subprocess.CalledProcessError, IndexError):
                    return ToolResult.error_result(
                        "Could not determine repository. Please provide 'repo' parameter."
                    )
            else:
                repo_str = params.repo

            # Parse owner and repo
            if "/" not in repo_str:
                return ToolResult.error_result(
                    "Repository must be in format 'owner/repo'"
                )
            owner, repo = repo_str.split("/", 1)

            # Enhance PR body with issue reference if provided
            pr_body = params.body
            if params.issue_number:
                pr_body = f"{pr_body}\n\nFixes #{params.issue_number}"

            # Create PR
            pr_data = await github_client.create_pr(
                owner=owner,
                repo=repo,
                title=params.title,
                body=pr_body,
                head=params.head,
                base=params.base,
            )

            return ToolResult.success_result(
                f"Created PR #{pr_data['number']}: {pr_data['title']}\n"
                f"URL: {pr_data['url']}"
            )

        except RuntimeError as e:
            return ToolResult.error_result(f"Failed to create PR: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Unexpected error: {e}")
