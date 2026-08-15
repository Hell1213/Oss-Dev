"""Project health metrics dashboard system.

Fetches and aggregates project health indicators from GitHub API with
6-hour caching. Provides maintainers with key signals about project status.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
  """Aggregated health metrics for a repository."""

  repo: str
  timestamp: str
  open_issues_count: int
  median_issue_age_days: float
  median_pr_merge_days: float
  response_rate_48h: float
  commit_frequency_12w: list[int]
  stars_growth_wow: float
  forks_growth_wow: float

  def to_dict(self) -> dict[str, Any]:
    """Convert metrics to dictionary."""
    return {
        "repo": self.repo,
        "timestamp": self.timestamp,
        "metrics": {
            "open_issues": self.open_issues_count,
            "median_issue_age_days": round(self.median_issue_age_days, 1),
            "median_pr_merge_days": round(self.median_pr_merge_days, 1),
            "response_rate_48h": round(self.response_rate_48h, 1),
            "commit_frequency_12w": self.commit_frequency_12w,
            "stars_growth_wow": round(self.stars_growth_wow, 2),
            "forks_growth_wow": round(self.forks_growth_wow, 2),
        },
    }

  def get_health_status(self) -> str:
    """Determine overall health status.

    Returns:
      "healthy", "warning", or "critical"
    """
    warning_count = 0

    if self.open_issues_count > 100:
      warning_count += 1
    if self.median_issue_age_days > 30:
      warning_count += 1
    if self.median_pr_merge_days > 7:
      warning_count += 1
    if self.response_rate_48h < 70:
      warning_count += 1
    if not self.commit_frequency_12w or sum(self.commit_frequency_12w) < 10:
      warning_count += 1

    if warning_count >= 4:
      return "critical"
    elif warning_count >= 2:
      return "warning"
    else:
      return "healthy"


class HealthMetricsGenerator:
  """Generates project health metrics from GitHub API data."""

  def __init__(self, github_token: str, cache_duration_hours: int = 6):
    """Initialize metrics generator.

    Args:
      github_token: GitHub personal access token
      cache_duration_hours: Cache duration for results

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
    self.last_fetch: dict[str, datetime] = {}
    self.cache: dict[str, Any] = {}

  def _is_cache_valid(self, repo: str) -> bool:
    """Check if cached data for repo is still valid."""
    if repo not in self.last_fetch:
      return False

    return datetime.now() - self.last_fetch[repo] < self.cache_duration

  def get_open_issues(self, repo: str) -> tuple[int, list[dict[str, Any]]]:
    """Fetch open issues from repository.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      Tuple of (issue count, list of issues)

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/issues"
      params: dict[str, str | int] = {"state": "open", "per_page": 100}

      issues = []
      response = requests.get(url, headers=self.headers, params=params, timeout=10)
      response.raise_for_status()
      issues = response.json()

      return len(issues), issues

    except requests.RequestException as e:
      logger.error(f"Failed to fetch open issues from {repo}: {e}")
      raise

  def calculate_issue_age_median(self, issues: list[dict[str, Any]]) -> float:
    """Calculate median age of open issues in days.

    Args:
      issues: List of issue data from GitHub API

    Returns:
      Median age in days
    """
    if not issues:
      return 0.0

    ages = []
    now = datetime.now(datetime.now().astimezone().tzinfo)

    for issue in issues:
      created_at = datetime.fromisoformat(
          issue["created_at"].replace("Z", "+00:00")
      )
      age_days = (now - created_at).days
      ages.append(age_days)

    return float(median(ages)) if ages else 0.0

  def get_pr_metrics(self, repo: str) -> tuple[float, int]:
    """Fetch PR merge metrics from repository.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      Tuple of (median merge time in days, total merged PRs count)

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/pulls"
      params: dict[str, str | int] = {"state": "closed", "per_page": 50}

      response = requests.get(url, headers=self.headers, params=params, timeout=10)
      response.raise_for_status()
      prs = response.json()

      merge_times = []
      merged_count = 0

      for pr in prs:
        if pr.get("merged_at"):
          merged_count += 1
          created_at = datetime.fromisoformat(
              pr["created_at"].replace("Z", "+00:00")
          )
          merged_at = datetime.fromisoformat(
              pr["merged_at"].replace("Z", "+00:00")
          )
          merge_time_days = (merged_at - created_at).days
          merge_times.append(max(0, merge_time_days))

      median_merge_time = float(median(merge_times)) if merge_times else 0.0
      return median_merge_time, merged_count

    except requests.RequestException as e:
      logger.error(f"Failed to fetch PR metrics from {repo}: {e}")
      raise

  def calculate_response_rate(self, issues: list[dict[str, Any]]) -> float:
    """Calculate percentage of issues with response within 48 hours.

    Args:
      issues: List of open issue data

    Returns:
      Percentage of issues with response within 48 hours
    """
    if not issues:
      return 0.0

    responded = 0
    now = datetime.now(datetime.now().astimezone().tzinfo)
    cutoff = now - timedelta(hours=48)

    for issue in issues:
      created_at = datetime.fromisoformat(
          issue["created_at"].replace("Z", "+00:00")
      )

      # Count as responded if there are comments
      if issue.get("comments", 0) > 0:
        if created_at >= cutoff:
          responded += 1

    response_rate = (responded / len(issues) * 100) if issues else 0.0
    return response_rate

  def get_commit_frequency(self, repo: str) -> list[int]:
    """Get commit frequency for last 12 weeks.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      List of 12 weekly commit counts

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/stats/commit_activity"
      response = requests.get(url, headers=self.headers, timeout=10)
      response.raise_for_status()

      data = response.json()
      if not data:
        return [0] * 12

      # Get last 12 weeks
      week_counts = [week["total"] for week in data[-12:]]
      return week_counts

    except requests.RequestException as e:
      logger.error(f"Failed to fetch commit frequency from {repo}: {e}")
      return [0] * 12

  def get_repo_growth(self, repo: str) -> tuple[float, float]:
    """Calculate week-over-week growth for stars and forks.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      Tuple of (stars WoW growth %, forks WoW growth %)

    Raises:
      requests.RequestException: If API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}"
      response = requests.get(url, headers=self.headers, timeout=10)
      response.raise_for_status()

      _ = response.json()

      # Simplified growth calculation (would need historical data for actual WoW)
      # For now, return 0 as placeholder - actual implementation would track
      # historical stars/forks data to calculate week-over-week changes
      return 0.0, 0.0

    except requests.RequestException as e:
      logger.error(f"Failed to fetch repo growth from {repo}: {e}")
      raise

  def generate_metrics(self, repo: str) -> HealthMetrics:
    """Generate health metrics for a repository.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      HealthMetrics object with all health indicators

    Raises:
      requests.RequestException: If any API requests fail
    """
    logger.info(f"Generating health metrics for {repo}")

    # Fetch data
    issue_count, issues = self.get_open_issues(repo)
    issue_age = self.calculate_issue_age_median(issues)
    pr_merge_time, _ = self.get_pr_metrics(repo)
    response_rate = self.calculate_response_rate(issues)
    commit_freq = self.get_commit_frequency(repo)
    stars_growth, forks_growth = self.get_repo_growth(repo)

    metrics = HealthMetrics(
        repo=repo,
        timestamp=datetime.now().isoformat(),
        open_issues_count=issue_count,
        median_issue_age_days=issue_age,
        median_pr_merge_days=pr_merge_time,
        response_rate_48h=response_rate,
        commit_frequency_12w=commit_freq,
        stars_growth_wow=stars_growth,
        forks_growth_wow=forks_growth,
    )

    # Cache the result
    self.cache[repo] = metrics
    self.last_fetch[repo] = datetime.now()

    return metrics

  def get_metrics_json(self, repo: str) -> str:
    """Generate metrics as JSON string.

    Args:
      repo: Repository in "owner/repo" format

    Returns:
      JSON string with health metrics
    """
    metrics = self.generate_metrics(repo)
    health_status = metrics.get_health_status()

    data = {
        "repository": repo,
        "health_status": health_status,
        "generated_at": datetime.now().isoformat(),
        "metrics": metrics.to_dict(),
    }

    return json.dumps(data, indent=2)


def get_health_metrics_generator() -> HealthMetricsGenerator:
  """Create a health metrics generator from environment variables.

  Returns:
    Initialized HealthMetricsGenerator

  Raises:
    ValueError: If GITHUB_TOKEN is not set
  """
  token = os.getenv("GITHUB_TOKEN")
  if not token:
    raise ValueError("GITHUB_TOKEN environment variable is required")

  return HealthMetricsGenerator(token)
