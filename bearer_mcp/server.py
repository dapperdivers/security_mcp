"""Bearer MCP Server implementation."""

from typing import Any

import mcp.types as types
from mcp.server import Server

from .core.config import SERVER_NAME, get_logger
from .tools.definitions import get_mcp_tools
from .tools.handlers import ToolHandlerRegistry

logger = get_logger(__name__)


class BearerMCPServer:
    """Main Bearer MCP Server class."""
    
    def __init__(self):
        self.server = Server(SERVER_NAME)
        self.handler_registry = ToolHandlerRegistry()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available Bearer CLI tools."""
            return get_mcp_tools()
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: dict[str, Any] | None = None
        ) -> list[types.TextContent]:
            """Handle tool calls for Bearer CLI operations."""
            arguments = arguments or {}
            
            try:
                if handler := self.handler_registry.get_handler(name):
                    return await handler.handle(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {e}"
                )]
    
    def get_server_instance(self) -> Server:
        """Get the underlying MCP Server instance."""
        return self.server


def create_server() -> BearerMCPServer:
    """Factory function to create a Bearer MCP Server instance."""
    return BearerMCPServer()