"""
Tests for Git tools.
"""

import pytest
from pathlib import Path
import subprocess

from tools.oss.git_status import GitStatusTool, GitStatusParams
from tools.oss.git_branch import GitBranchTool, GitBranchParams
from tools.oss.git_commit import GitCommitTool, GitCommitParams
from tools.oss.git_diff import GitDiffTool, GitDiffParams
from config.config import Config, OSSConfig


@pytest.fixture
def mock_git_repo(tmp_path):
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    subprocess.run(['git', 'init'], cwd=repo)
    (repo / 'README.md').write_text('Initial commit')
    subprocess.run(['git', 'add', 'README.md'], cwd=repo)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo)
    return repo


@pytest.mark.asyncio
async def test_git_status_tool(test_config, mock_git_repo):
    """Test git status tool."""
    tool = GitStatusTool(test_config)
    params = GitStatusParams(path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is True
    assert "Dirty" in result.output or "Modified" in result.output


@pytest.mark.asyncio
async def test_git_branch_create(test_config, mock_git_repo):
    """Test git branch creation."""
    tool = GitBranchTool(test_config)
    params = GitBranchParams(action="create", branch_name="test-branch", path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is True
    # Verify the branch creation message
    assert "Created and switched to branch" in result.output


@pytest.mark.asyncio
async def test_git_branch_list(test_config, mock_git_repo):
    """Test git branch list."""
    tool = GitBranchTool(test_config)
    params = GitBranchParams(action="list", path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is True
    assert "Branches:" in result.output


@pytest.mark.asyncio
async def test_git_branch_protected(test_config, mock_git_repo):
    """Test that protected branches cannot be created."""
    tool = GitBranchTool(test_config)
    params = GitBranchParams(action="create", branch_name="main", path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is False
    assert "protected" in result.error.lower()


@pytest.mark.asyncio
async def test_git_diff_tool(test_config, mock_git_repo):
    """Test git diff tool."""
    tool = GitDiffTool(test_config)
    test_file = mock_git_repo / "test.txt"
    test_file.write_text("test content")
    params = GitDiffParams(path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is True


@pytest.mark.asyncio
async def test_git_commit_tool(test_config, mock_git_repo):
    """Test git commit tool."""
    tool = GitCommitTool(test_config)
    test_file = mock_git_repo / "test.txt"
    test_file.write_text("test content")
    subprocess.run([
        "git", "add", "test.txt",
        "--recurse-submodules",
        "--quiet"
    ], cwd=mock_git_repo, capture_output=True, check=True)
    params = GitCommitParams(message="test: add test file", path=str(mock_git_repo))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': mock_git_repo
    })()
    result = await tool.execute(invocation)
    assert result.success is True
    assert "Created commit" in result.output