"""
Fetch Issue Tool

Fetch GitHub issue details.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.github import GitHubClient


class FetchIssueParams(BaseModel):
    """Parameters for fetching a GitHub issue"""

    issue_url: str = Field(..., description="GitHub issue URL")
    path: str | None = Field(
        None,
        description="Path to git repository (defaults to current working directory)",
    )


class FetchIssueTool(Tool):
    """Tool for fetching GitHub issue details"""

    name = "fetch_issue"
    description = "Fetch details of a GitHub issue including title, body, labels, and status."
    kind = ToolKind.NETWORK
    schema = FetchIssueParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute fetch issue command"""
        params = FetchIssueParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        try:
            github_client = GitHubClient(self.config)

            # Fetch issue
            issue_data = await github_client.fetch_issue(params.issue_url)

            # Format output
            output_lines = [
                f"Issue #{issue_data['number']}: {issue_data['title']}",
                f"Status: {issue_data['state']}",
                f"URL: {issue_data['url']}",
                "",
                "Description:",
                issue_data.get("body", "No description"),
                "",
            ]

            if issue_data.get("labels"):
                output_lines.append(f"Labels: {', '.join(issue_data['labels'])}")

            return ToolResult.success_result("\n".join(output_lines))

        except ValueError as e:
            return ToolResult.error_result(f"Invalid issue URL: {e}")

        except RuntimeError as e:
            return ToolResult.error_result(f"Failed to fetch issue: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Unexpected error: {e}")
