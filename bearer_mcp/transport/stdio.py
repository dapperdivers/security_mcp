"""STDIO transport for Bearer MCP Server."""

import mcp.server.stdio
from mcp.server import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability

from ..core.config import SERVER_NAME, SERVER_VERSION, get_logger

logger = get_logger(__name__)


async def run_stdio_server(server_instance):
    """
    Run the MCP server using STDIO transport.
    
    Args:
        server_instance: The MCP Server instance to run
    """
    logger.info("Starting STDIO server")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server_instance.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                capabilities=ServerCapabilities(
                    tools=ToolsCapability()
                )
            )
        )