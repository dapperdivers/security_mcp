"""Bearer MCP Server - Security scanning via Bearer CLI."""

from .core.config import SERVER_NAME, SERVER_VERSION
from .server import BearerMCPServer, create_server

__version__ = SERVER_VERSION
__all__ = [
    "BearerMCPServer",
    "create_server",
    "SERVER_NAME",
    "SERVER_VERSION",
]
