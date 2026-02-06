"""
Check PR Comments Tool

Get comments from a GitHub pull request.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.github import GitHubClient


class CheckPRCommentsParams(BaseModel):
    """Parameters for checking PR comments"""

    pr_number: int = Field(..., description="PR number")
    repo: str | None = Field(
        None,
        description="Repository in format 'owner/repo' (defaults to current repo)",
    )
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class CheckPRCommentsTool(Tool):
    """Tool for checking GitHub PR comments"""

    name = "check_pr_comments"
    description = "Get comments from a GitHub pull request including review comments and discussion."
    kind = ToolKind.NETWORK
    schema = CheckPRCommentsParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute check PR comments command"""
        params = CheckPRCommentsParams(**invocation.params)
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

            # Get PR comments
            comments = await github_client.get_pr_comments(owner, repo, params.pr_number)

            if not comments:
                return ToolResult.success_result(
                    f"No comments found for PR #{params.pr_number}"
                )

            # Format output
            output_lines = [
                f"Found {len(comments)} comment(s) on PR #{params.pr_number}:",
                "",
            ]

            for i, comment in enumerate(comments, 1):
                output_lines.append(f"Comment #{i}:")
                output_lines.append(f"  Author: {comment.get('user', 'Unknown')}")
                if comment.get("created_at"):
                    output_lines.append(f"  Created: {comment['created_at']}")
                output_lines.append(f"  Body: {comment.get('body', 'No body')}")
                output_lines.append("")

            return ToolResult.success_result("\n".join(output_lines))

        except RuntimeError as e:
            return ToolResult.error_result(f"Failed to get PR comments: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Unexpected error: {e}")
