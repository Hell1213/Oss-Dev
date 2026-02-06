"""
Tests for OSS CLI commands.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path

from cli.oss_commands import oss_dev_group


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_repo(temp_dir):
    """Create a temporary git repository."""
    import subprocess
    
    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )
    
    # Add remote (mock)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/test-owner/test-repo.git"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )
    
    return temp_dir


def test_oss_dev_group_help(cli_runner):
    """Test oss-dev command group help."""
    result = cli_runner.invoke(oss_dev_group, ["--help"])
    assert result.exit_code == 0
    assert "OSS Dev Agent" in result.output
    assert "fix" in result.output
    assert "review" in result.output
    assert "resume" in result.output
    assert "status" in result.output
    assert "list" in result.output
    assert "switch" in result.output


def test_oss_dev_fix_requires_url(cli_runner):
    """Test that oss-dev fix requires an issue URL."""
    result = cli_runner.invoke(oss_dev_group, ["fix"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "required" in result.output.lower()


def test_oss_dev_review_requires_number(cli_runner):
    """Test that oss-dev review requires an issue number."""
    result = cli_runner.invoke(oss_dev_group, ["review"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "required" in result.output.lower()


def test_oss_dev_status_command(cli_runner, temp_repo):
    """Test oss-dev status command."""
    result = cli_runner.invoke(
        oss_dev_group,
        ["status"],
        env={"GITHUB_TOKEN": "test-token"},
    )
    # Should not crash even if no workflow exists
    assert result.exit_code in [0, 1]  # May exit with error if OSS not enabled


def test_oss_dev_list_command(cli_runner, temp_repo):
    """Test oss-dev list command."""
    result = cli_runner.invoke(
        oss_dev_group,
        ["list"],
        env={"GITHUB_TOKEN": "test-token"},
    )
    # Should not crash
    assert result.exit_code in [0, 1]  # May exit with error if OSS not enabled


def test_oss_dev_switch_requires_target(cli_runner):
    """Test that oss-dev switch requires a target."""
    result = cli_runner.invoke(oss_dev_group, ["switch"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output or "required" in result.output.lower()
