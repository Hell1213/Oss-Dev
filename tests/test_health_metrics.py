"""Tests for project health metrics system."""

from unittest.mock import MagicMock, patch

import pytest

from tools.health_metrics import (
    HealthMetrics,
    HealthMetricsGenerator,
    get_health_metrics_generator,
)


class TestHealthMetrics:
  """Test suite for HealthMetrics class."""

  def test_create_metrics(self) -> None:
    """Test creating health metrics."""
    metrics = HealthMetrics(
        repo="owner/repo",
        timestamp="2024-01-01T00:00:00",
        open_issues_count=25,
        median_issue_age_days=10.5,
        median_pr_merge_days=3.2,
        response_rate_48h=85.0,
        commit_frequency_12w=[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        stars_growth_wow=2.5,
        forks_growth_wow=1.0,
    )

    assert metrics.repo == "owner/repo"
    assert metrics.open_issues_count == 25

  def test_get_health_status_healthy(self) -> None:
    """Test health status when metrics are good."""
    metrics = HealthMetrics(
        repo="owner/repo",
        timestamp="2024-01-01T00:00:00",
        open_issues_count=20,
        median_issue_age_days=5.0,
        median_pr_merge_days=2.0,
        response_rate_48h=90.0,
        commit_frequency_12w=[10] * 12,
        stars_growth_wow=1.0,
        forks_growth_wow=0.5,
    )

    assert metrics.get_health_status() == "healthy"

  def test_get_health_status_warning(self) -> None:
    """Test health status with some issues."""
    metrics = HealthMetrics(
        repo="owner/repo",
        timestamp="2024-01-01T00:00:00",
        open_issues_count=110,  # > 100
        median_issue_age_days=35.0,  # > 30
        median_pr_merge_days=2.0,
        response_rate_48h=90.0,
        commit_frequency_12w=[10] * 12,
        stars_growth_wow=1.0,
        forks_growth_wow=0.5,
    )

    assert metrics.get_health_status() == "warning"

  def test_get_health_status_critical(self) -> None:
    """Test health status when multiple issues exist."""
    metrics = HealthMetrics(
        repo="owner/repo",
        timestamp="2024-01-01T00:00:00",
        open_issues_count=150,
        median_issue_age_days=40.0,
        median_pr_merge_days=10.0,
        response_rate_48h=50.0,
        commit_frequency_12w=[1] * 12,
        stars_growth_wow=0.0,
        forks_growth_wow=0.0,
    )

    assert metrics.get_health_status() == "critical"

  def test_to_dict(self) -> None:
    """Test converting metrics to dictionary."""
    metrics = HealthMetrics(
        repo="owner/repo",
        timestamp="2024-01-01T00:00:00",
        open_issues_count=25,
        median_issue_age_days=10.5,
        median_pr_merge_days=3.2,
        response_rate_48h=85.0,
        commit_frequency_12w=[5] * 12,
        stars_growth_wow=2.5,
        forks_growth_wow=1.0,
    )

    data = metrics.to_dict()
    assert data["repo"] == "owner/repo"
    assert "metrics" in data
    assert data["metrics"]["open_issues"] == 25


class TestHealthMetricsGenerator:
  """Test suite for HealthMetricsGenerator class."""

  def test_init_with_token(self) -> None:
    """Test generator initialization."""
    gen = HealthMetricsGenerator("test-token")
    assert gen.token == "test-token"

  def test_init_without_token(self) -> None:
    """Test initialization fails without token."""
    with pytest.raises(ValueError):
      HealthMetricsGenerator("")

  @patch("tools.health_metrics.requests.get")
  def test_get_open_issues(self, mock_get) -> None:
    """Test fetching open issues."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "Issue 1",
            "created_at": "2024-01-01T00:00:00Z",
            "comments": 2,
        }
    ]
    mock_get.return_value = mock_response

    gen = HealthMetricsGenerator("token")
    count, issues = gen.get_open_issues("owner/repo")

    assert count == 1
    assert len(issues) == 1

  def test_calculate_issue_age_median_empty(self) -> None:
    """Test calculating median with empty issues."""
    gen = HealthMetricsGenerator("token")
    age = gen.calculate_issue_age_median([])
    assert age == 0.0

  def test_calculate_issue_age_median_single(self) -> None:
    """Test calculating median with single issue."""
    gen = HealthMetricsGenerator("token")
    issues = [
        {
            "created_at": "2023-12-01T00:00:00Z",
        }
    ]
    age = gen.calculate_issue_age_median(issues)
    assert age > 0  # Should be positive days old

  @patch("tools.health_metrics.requests.get")
  def test_get_pr_metrics(self, mock_get) -> None:
    """Test fetching PR metrics."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "merged_at": "2024-01-03T00:00:00Z",
        }
    ]
    mock_get.return_value = mock_response

    gen = HealthMetricsGenerator("token")
    merge_time, count = gen.get_pr_metrics("owner/repo")

    assert merge_time >= 0
    assert count >= 0

  def test_calculate_response_rate_empty(self) -> None:
    """Test response rate with no issues."""
    gen = HealthMetricsGenerator("token")
    rate = gen.calculate_response_rate([])
    assert rate == 0.0

  @patch("tools.health_metrics.requests.get")
  def test_get_commit_frequency(self, mock_get) -> None:
    """Test fetching commit frequency."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"week": 0, "total": 5},
        {"week": 1, "total": 6},
    ]
    mock_get.return_value = mock_response

    gen = HealthMetricsGenerator("token")
    freq = gen.get_commit_frequency("owner/repo")

    assert isinstance(freq, list)
    assert len(freq) <= 12

  @patch("tools.health_metrics.requests.get")
  def test_get_repo_growth(self, mock_get) -> None:
    """Test fetching repo growth metrics."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "stargazers_count": 100,
        "forks_count": 50,
    }
    mock_get.return_value = mock_response

    gen = HealthMetricsGenerator("token")
    stars_growth, forks_growth = gen.get_repo_growth("owner/repo")

    assert isinstance(stars_growth, float)
    assert isinstance(forks_growth, float)

  def test_get_health_metrics_generator(self) -> None:
    """Test creating generator from environment."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
      gen = get_health_metrics_generator()
      assert gen.token == "test-token"

  def test_get_health_metrics_generator_missing_token(self) -> None:
    """Test generator creation fails without token."""
    with patch.dict("os.environ", {}, clear=True):
      with pytest.raises(ValueError):
        get_health_metrics_generator()
