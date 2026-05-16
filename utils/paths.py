from pathlib import Path


def resolve_path(base: str | Path, path: str | Path):
    """Resolve a path relative to a base directory.

    Args:
        base: Base directory used when ``path`` is relative.
        path: Absolute or relative path to resolve.

    Returns:
        The resolved absolute path when ``path`` is absolute, otherwise the
        resolved base directory joined with ``path``.
    """
    path = Path(path)
    if path.is_absolute():
        return path.resolve()

    return Path(base).resolve() / path


def display_path_rel_to_cwd(path: str, cwd: Path | None) -> str:
    """Return a path display string relative to the current working directory.

    Args:
        path: Path to display.
        cwd: Current working directory to make ``path`` relative to, if possible.

    Returns:
        ``path`` relative to ``cwd`` when possible; otherwise, the original path
        string or normalized path string.
    """
    try:
        p = Path(path)
    except Exception:
        return path

    if cwd:
        try:
            return str(p.relative_to(cwd))
        except ValueError:
            pass

    return str(p)


def ensure_parent_directory(path: str | Path) -> Path:
    """Ensure the parent directory for a path exists.

    Args:
        path: File path whose parent directory should be created.

    Returns:
        The input path converted to a ``Path`` instance.
    """
    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def is_binary_file(path: str | Path) -> bool:
    """Check whether a file appears to contain binary data.

    Args:
        path: File path to inspect.

    Returns:
        True if the first bytes of the file contain a null byte; otherwise False.
        Returns False if the file cannot be read.
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, IOError):
        return False
