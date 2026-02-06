"""
List Issues Tool

List repository issues from GitHub.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.github import GitHubClient


class ListIssuesParams(BaseModel):
    """Parameters for listing issues"""

    repo: str | None = Field(
        None,
        description="Repository in format 'owner/repo' (defaults to current repo)",
    )
    state: str = Field(
        "open", description="Issue state: 'open', 'closed', or 'all' (default: open)"
    )
    limit: int = Field(10, ge=1, le=100, description="Maximum number of issues (default: 10)")
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class ListIssuesTool(Tool):
    """Tool for listing GitHub repository issues"""

    name = "list_issues"
    description = "List issues from a GitHub repository. Can filter by state (open/closed/all)."
    kind = ToolKind.NETWORK
    schema = ListIssuesParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute list issues command"""
        params = ListIssuesParams(**invocation.params)
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

            # Validate state
            if params.state not in ["open", "closed", "all"]:
                return ToolResult.error_result(
                    f"Invalid state: {params.state}. Must be 'open', 'closed', or 'all'"
                )

            # List issues
            issues = await github_client.list_issues(
                owner=owner, repo=repo, state=params.state, limit=params.limit
            )

            if not issues:
                return ToolResult.success_result(
                    f"No {params.state} issues found in {repo_str}"
                )

            # Format output
            output_lines = [
                f"Found {len(issues)} {params.state} issue(s) in {repo_str}:",
                "",
            ]

            for issue in issues:
                output_lines.append(f"#{issue['number']}: {issue['title']}")
                output_lines.append(f"  State: {issue['state']}")
                if issue.get("labels"):
                    output_lines.append(f"  Labels: {', '.join(issue['labels'])}")
                if issue.get("url"):
                    output_lines.append(f"  URL: {issue['url']}")
                output_lines.append("")

            return ToolResult.success_result("\n".join(output_lines))

        except RuntimeError as e:
            return ToolResult.error_result(f"Failed to list issues: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Unexpected error: {e}")
