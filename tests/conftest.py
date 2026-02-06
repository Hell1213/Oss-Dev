"""
Pytest configuration and fixtures for testing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from config.config import Config, OSSConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    return Config(
        cwd=temp_dir,
        oss=OSSConfig(enabled=True),
    )


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock()
    client.parse_issue_url = Mock(return_value={
        "owner": "test-owner",
        "repo": "test-repo",
        "issue_number": 123,
    })
    client.fetch_issue = AsyncMock(return_value={
        "title": "Test Issue",
        "body": "Test issue body",
        "state": "open",
        "labels": [],
        "number": 123,
        "url": "https://github.com/test-owner/test-repo/issues/123",
    })
    return client


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository."""
    # Initialize git repo
    import subprocess
    subprocess.run(
        ["git", "init"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    return temp_dir
