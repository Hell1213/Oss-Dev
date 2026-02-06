"""
Tests for GitHub client.
"""

import pytest

from oss.github import GitHubClient
from config.config import Config, OSSConfig


def test_parse_issue_url():
    """Test parsing GitHub issue URLs."""
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    result = client.parse_issue_url("https://github.com/owner/repo/issues/123")
    
    assert result["owner"] == "owner"
    assert result["repo"] == "repo"
    assert result["issue_number"] == 123


def test_parse_issue_url_invalid():
    """Test parsing invalid GitHub issue URLs."""
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    with pytest.raises(ValueError):
        client.parse_issue_url("https://invalid-url.com")
