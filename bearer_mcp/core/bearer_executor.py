"""Bearer CLI command execution module."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from ..core.config import BEARER_BINARY, get_logger, get_working_directory

logger = get_logger(__name__)


class BearerExecutor:
    """Handles execution of Bearer CLI commands."""

    def __init__(self, binary_path: str = BEARER_BINARY):
        self.binary_path = binary_path

    async def run_command(
        self, args: list[str], cwd: Path | None = None, capture_output: bool = True
    ) -> dict[str, Any]:
        """
        Run a Bearer CLI command and return the result.

        Args:
            args: Command arguments (excluding 'bearer')
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr

        Returns:
            Dictionary with exit_code, stdout, stderr, and success status
        """
        cwd = cwd or get_working_directory() or Path.cwd()

        cmd = [self.binary_path] + args
        logger.info(f"Running command: {' '.join(cmd)} in {cwd}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
            )

            stdout, stderr = await process.communicate()

            result = {
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "success": process.returncode == 0,
                "command": " ".join(cmd),
                "working_directory": str(cwd),
            }

            if not result["success"]:
                logger.error(f"Bearer command failed: {result['stderr']}")

            return result

        except FileNotFoundError:
            error_msg = (
                f"Bearer CLI not found. Please ensure '{self.binary_path}' "
                "is installed and in PATH."
            )
            logger.error(error_msg)
            return self._error_result(cmd, cwd, error_msg, -1)

        except Exception as e:
            error_msg = f"Error running Bearer command: {str(e)}"
            logger.error(error_msg)
            return self._error_result(cmd, cwd, error_msg, -1)

    @staticmethod
    def _error_result(
        cmd: list[str], cwd: Path, error_msg: str, exit_code: int
    ) -> dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "exit_code": exit_code,
            "stdout": "",
            "stderr": error_msg,
            "success": False,
            "command": " ".join(cmd),
            "working_directory": str(cwd),
        }


def get_executor() -> BearerExecutor:
    """Get a Bearer executor instance."""
    return BearerExecutor()


# Global executor instance (for backward compatibility)
executor = get_executor()
