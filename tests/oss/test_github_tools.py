"""
Tests for GitHub tools.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from tools.oss.fetch_issue import FetchIssueTool, FetchIssueParams
from tools.oss.create_pr import CreatePRTool, CreatePRParams
from tools.oss.get_pr_status import GetPRStatusTool, GetPRStatusParams
from tools.oss.list_issues import ListIssuesTool, ListIssuesParams
from config.config import Config, OSSConfig


@pytest.mark.asyncio
async def test_fetch_issue_tool(test_config):
    """Test fetch issue tool."""
    tool = FetchIssueTool(test_config)

    with patch("tools.oss.fetch_issue.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client.fetch_issue = AsyncMock(return_value={
            "title": "Test Issue",
            "body": "Test issue body",
            "state": "open",
            "labels": ["bug"],
            "number": 123,
            "url": "https://github.com/test/repo/issues/123",
        })
        mock_client_class.return_value = mock_client

        params = FetchIssueParams(issue_url="https://github.com/test/repo/issues/123")
        invocation = type('obj', (object,), {
            'params': params.model_dump(),
            'cwd': "/tmp/test"
        })()

        result = await tool.execute(invocation)
        assert result.success is True
        assert "Test Issue" in result.output
        assert "open" in result.output


@pytest.mark.asyncio
async def test_fetch_issue_invalid_url(test_config):
    """Test fetch issue with invalid URL."""
    tool = FetchIssueTool(test_config)

    params = FetchIssueParams(issue_url="invalid-url")
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': "/tmp/test"
    })()

    result = await tool.execute(invocation)
    assert result.success is False
    assert "Invalid issue URL" in result.error


@pytest.mark.asyncio
async def test_create_pr_tool(test_config):
    """Test create PR tool."""
    tool = CreatePRTool(test_config)

    with patch("tools.oss.create_pr.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client.create_pr = AsyncMock(return_value={
            "url": "https://github.com/test/repo/pull/1",
            "number": 1,
            "title": "Test PR",
        })
        mock_client_class.return_value = mock_client

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = type('obj', (object,), {
                'stdout': 'https://github.com/test/repo.git',
                'returncode': 0
            })()

            params = CreatePRParams(
                title="Test PR",
                body="Test PR body",
                head="feature-branch",
                repo="test/repo"
            )
            invocation = type('obj', (object,), {
                'params': params.model_dump(),
                'cwd': "/tmp/test"
            })()

            result = await tool.execute(invocation)
            assert result.success is True
            assert "Created PR" in result.output


@pytest.mark.asyncio
async def test_get_pr_status_tool(test_config):
    """Test get PR status tool."""
    tool = GetPRStatusTool(test_config)

    with patch("tools.oss.get_pr_status.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get_pr_status = Mock(return_value={
            "state": "open",
            "isDraft": False,
            "reviewDecision": "APPROVED",
            "url": "https://github.com/test/repo/pull/1",
        })
        mock_client_class.return_value = mock_client

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = type('obj', (object,), {
                'stdout': 'https://github.com/test/repo.git',
                'returncode': 0
            })()

            params = GetPRStatusParams(pr_number=1, repo="test/repo")
            invocation = type('obj', (object,), {
                'params': params.model_dump(),
                'cwd': "/tmp/test"
            })()

            result = await tool.execute(invocation)
            assert result.success is True
            assert "open" in result.output


@pytest.mark.asyncio
async def test_list_issues_tool(test_config):
    """Test list issues tool."""
    tool = ListIssuesTool(test_config)

    with patch("tools.oss.list_issues.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client.list_issues = AsyncMock(return_value=[
            {
                "title": "Issue 1",
                "number": 1,
                "state": "open",
                "labels": ["bug"],
                "url": "https://github.com/test/repo/issues/1",
            },
            {
                "title": "Issue 2",
                "number": 2,
                "state": "open",
                "labels": [],
                "url": "https://github.com/test/repo/issues/2",
            },
        ])
        mock_client_class.return_value = mock_client

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = type('obj', (object,), {
                'stdout': 'https://github.com/test/repo.git',
                'returncode': 0
            })()

            params = ListIssuesParams(repo="test/repo", state="open", limit=10)
            invocation = type('obj', (object,), {
                'params': params.model_dump(),
                'cwd': "/tmp/test"
            })()

            result = await tool.execute(invocation)
            assert result.success is True
            assert "Issue 1" in result.output
            assert "Issue 2" in result.output
