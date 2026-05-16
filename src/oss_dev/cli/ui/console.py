"""Rich console singleton for consistent CLI output."""

from rich.console import Console

from oss_dev.cli.ui.themes import OSS_DEV_THEME

_console: Console | None = None


def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=OSS_DEV_THEME, highlight=False)
    return _console


console = get_console()
