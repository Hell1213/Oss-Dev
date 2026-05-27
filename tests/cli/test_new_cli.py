from typer.testing import CliRunner

from oss_dev.cli.app import app


runner = CliRunner()


def test_typer_app_version_option():
    result = runner.invoke(
        app,
        ["--version"],
    )

    assert result.exit_code == 0
    assert result.output == "oss-dev v0.2.0\n"


def test_mentor_accepts_github_issue_url_with_positive_issue_number():
    result = runner.invoke(
        app,
        ["mentor", "https://github.com/Hell1213/Oss-Dev/issues/28"],
    )

    assert result.exit_code == 0
    assert "Mentoring for issue #28" in result.output


def test_mentor_rejects_issue_url_without_issue_number():
    result = runner.invoke(
        app,
        ["mentor", "https://github.com/Hell1213/Oss-Dev/issues/not-a-number"],
    )

    assert result.exit_code != 0
    assert "positive issue" in result.output
    assert "number" in result.output


def test_mentor_rejects_non_positive_issue_number():
    result = runner.invoke(
        app,
        ["mentor", "https://github.com/Hell1213/Oss-Dev/issues/0"],
    )

    assert result.exit_code != 0
    assert "positive issue" in result.output
    assert "number" in result.output
