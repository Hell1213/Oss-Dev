import subprocess
from unittest.mock import patch

import pytest

from oss_dev.config.models import Config
from oss_dev.core.errors import ProviderError
from oss_dev.providers.github.client import GitHubCLIProvider


def _completed_process(stdout: str, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gh"],
        returncode=0,
        stdout=stdout,
        stderr=stderr,
    )


def test_healthy_quota():
    with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
        provider = GitHubCLIProvider(Config())

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed_process(
                '{"resources":{"core":{"limit":5000,"remaining":100,"reset":1710000000,"used":1}}}'
            ),
            _completed_process("{}"),
        ]

        output = provider._run_gh(["api", "repos/owner/repo"])

    assert output == "{}"
    assert mock_run.call_count == 2


def test_zero_quota():
    with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
        provider = GitHubCLIProvider(Config())

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed_process(
                '{"resources":{"core":{"limit":5000,"remaining":0,"reset":1710000000,"used":5000}}}'
            )
        ]

        with pytest.raises(ProviderError) as exc_info:
            provider._run_gh(["api", "repos/owner/repo"])

    assert "rate limit exceeded" in str(exc_info.value).lower()
    assert mock_run.call_count == 1


def test_low_quota_warning(capsys: pytest.CaptureFixture[str]):
    with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
        provider = GitHubCLIProvider(Config())

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed_process(
                '{"resources":{"core":{"limit":5000,"remaining":5,"reset":1710000000,"used":4995}}}'
            ),
            _completed_process("{}"),
        ]

        output = provider._run_gh(["api", "repos/owner/repo"])

    captured = capsys.readouterr()
    assert "rate limit is low" in captured.err.lower()
    assert output == "{}"


def test_malformed_rate_limit_response():
    with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
        provider = GitHubCLIProvider(Config())

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed_process("not-json"),
            _completed_process("{}"),
        ]

        output = provider._run_gh(["api", "repos/owner/repo"])

    assert output == "{}"


def test_rate_limit_endpoint_does_not_recurse():
    with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
        provider = GitHubCLIProvider(Config())

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _completed_process(
            '{"resources":{"core":{"limit":5000,"remaining":100,"reset":1710000000,"used":1}}}'
        )

        output = provider._run_gh(["api", "rate_limit"])

    assert output == '{"resources":{"core":{"limit":5000,"remaining":100,"reset":1710000000,"used":1}}}'
    assert mock_run.call_count == 1
