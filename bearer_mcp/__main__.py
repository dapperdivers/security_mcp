"""Main entry point for Bearer MCP Server."""

import asyncio
import os
import sys
from enum import Enum

from .core.config import get_logger, set_working_directory
from .server import create_server
from .transport import run_sse_server, run_stdio_server

logger = get_logger(__name__)


class TransportType(Enum):
    """Available transport types."""
    STDIO = "stdio"
    SSE = "sse"


def configure_environment():
    """Configure environment variables and working directory."""
    if working_dir := os.getenv("MCP_WORKING_DIRECTORY"):
        set_working_directory(working_dir)
        logger.info(f"Working directory set from environment: {working_dir}")


async def main():
    """Main entry point for the MCP server."""
    # Configure environment
    configure_environment()
    
    # Create server instance
    bearer_server = create_server()
    server_instance = bearer_server.get_server_instance()
    
    # Determine transport type
    transport_env = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    try:
        transport_type = TransportType(transport_env)
    except ValueError:
        logger.error(f"Invalid transport type: {transport_env}. Using STDIO.")
        transport_type = TransportType.STDIO
    
    # Run server with appropriate transport
    await (
        run_sse_server(server_instance)
        if transport_type == TransportType.SSE
        else run_stdio_server(server_instance)
    )


def run():
    """Run the Bearer MCP server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()