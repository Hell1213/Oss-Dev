from pathlib import Path

def resolve_path(base: str | Path, path: str | Path):

    """Resolve a path relative to a base directory.

    Args:
        base: Base directory path
        path: Target path to resolve

    Returns:
        Absolute resolved path.
    """
    
    path = Path(path)
    if path.is_absolute():
        return path.resolve()

    return Path(base).resolve() / path


def display_path_rel_to_cwd(path: str, cwd: Path | None) -> str:

    """Display a path relative to the current working directory.

    Args:
        path: Path to display.
        cwd: Current working directory path.

    Returns:
        Relative path if possible, otherwise the original path.
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
        path: File or directory path.

    Returns:
        Path object with ensured parent directories.
    """

    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def is_binary_file(path: str | Path) -> bool:

    """Check whether a file is binary.

    Args:
        path: Path to the file.

    Returns:
        True if the file is binary, otherwise False.
    """
    
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, IOError):
        return False
