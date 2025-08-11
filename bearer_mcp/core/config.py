"""Configuration and constants for Bearer MCP Server."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ServerConfig:
    """Bearer MCP Server configuration."""
    name: str = "bearer-mcp-server"
    version: str = "1.0.1"
    bearer_binary: str = "bearer"
    log_level: int = logging.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# Global server configuration
config = ServerConfig()

# Logging configuration
logging.basicConfig(
    level=config.log_level,
    format=config.log_format,
    stream=sys.stderr
)

# Server metadata (for backward compatibility)
SERVER_NAME = config.name
SERVER_VERSION = config.version

# Bearer CLI configuration (for backward compatibility)
BEARER_BINARY = config.bearer_binary

# Global working directory
_working_directory: Path | None = None


def get_working_directory() -> Path | None:
    """Get the current working directory."""
    return _working_directory


def set_working_directory(path: str) -> None:
    """Set the working directory from MCP configuration."""
    global _working_directory
    _working_directory = Path(path).resolve()
    logger = get_logger(SERVER_NAME)
    logger.info(f"Working directory set to: {_working_directory}")


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name or SERVER_NAME)