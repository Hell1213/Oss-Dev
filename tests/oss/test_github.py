"""
Tests for GitHub client.
"""

import pytest

from oss.github import GitHubClient
from config.config import Config, OSSConfig


def test_parse_issue_url_rejects_invalid_url():
    """Test invalid issue URL validation."""
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)

    with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
        client.parse_issue_url("https://invalid-url.com")


def test_parse_issue_url_extracts_repository_and_issue():
    """Test GitHub issue URL parsing."""
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)

    parsed = client.parse_issue_url("https://github.com/Hell1213/Oss-Dev/issues/21")

    assert parsed == {
        "owner": "Hell1213",
        "repo": "Oss-Dev",
        "issue_number": 21,
    }


@pytest.mark.asyncio
async def test_create_pr_error_handling():
    """
    Test error handling of create_pr method.
    """
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)

    with pytest.raises(RuntimeError, match="Failed to create PR via GitHub CLI"):
        await client.create_pr("owner", "repo", "title", "body", "head")
