"""
Get PR Status Tool

Check the status of a GitHub pull request.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.github import GitHubClient


class GetPRStatusParams(BaseModel):
    """Parameters for getting PR status"""

    pr_number: int = Field(..., description="PR number")
    repo: str | None = Field(
        None,
        description="Repository in format 'owner/repo' (defaults to current repo)",
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class GetPRStatusTool(Tool):
    """Tool for checking GitHub PR status"""

    name = "get_pr_status"
    description = "Get the status of a GitHub pull request including state, review decision, and draft status."
    kind = ToolKind.NETWORK
    schema = GetPRStatusParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute get PR status command"""
        params = GetPRStatusParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

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
                    url = result.stdout.strip()
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

            # Get PR status
            status = github_client.get_pr_status(owner, repo, params.pr_number)

            # Format output
            output_lines = [
                f"PR #{params.pr_number} Status:",
                f"State: {status.get('state', 'unknown')}",
            ]

            if status.get("isDraft") is not None:
                output_lines.append(f"Draft: {status.get('isDraft', False)}")

            if status.get("reviewDecision"):
                output_lines.append(f"Review Decision: {status.get('reviewDecision')}")

            if status.get("url"):
                output_lines.append(f"URL: {status.get('url')}")

            return ToolResult.success_result("\n".join(output_lines))

        except Exception as e:
            return ToolResult.error_result(f"Failed to get PR status: {e}")
