import json

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


def test_discover_repos_json_output():
    result = runner.invoke(
        app,
        ["discover", "repos", "--language", "Python", "--good-first-issues", "--limit", "5", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {
        "repositories": [],
        "filters": {
            "language": "Python",
            "good_first_issues": True,
            "limit": 5,
        },
    }


def test_discover_issues_json_output():
    result = runner.invoke(
        app,
        ["discover", "issues", "--repo", "owner/repo", "--good-first", "--label", "bug", "--limit", "7", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {
        "issues": [],
        "filters": {
            "repo": "owner/repo",
            "good_first": True,
            "label": "bug",
            "limit": 7,
        },
    }


def test_issues_list_json_output():
    result = runner.invoke(
        app,
        ["issues", "list", "owner/repo", "--state", "closed", "--label", "help wanted", "--limit", "3", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {
        "repo": "owner/repo",
        "state": "closed",
        "label": "help wanted",
        "limit": 3,
        "issues": [],
    }


def test_analyze_json_output():
    result = runner.invoke(
        app,
        ["analyze", "https://github.com/owner/repo", "--output", "analysis.json", "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {
        "target": "https://github.com/owner/repo",
        "output": "analysis.json",
        "analysis": {
            "status": "pending",
        },
    }


def test_discover_repos_text_output_unchanged_without_json():
    result = runner.invoke(
        app,
        ["discover", "repos"],
    )

    assert result.exit_code == 0
