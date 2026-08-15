"""Contributor activity leaderboard system.

Fetches and aggregates contributor activity metrics from GitHub API
(issues resolved, PRs merged, reviews, docs contributions) and ranks
contributors for public recognition and motivation.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardMetrics:
  """Aggregated metrics for a single contributor."""

  login: str
  avatar_url: str
  issues_resolved: int = 0
  prs_merged: int = 0
  review_comments: int = 0
  docs_commits: int = 0
  total_points: int = 0

  def calculate_points(self) -> int:
    """Calculate total points from metrics using weighted system.

    Points are weighted to encourage diverse contributions:
    - Issues resolved: 10 points each
    - PRs merged: 15 points each
    - Code reviews: 5 points each
    - Documentation: 20 points each

    Returns:
      Total weighted points
    """
    self.total_points = (
        self.issues_resolved * 10
        + self.prs_merged * 15
        + self.review_comments * 5
        + self.docs_commits * 20
    )
    return self.total_points

  def to_dict(self) -> dict[str, Any]:
    """Convert metrics to dictionary."""
    return {
        "login": self.login,
        "avatar_url": self.avatar_url,
        "points": self.total_points,
        "breakdown": {
            "issues_resolved": self.issues_resolved,
            "prs_merged": self.prs_merged,
            "review_comments": self.review_comments,
            "docs_commits": self.docs_commits,
        },
    }


class LeaderboardGenerator:
  """Generates contributor leaderboards from GitHub API data."""

  def __init__(self, github_token: str, cache_duration_hours: int = 1):
    """Initialize leaderboard generator.

    Args:
      github_token: GitHub personal access token
      cache_duration_hours: How long to cache results

    Raises:
      ValueError: If github_token is not provided
    """
    if not github_token:
      raise ValueError("GITHUB_TOKEN is required")

    self.token = github_token
    self.headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    self.base_url = "https://api.github.com"
    self.cache_duration = timedelta(hours=cache_duration_hours)
    self.last_fetch = None
    self.cache: dict[str, Any] = {}

  def _is_cache_valid(self) -> bool:
    """Check if cached data is still valid."""
    if not self.last_fetch:
      return False

    return datetime.now() - self.last_fetch < self.cache_duration

  def get_closed_issues(
      self, repo: str, since: datetime | None = None, max_pages: int = 5
  ) -> list[dict[str, Any]]:
    """Fetch closed issues from repository.

    Args:
      repo: Repository in "owner/repo" format
      since: Only get issues closed after this date
      max_pages: Maximum pages to fetch (prevents infinite loops)

    Returns:
      List of closed issues

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/issues"
      params: dict[str, str | int] = {"state": "closed", "per_page": 100}

      if since:
        params["since"] = since.isoformat()

      issues = []
      page = 1

      while page <= max_pages:
        params["page"] = page
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        page_issues = response.json()
        if not page_issues:
          break

        issues.extend(page_issues)
        page += 1

      return issues

    except requests.RequestException as e:
      logger.error(f"Failed to fetch issues from {repo}: {e}")
      raise

  def get_merged_prs(
      self, repo: str, since: datetime | None = None, max_pages: int = 5
  ) -> list[dict[str, Any]]:
    """Fetch merged pull requests from repository.

    Args:
      repo: Repository in "owner/repo" format
      since: Only get PRs merged after this date
      max_pages: Maximum pages to fetch (prevents infinite loops)

    Returns:
      List of merged pull requests

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/pulls"
      params: dict[str, str | int] = {"state": "closed", "per_page": 100}

      prs = []
      page = 1

      while page <= max_pages:
        params["page"] = page
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        page_prs = response.json()
        if not page_prs:
          break

        # Filter for only merged PRs
        for pr in page_prs:
          if pr.get("merged_at"):
            if since is None or datetime.fromisoformat(
                pr["merged_at"].replace("Z", "+00:00")
            ) > since:
              prs.append(pr)

        page += 1

      return prs

    except requests.RequestException as e:
      logger.error(f"Failed to fetch PRs from {repo}: {e}")
      raise

  def get_code_reviews(
      self, repo: str, since: datetime | None = None, max_pages: int = 5
  ) -> dict[str, int]:
    """Fetch code review comments by contributor.

    Args:
      repo: Repository in "owner/repo" format
      since: Only count reviews after this date
      max_pages: Maximum pages to fetch (prevents infinite loops)

    Returns:
      Dictionary mapping login to review comment count

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/pulls/comments"
      params = {"per_page": 100}

      review_counts: dict[str, int] = {}
      page = 1

      while page <= max_pages:
        params["page"] = page
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        comments = response.json()
        if not comments:
          break

        for comment in comments:
          if comment.get("user"):
            login = comment["user"]["login"]
            review_counts[login] = review_counts.get(login, 0) + 1

        page += 1

      return review_counts

    except requests.RequestException as e:
      logger.error(f"Failed to fetch code reviews from {repo}: {e}")
      return {}

  def get_docs_contributions(
      self, repo: str, since: datetime | None = None, max_pages: int = 5
  ) -> dict[str, int]:
    """Fetch documentation contributions by counting commits to docs files.

    Args:
      repo: Repository in "owner/repo" format
      since: Only count commits after this date
      max_pages: Maximum pages to fetch (prevents infinite loops)

    Returns:
      Dictionary mapping login to docs commit count

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/commits"
      params: dict[str, str | int] = {"per_page": 100, "path": "docs/"}

      docs_counts: dict[str, int] = {}
      page = 1

      while page <= max_pages:
        params["page"] = page
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        commits = response.json()
        if not commits:
          break

        for commit in commits:
          author = commit.get("commit", {}).get("author")
          if author and author.get("name"):
            # Try to get GitHub login from commit
            if commit.get("author", {}).get("login"):
              login = commit["author"]["login"]
              docs_counts[login] = docs_counts.get(login, 0) + 1

        page += 1

      return docs_counts

    except requests.RequestException as e:
      logger.error(f"Failed to fetch docs contributions from {repo}: {e}")
      return {}

  def generate_leaderboard(
      self, repo: str, time_window: str = "all-time", top_n: int = 20
  ) -> list[LeaderboardMetrics]:
    """Generate leaderboard for a repository.

    Args:
      repo: Repository in "owner/repo" format
      time_window: Time period ("weekly", "monthly", "all-time")
      top_n: Number of top contributors to return

    Returns:
      List of top contributors ranked by points

    Raises:
      ValueError: If time_window is invalid
      requests.RequestException: If API requests fail
    """
    if time_window not in ("weekly", "monthly", "all-time"):
      raise ValueError(f"Invalid time_window: {time_window}")

    # Determine since date based on time_window
    since = None
    if time_window == "weekly":
      since = datetime.now() - timedelta(days=7)
    elif time_window == "monthly":
      since = datetime.now() - timedelta(days=30)

    logger.info(f"Generating leaderboard for {repo} (time_window={time_window})")

    # Fetch all metrics
    issues = self.get_closed_issues(repo, since)
    prs = self.get_merged_prs(repo, since)
    reviews = self.get_code_reviews(repo, since)
    docs = self.get_docs_contributions(repo, since)

    # Aggregate metrics by contributor
    metrics: dict[str, LeaderboardMetrics] = {}

    # Count issues resolved by closer
    for issue in issues:
      if issue.get("closed_by"):
        login = issue["closed_by"].get("login")
        if login:
          if login not in metrics:
            metrics[login] = LeaderboardMetrics(
                login=login,
                avatar_url=issue["closed_by"].get("avatar_url", ""),
            )
          metrics[login].issues_resolved += 1

    # Count PRs merged
    for pr in prs:
      if pr.get("merged_by"):
        login = pr["merged_by"].get("login")
        if login:
          if login not in metrics:
            metrics[login] = LeaderboardMetrics(
                login=login,
                avatar_url=pr["merged_by"].get("avatar_url", ""),
            )
          metrics[login].prs_merged += 1

    # Add review comments
    for login, count in reviews.items():
      if login not in metrics:
        metrics[login] = LeaderboardMetrics(
            login=login,
            avatar_url="",
        )
      metrics[login].review_comments = count

    # Add docs contributions
    for login, count in docs.items():
      if login not in metrics:
        metrics[login] = LeaderboardMetrics(
            login=login,
            avatar_url="",
        )
      metrics[login].docs_commits = count

    # Calculate points and sort
    for metric in metrics.values():
      metric.calculate_points()

    sorted_leaderboard = sorted(
        metrics.values(), key=lambda m: m.total_points, reverse=True
    )

    return sorted_leaderboard[:top_n]

  def get_leaderboard_json(
      self, repo: str, time_window: str = "all-time", top_n: int = 20
  ) -> str:
    """Generate leaderboard as JSON string.

    Args:
      repo: Repository in "owner/repo" format
      time_window: Time period ("weekly", "monthly", "all-time")
      top_n: Number of top contributors to return

    Returns:
      JSON string with leaderboard data
    """
    leaderboard = self.generate_leaderboard(repo, time_window, top_n)

    data = {
        "repository": repo,
        "time_window": time_window,
        "generated_at": datetime.now().isoformat(),
        "total_contributors": len(leaderboard),
        "leaderboard": [metric.to_dict() for metric in leaderboard],
    }

    return json.dumps(data, indent=2)


def get_leaderboard_generator() -> LeaderboardGenerator:
  """Create a leaderboard generator from environment variables.

  Returns:
    Initialized LeaderboardGenerator

  Raises:
    ValueError: If GITHUB_TOKEN is not set
  """
  token = os.getenv("GITHUB_TOKEN")
  if not token:
    raise ValueError("GITHUB_TOKEN environment variable is required")

  return LeaderboardGenerator(token)
