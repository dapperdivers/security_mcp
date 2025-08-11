"""Path utilities for Bearer MCP Server."""

from pathlib import Path

from ..core.config import get_working_directory


def validate_path(path_str: str, must_exist: bool = False) -> Path:
    """
    Validate and resolve a path string.

    Args:
        path_str: Path string to validate
        must_exist: Whether the path must exist

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is invalid or doesn't exist when required
    """
    try:
        path = Path(path_str)

        # Make relative paths relative to working directory
        if not path.is_absolute() and (working_dir := get_working_directory()):
            path = working_dir / path

        path = path.resolve()

        if must_exist:
            try:
                # Use EAFP - attempt to check if the path is accessible
                path.stat()
            except (OSError, FileNotFoundError) as e:
                raise ValueError(
                    f"Path does not exist or is not accessible: {path}"
                ) from e

        return path
    except Exception as e:
        raise ValueError(f"Invalid path '{path_str}': {str(e)}")


def resolve_scan_path(path_str: str | None = None) -> Path:
    """
    Resolve a path for scanning, with intelligent defaults.

    Args:
        path_str: Optional path string to scan

    Returns:
        Resolved Path object for scanning

    Raises:
        ValueError: If the resolved path doesn't exist
    """
    if path_str:
        # If path is provided, resolve it
        if not Path(path_str).is_absolute():
            # Try /workspace first for Docker environments
            if (workspace_path := Path("/workspace") / path_str).exists():
                return workspace_path

            # Fallback to working directory
            working_dir = get_working_directory() or Path.cwd()
            scan_path = working_dir / path_str
        else:
            scan_path = Path(path_str)

        if not scan_path.exists():
            raise ValueError(f"Path does not exist: {scan_path}")

        return scan_path

    # No path provided - use defaults
    # Try /workspace first (Docker environment)
    if (workspace := Path("/workspace")).exists():
        return workspace

    # Fallback to working directory or current directory
    return get_working_directory() or Path.cwd()
