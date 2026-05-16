"""Display helpers for consistent Rich output."""

from typing import Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from oss_dev.cli.ui.console import console


def display_error(message: str, details: Optional[str] = None) -> None:
    """Display an error message."""
    text = Text(message, style="error")
    if details:
        text.append(f"\n{details}", style="dim")
    panel = Panel(text, border_style="red", box=box.ROUNDED, padding=(1, 2))
    console.print()
    console.print(panel)
    console.print()


def display_success(message: str) -> None:
    """Display a success message."""
    panel = Panel(
        Text(message, style="success"),
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def display_warning(message: str) -> None:
    """Display a warning message."""
    panel = Panel(
        Text(message, style="warning"),
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def display_info(message: str) -> None:
    """Display an info message."""
    console.print(f"[info]{message}[/info]")


def display_panel(
    title: str,
    content: str,
    border_style: str = "cyan",
    style: str = "white",
) -> None:
    """Display a panel with title and content."""
    panel = Panel(
        Text(content, style=style),
        title=Text(title, style=f"bold {border_style}"),
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def display_table(
    title: str,
    columns: list[str],
    rows: list[list[str]],
    border_style: str = "cyan",
) -> None:
    """Display a table with title."""
    table = Table(
        title=Text(title, style=f"bold {border_style}"),
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    for col in columns:
        table.add_column(col, style="bold", no_wrap=True)
    for row in rows:
        table.add_row(*row)
    console.print()
    console.print(table)
    console.print()


def display_status(items: list[tuple[str, str, str]]) -> None:
    """Display a status grid (label, value, style)."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", justify="right", width=15)
    grid.add_column(style="white")
    for label, value, style in items:
        grid.add_row(f"{label}:", f"[{style}]{value}[/{style}]")
    panel = Panel(
        grid,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()
