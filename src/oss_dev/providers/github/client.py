"""GitHub provider implementation.

Primary: GitHub CLI (gh)
Fallback: REST API (future)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

from oss_dev.core.contracts.provider import (
    Comment,
    GitHubProvider,
    Issue,
    PRStatus,
    PullRequest,
)
from oss_dev.core.errors import ProviderError
from oss_dev.config.models import Config

LOW_RATE_LIMIT_THRESHOLD = 10


class GitHubCLIProvider(GitHubProvider):
    """GitHub provider using the gh CLI tool."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._gh_available = self._check_gh()

    def _check_gh(self) -> bool:
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _require_gh(self) -> None:
        if not self._gh_available:
            raise ProviderError(
                "GitHub CLI (gh) is required. Install: https://cli.github.com/",
                details={"hint": "sudo apt install gh && gh auth login"},
            )

    def _format_rate_limit_reset(self, reset: Any) -> str | None:
        try:
            reset_timestamp = int(reset)
        except (TypeError, ValueError):
            return None

        return datetime.fromtimestamp(
            reset_timestamp,
            tz=timezone.utc,
        ).isoformat()

    def _get_rate_limit(self) -> dict[str, Any] | None:
        try:
            result = subprocess.run(
                ["gh", "api", "rate_limit"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        resources = payload.get("resources")
        if not isinstance(resources, dict):
            return None

        core = resources.get("core")
        if not isinstance(core, dict):
            return None

        return core

    def _check_rate_limit(self) -> None:
        rate_limit = self._get_rate_limit()
        if not rate_limit:
            return

        try:
            remaining = int(rate_limit["remaining"])
        except (KeyError, TypeError, ValueError):
            return

        reset_time = self._format_rate_limit_reset(rate_limit.get("reset"))

        if remaining <= 0:
            details: dict[str, Any] = {"remaining": remaining}
            if reset_time:
                details["reset_time"] = reset_time

            message = "GitHub API rate limit exceeded."
            if reset_time:
                message = f"{message} Resets at {reset_time}."

            raise ProviderError(message, details=details)

        if remaining <= LOW_RATE_LIMIT_THRESHOLD:
            warning = f"Warning: GitHub API rate limit is low ({remaining} requests remaining)."
            if reset_time:
                warning = f"{warning} Resets at {reset_time}."
            print(warning, file=sys.stderr)

    def _run_gh(self, args: list[str]) -> str:
        self._require_gh()
        is_api_call = len(args) >= 2 and args[0] == "api"
        endpoint = args[1] if len(args) >= 2 else None

        if is_api_call and endpoint != "rate_limit":
            self._check_rate_limit()

        try:
            result = subprocess.run(
                ["gh", *args],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_text = e.stderr.strip() or e.stdout.strip()
            details: dict[str, Any] = {"args": args}

            if "rate limit" in error_text.lower():
                rate_limit = self._get_rate_limit() if endpoint != "rate_limit" else None
                reset_time = self._format_rate_limit_reset(
                    rate_limit.get("reset") if rate_limit else None
                )
                if reset_time:
                    details["reset_time"] = reset_time
                if rate_limit and "remaining" in rate_limit:
                    details["remaining"] = rate_limit["remaining"]

                message = "GitHub API rate limit exceeded."
                if reset_time:
                    message = f"{message} Resets at {reset_time}."
                if error_text:
                    details["error"] = error_text
                raise ProviderError(message, details=details) from e

            raise ProviderError(
                f"GitHub CLI error: {error_text}",
                details=details,
            ) from e

    def parse_issue_url(self, url: str) -> dict[str, Any]:
        pattern = r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
        match = re.search(pattern, url)
        if not match:
            raise ProviderError(f"Invalid GitHub issue URL: {url}")
        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "issue_number": int(match.group(3)),
        }

    async def fetch_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        output = self._run_gh([
            "api",
            f"repos/{owner}/{repo}/issues/{issue_number}",
            "--jq",
            "{title: .title, body: .body, state: .state, labels: [.labels[].name], number: .number}",
        ])
        data = json.loads(output)
        return Issue(
            number=data.get("number", issue_number),
            title=data.get("title", ""),
            body=data.get("body", ""),
            state=data.get("state", "open"),
            labels=data.get("labels", []),
            url=f"https://github.com/{owner}/{repo}/issues/{issue_number}",
            owner=owner,
            repo=repo,
        )

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 10
    ) -> list[Issue]:
        output = self._run_gh([
            "api",
            f"repos/{owner}/{repo}/issues",
            "--jq",
            f".[:{limit}] | .[] | {{title: .title, number: .number, state: .state, labels: [.labels[].name], url: .html_url}}",
        ])
        issues = []
        for line in output.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                issues.append(
                    Issue(
                        number=data.get("number", 0),
                        title=data.get("title", ""),
                        body="",
                        state=data.get("state", "open"),
                        labels=data.get("labels", []),
                        url=data.get("url", ""),
                        owner=owner,
                        repo=repo,
                    )
                )
        return issues[:limit]

    async def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> PullRequest:
        output = self._run_gh([
            "pr",
            "create",
            "--repo", f"{owner}/{repo}",
            "--title", title,
            "--body", body,
            "--head", head,
            "--base", base,
            "--json", "url,number,title",
        ])
        data = json.loads(output)
        return PullRequest(
            url=data.get("url", ""),
            number=data.get("number", 0),
            title=data.get("title", title),
        )

    async def get_pr_status(
        self, owner: str, repo: str, pr_number: int
    ) -> PRStatus:
        output = self._run_gh([
            "pr", "view", str(pr_number),
            "--repo", f"{owner}/{repo}",
            "--json", "state,isDraft,reviewDecision,url",
        ])
        data = json.loads(output)
        return PRStatus(
            state=data.get("state", "unknown"),
            is_draft=data.get("isDraft", False),
            review_decision=data.get("reviewDecision"),
            url=data.get("url", ""),
        )

    async def get_pr_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[Comment]:
        output = self._run_gh([
            "api",
            f"repos/{owner}/{repo}/pulls/{pr_number}/comments",
            "--jq",
            ".[] | {body: .body, user: .user.login, created_at: .created_at}",
        ])
        comments = []
        for line in output.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                comments.append(
                    Comment(
                        body=data.get("body", ""),
                        user=data.get("user", ""),
                        created_at=data.get("created_at", ""),
                    )
                )
        return comments
