from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    BarColumn,
)
from contextlib import contextmanager


@contextmanager
def progress_bar(description: str = "Processing..."):
    """Reusable progress bar for long-running CLI operations."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(description, total=None)
        yield progress, task
