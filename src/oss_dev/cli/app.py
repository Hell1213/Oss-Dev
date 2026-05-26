"""OSS-Dev CLI application.

Professional Typer-based CLI with consistent UX, rich output, and actionable errors.
"""

import re
from pathlib import Path
from typing import Optional

import typer

from oss_dev._version import __version__
from oss_dev.cli.progress import progress_bar

app = typer.Typer(
    name="oss-dev",
    help="Open Source Contributor Operating System — discover, understand, and contribute to OSS projects.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)

discover_app = typer.Typer(help="Discover repositories or issues.", no_args_is_help=True)
issues_app = typer.Typer(help="Manage and explore issues.", no_args_is_help=True)
app.add_typer(discover_app, name="discover")
app.add_typer(issues_app, name="issues")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"oss-dev v{__version__}")
        raise typer.Exit()


def _parse_issue_number(issue_url: str) -> int:
    pattern = r"^https?://github\.com/[^/]+/[^/]+/issues/([1-9]\d*)(?:[/?#].*)?$"
    match = re.match(pattern, issue_url)
    if not match:
        raise typer.BadParameter(
            "issue_url must be a GitHub issue URL with a positive issue number, "
            "for example: https://github.com/owner/repo/issues/123"
        )
    return int(match.group(1))


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version.", callback=_version_callback, is_eager=True),
    cwd: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Working directory.", exists=True, file_okay=False, dir_okay=True),
) -> None:
    """OSS-Dev: Open Source Contributor Operating System."""
    pass


@discover_app.command("repos")
def discover_repos(
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Filter by language."),
    good_first_issues: bool = typer.Option(False, "--good-first-issues", "-g", help="Only repos with good first issues."),
    limit: int = typer.Option(10, "--limit", help="Maximum results."),
) -> None:
    """Discover open source repositories to contribute to."""
    with progress_bar("Discovering repositories...") as (progress, task):
        import time
        time.sleep(2)  # simulates real work
        progress.update(task, description="Repositories discovered!")


@discover_app.command("issues")
def discover_issues(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/name)."),
    good_first: bool = typer.Option(False, "--good-first", "-g", help="Good first issues only."),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label."),
    limit: int = typer.Option(10, "--limit", help="Maximum results."),
) -> None:
    """Discover issues to work on."""
    with progress_bar("Discovering issues...") as (progress, task):
        import time
        time.sleep(2)  # simulates real work
        progress.update(task, description="Issues discovered!")


@issues_app.command("list")
def issues_list(
    repo: str = typer.Argument(..., help="Repository (owner/name)."),
    state: str = typer.Option("open", "--state", "-s", help="Issue state: open, closed, all."),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label."),
    limit: int = typer.Option(10, "--limit", help="Maximum results."),
) -> None:
    """List issues for a repository."""
    typer.echo(f"Listing issues for {repo}...")


@issues_app.command("show")
def issues_show(
    repo: str = typer.Argument(..., help="Repository (owner/name)."),
    issue_number: int = typer.Argument(..., help="Issue number."),
) -> None:
    """Show details for a specific issue."""
    typer.echo(f"Showing issue #{issue_number} for {repo}...")


@app.command()
def analyze(
    target: str = typer.Argument(..., help="Repository path or URL to analyze."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for analysis results."),
) -> None:
    """Analyze a repository or issue for contribution readiness."""
    with progress_bar(f"Analyzing {target}...") as (progress, task):
        import time
        time.sleep(2)  # simulates real work
        progress.update(task, description="Analysis complete!")


@app.command()
def explain(
    path: Path = typer.Argument(..., help="Path to file or directory to explain.", exists=True),
    depth: int = typer.Option(2, "--depth", "-d", help="Explanation depth."),
) -> None:
    """Explain code structure and purpose."""
    typer.echo(f"Explaining {path}...")


@app.command()
def roadmap(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/name)."),
) -> None:
    """Show contribution roadmap for current or specified repository."""
    typer.echo("Showing contribution roadmap...")


@app.command()
def mentor(
    issue_url: str = typer.Argument(..., help="GitHub issue URL to work on."),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from last checkpoint."),
) -> None:
    """Get step-by-step mentoring through a contribution."""
    issue_number = _parse_issue_number(issue_url)
    typer.echo(f"Mentoring for issue #{issue_number}: {issue_url}...")


@app.command()
def docs(
    query: Optional[str] = typer.Argument(None, help="Documentation search query."),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/name)."),
) -> None:
    """Search and explore project documentation."""
    typer.echo(f"Searching docs for '{query}'...")


@app.command()
def doctor() -> None:
    """Run system diagnostics to check OSS-Dev setup."""
    with progress_bar("Running diagnostics...") as (progress, task):
        import time
        time.sleep(2)  # simulates real work
        progress.update(task, description="Diagnostics complete!")


@app.command()
def plugins(
    action: str = typer.Argument("list", help="Action: list, install, remove, info."),
    name: Optional[str] = typer.Argument(None, help="Plugin name."),
) -> None:
    """Manage OSS-Dev plugins."""
    typer.echo(f"Plugins: {action} {name or ''}")


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key to get/set."),
    value: Optional[str] = typer.Argument(None, help="Value to set."),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all config."),
) -> None:
    """View or modify OSS-Dev configuration."""
    typer.echo("Configuration management...")


if __name__ == "__main__":
    app()
