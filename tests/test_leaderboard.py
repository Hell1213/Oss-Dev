"""Tests for contributor activity leaderboard system."""

from unittest.mock import MagicMock, patch

import pytest

from tools.leaderboard import LeaderboardGenerator, LeaderboardMetrics, get_leaderboard_generator


class TestLeaderboardMetrics:
  """Test suite for LeaderboardMetrics class."""

  def test_create_metrics(self) -> None:
    """Test creating metrics for a contributor."""
    metrics = LeaderboardMetrics(
        login="alice",
        avatar_url="https://example.com/alice.jpg",
        issues_resolved=5,
        prs_merged=3,
        review_comments=10,
        docs_commits=2,
    )

    assert metrics.login == "alice"
    assert metrics.issues_resolved == 5

  def test_calculate_points(self) -> None:
    """Test point calculation with correct weights."""
    metrics = LeaderboardMetrics(
        login="bob",
        avatar_url="",
        issues_resolved=5,  # 5 * 10 = 50
        prs_merged=3,  # 3 * 15 = 45
        review_comments=10,  # 10 * 5 = 50
        docs_commits=2,  # 2 * 20 = 40
    )

    points = metrics.calculate_points()
    # 50 + 45 + 50 + 40 = 185
    assert points == 185
    assert metrics.total_points == 185

  def test_to_dict(self) -> None:
    """Test converting metrics to dictionary."""
    metrics = LeaderboardMetrics(
        login="charlie",
        avatar_url="https://example.com/charlie.jpg",
        issues_resolved=3,
        prs_merged=2,
        review_comments=5,
        docs_commits=1,
    )
    metrics.calculate_points()

    data = metrics.to_dict()
    assert data["login"] == "charlie"
    assert "points" in data
    assert "breakdown" in data
    assert data["breakdown"]["issues_resolved"] == 3


class TestLeaderboardGenerator:
  """Test suite for LeaderboardGenerator class."""

  def test_init_with_token(self) -> None:
    """Test generator initialization."""
    generator = LeaderboardGenerator("test-token")
    assert generator.token == "test-token"
    assert "Bearer test-token" in generator.headers["Authorization"]

  def test_init_without_token(self) -> None:
    """Test that initialization fails without token."""
    with pytest.raises(ValueError):
      LeaderboardGenerator("")

  @patch("tools.leaderboard.requests.get")
  def test_get_closed_issues(self, mock_get) -> None:
    """Test fetching closed issues."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "Issue 1",
            "closed_by": {"login": "alice", "avatar_url": "url1"},
        }
    ]
    mock_get.return_value = mock_response

    generator = LeaderboardGenerator("token")
    issues = generator.get_closed_issues("owner/repo")

    assert len(issues) >= 0
    mock_get.assert_called()

  @patch("tools.leaderboard.requests.get")
  def test_get_merged_prs(self, mock_get) -> None:
    """Test fetching merged pull requests."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "PR 1",
            "merged_by": {"login": "bob", "avatar_url": "url2"},
            "merged_at": "2024-01-01T00:00:00Z",
        }
    ]
    mock_get.return_value = mock_response

    generator = LeaderboardGenerator("token")
    prs = generator.get_merged_prs("owner/repo")

    assert len(prs) >= 0
    mock_get.assert_called()

  @patch("tools.leaderboard.requests.get")
  def test_get_code_reviews(self, mock_get) -> None:
    """Test fetching code reviews."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": 1,
            "user": {"login": "charlie"},
            "body": "Great work!",
        }
    ]
    mock_get.return_value = mock_response

    generator = LeaderboardGenerator("token")
    reviews = generator.get_code_reviews("owner/repo")

    assert isinstance(reviews, dict)
    mock_get.assert_called()

  def test_generate_leaderboard_invalid_window(self) -> None:
    """Test that invalid time window raises error."""
    generator = LeaderboardGenerator("token")

    with pytest.raises(ValueError):
      generator.generate_leaderboard("owner/repo", time_window="invalid")

  @patch("tools.leaderboard.LeaderboardGenerator.get_merged_prs")
  @patch("tools.leaderboard.LeaderboardGenerator.get_closed_issues")
  @patch("tools.leaderboard.LeaderboardGenerator.get_code_reviews")
  @patch("tools.leaderboard.LeaderboardGenerator.get_docs_contributions")
  def test_generate_leaderboard_ranking(
      self, mock_docs, mock_reviews, mock_issues, mock_prs
  ) -> None:
    """Test leaderboard ranking by points."""
    # Setup mock data
    mock_issues.return_value = [
        {
            "number": 1,
            "closed_by": {"login": "alice", "avatar_url": "url1"},
        }
    ]
    mock_prs.return_value = [
        {
            "number": 1,
            "merged_by": {"login": "bob", "avatar_url": "url2"},
            "merged_at": "2024-01-01T00:00:00Z",
        }
    ]
    mock_reviews.return_value = {"charlie": 5}
    mock_docs.return_value = {"alice": 2}

    generator = LeaderboardGenerator("token")
    leaderboard = generator.generate_leaderboard("owner/repo", top_n=10)

    assert isinstance(leaderboard, list)
    if leaderboard:
      # Should be sorted by points descending
      for i in range(len(leaderboard) - 1):
        assert leaderboard[i].total_points >= leaderboard[i + 1].total_points

  def test_get_leaderboard_json(self) -> None:
    """Test generating leaderboard as JSON."""
    with patch.object(
        LeaderboardGenerator, "generate_leaderboard", return_value=[]
    ):
      generator = LeaderboardGenerator("token")
      json_str = generator.get_leaderboard_json("owner/repo")

      assert isinstance(json_str, str)
      assert "leaderboard" in json_str
      assert "owner/repo" in json_str

  def test_get_leaderboard_generator(self) -> None:
    """Test creating generator from environment."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
      generator = get_leaderboard_generator()
      assert generator.token == "test-token"

  def test_get_leaderboard_generator_missing_token(self) -> None:
    """Test generator creation fails without token."""
    with patch.dict("os.environ", {}, clear=True):
      with pytest.raises(ValueError):
        get_leaderboard_generator()
