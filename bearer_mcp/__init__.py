"""Bearer MCP Server - Security scanning via Bearer CLI."""

from .server import BearerMCPServer, create_server
from .core.config import SERVER_NAME, SERVER_VERSION

__version__ = SERVER_VERSION
__all__ = [
    "BearerMCPServer",
    "create_server",
    "SERVER_NAME",
    "SERVER_VERSION",
]