"""
GitHub API Integration

Provides GitHub API client functionality using GitHub CLI (gh) as primary method,
with fallback to GitHub API when needed.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from config.config import Config


class GitHubClient:
    """
    GitHub API client using GitHub CLI (gh) as primary method.

    Falls back to direct API calls if GitHub CLI is not available.
    """

    def __init__(self, config: Config):
        """
        Initialize GitHub client.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._gh_available = self._check_gh_available()

    def _check_gh_available(self) -> bool:
        """Check if GitHub CLI is available."""
        try:
            subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def parse_issue_url(self, issue_url: str) -> dict[str, Any]:
        """
        Parse GitHub issue URL to extract owner, repo, and issue number.

        Args:
            issue_url: GitHub issue URL

        Returns:
            Dictionary with owner, repo, and issue_number
        """
        # Pattern: https://github.com/owner/repo/issues/123
        pattern = r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
        match = re.search(pattern, issue_url)

        if not match:
            raise ValueError(f"Invalid GitHub issue URL: {issue_url}. Ensure it follows the format: https://github.com/owner/repo/issues/number. Refer to GitHub documentation for help.")

        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "issue_number": int(match.group(3)),
        }

    async def fetch_issue(
        self, issue_url: str, issue_number: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Fetch issue details from GitHub.

        Args:
            issue_url: GitHub issue URL
            issue_number: Issue number (optional, will be parsed from URL)

        Returns:
            Issue data dictionary
        """
        if not issue_number:
            parsed = self.parse_issue_url(issue_url)
            issue_number = parsed["issue_number"]
            owner = parsed["owner"]
            repo = parsed["repo"]
        else:
            parsed = self.parse_issue_url(issue_url)
            owner = parsed["owner"]
            repo = parsed["repo"]

        if self._gh_available:
            return await self._fetch_issue_via_gh(owner, repo, issue_number)
        else:
            return await self._fetch_issue_via_api(owner, repo, issue_number)

    async def _fetch_issue_via_gh(
        self, owner: str, repo: str, issue_number: int
    ) -> dict[str, Any]:
        """
        Fetch issue using GitHub CLI.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue data dictionary
        """
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{repo}/issues/{issue_number}",
                    "--jq",
                    "{title: .title, body: .body, state: .state, labels: [.labels[].name], number: .number}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            issue_data = json.loads(result.stdout)

            return {
                "title": issue_data.get("title", ""),
                "body": issue_data.get("body", ""),
                "state": issue_data.get("state", "open"),
                "labels": issue_data.get("labels", []),
                "number": issue_data.get("number", issue_number),
                "url": f"https://github.com/{owner}/{repo}/issues/{issue_number}",
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to fetch issue via GitHub CLI: {e}. This might be due to authentication issues or the CLI may not be installed. Please verify your CLI setup.")

    async def _fetch_issue_via_api(
        self, owner: str, repo: str, issue_number: int
    ) -> dict[str, Any]:
        """
        Fetch issue using GitHub API directly.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue data dictionary
        """
        github_token = self.config.github_token
        if not github_token:
            raise RuntimeError(
                "GitHub token required when GitHub CLI is not available. "
                "Set GITHUB_TOKEN environment variable or install GitHub CLI (gh)."
            )

        # This would use httpx or requests to call GitHub API
        # For now, raise an error to encourage using GitHub CLI
        # Placeholder for future API calls to GitHub.
            raise NotImplementedError(
            "Direct GitHub API calls not yet implemented. "
            "Please install GitHub CLI: sudo apt install gh && gh auth login"
        )

    async def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """
        Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR body
            head: Source branch
            base: Target branch (default: main)

        Returns:
            PR data dictionary with URL
        """
        if self._gh_available:
            return await self._create_pr_via_gh(owner, repo, title, body, head, base)
        else:
            return await self._create_pr_via_api(owner, repo, title, body, head, base)

    async def _create_pr_via_gh(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Create PR using GitHub CLI."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    f"{owner}/{repo}",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--head",
                    head,
                    "--base",
                    base,
                    "--json",
                    "url,number,title",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            import json
            pr_data = json.loads(result.stdout)

            return {
                "url": pr_data.get("url", ""),
                "number": pr_data.get("number", 0),
                "title": pr_data.get("title", title),
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to create PR via GitHub CLI: {e}. Make sure the repository exists and that you have appropriate permissions to access it.")

    async def _create_pr_via_api(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Create PR using GitHub API directly."""
        # Placeholder for future API calls to GitHub.
            raise NotImplementedError(
            "Direct GitHub API calls not yet implemented. "
            "Please install GitHub CLI: sudo apt install gh && gh auth login"
        )

    def get_pr_status(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """
        Get PR status.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            PR status dictionary
        """
        if self._gh_available:
            try:
                result = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "view",
                        str(pr_number),
                        "--repo",
                        f"{owner}/{repo}",
                        "--json",
                        "state,isDraft,reviewDecision,url",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                import json
                return json.loads(result.stdout)
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                return {"state": "unknown"}

        return {"state": "unknown"}

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        List repository issues.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all) - default: open
            limit: Maximum number of issues to return - default: 10

        Returns:
            List of issue dictionaries
        """
        if self._gh_available:
            return await self._list_issues_via_gh(owner, repo, state, limit)
        else:
            return await self._list_issues_via_api(owner, repo, state, limit)

    async def _list_issues_via_gh(
        self, owner: str, repo: str, state: str, limit: int
    ) -> list[dict[str, Any]]:
        """List issues using GitHub CLI."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{repo}/issues",
                    "--jq",
                    f".[:{limit}] | .[] | {{title: .title, number: .number, state: .state, labels: [.labels[].name], url: .html_url}}",
                    "--paginate",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            import json
            # Parse line-delimited JSON
            issues = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    issues.append(json.loads(line))
            return issues[:limit]

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to list issues via GitHub CLI: {e}. This may be related to network connectivity or GitHub CLI authentication issues.")

    async def _list_issues_via_api(
        self, owner: str, repo: str, state: str, limit: int
    ) -> list[dict[str, Any]]:
        """List issues using GitHub API directly."""
        # Placeholder for future API calls to GitHub.
            raise NotImplementedError(
            "Direct GitHub API calls not yet implemented. "
            "Please install GitHub CLI: sudo apt install gh && gh auth login"
        )

    async def get_pr_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """
        Get PR comments.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            List of comment dictionaries
        """
        if self._gh_available:
            return await self._get_pr_comments_via_gh(owner, repo, pr_number)
        else:
            return await self._get_pr_comments_via_api(owner, repo, pr_number)

    async def _get_pr_comments_via_gh(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Get PR comments using GitHub CLI."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{repo}/pulls/{pr_number}/comments",
                    "--jq",
                    ".[] | {body: .body, user: .user.login, created_at: .created_at}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            import json
            comments = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    comments.append(json.loads(line))
            return comments

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to get PR comments via GitHub CLI: {e}. Please check your internet connection and ensure that the CLI is properly authenticated.")

    async def _get_pr_comments_via_api(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Get PR comments using GitHub API directly."""
        # Placeholder for future API calls to GitHub.
            raise NotImplementedError(
            "Direct GitHub API calls not yet implemented. "
            "Please install GitHub CLI: sudo apt install gh && gh auth login"
        )
