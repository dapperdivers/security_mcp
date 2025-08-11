"""SSE (Server-Sent Events) transport for Bearer MCP Server."""

import os

import uvicorn
from mcp.server import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.types import ServerCapabilities, ToolsCapability
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, Response
from starlette.routing import Mount, Route

from ..core.config import SERVER_NAME, SERVER_VERSION, get_logger

logger = get_logger(__name__)


class SSETransportServer:
    """SSE transport server for MCP."""

    def __init__(self, server_instance, host: str = "localhost", port: int = 8000):
        self.server = server_instance
        self.host = host
        self.port = port
        self.transport: SseServerTransport | None = None
        self.app: Starlette | None = None

    async def _handle_sse(self, request):
        """Handle SSE connections."""
        async with self.transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await self.server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name=SERVER_NAME,
                    server_version=SERVER_VERSION,
                    capabilities=ServerCapabilities(tools=ToolsCapability()),
                ),
            )
        return Response()

    async def _handle_root(self, request):
        """Handle root endpoint with status page."""
        return HTMLResponse(
            f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bearer MCP Server</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 
                                 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .status {{
                    background: #4CAF50;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    display: inline-block;
                }}
                .endpoint {{
                    background: #f0f0f0;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-family: monospace;
                }}
                .info {{
                    margin: 20px 0;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Bearer MCP Server</h1>
                <div class="info">
                    <p><strong>Status:</strong> <span class="status">Running</span></p>
                    <p><strong>Version:</strong> {SERVER_VERSION}</p>
                    <p><strong>Transport:</strong> SSE (Server-Sent Events)</p>
                    <p><strong>Host:</strong> {self.host}:{self.port}</p>
                </div>
                <div class="info">
                    <h3>Endpoints</h3>
                    <p>SSE endpoint: <span class="endpoint">/sse</span></p>
                    <p>Messages endpoint: <span class="endpoint">/messages/</span></p>
                </div>
                <div class="info">
                    <h3>Description</h3>
                    <p>This is an MCP server that wraps the Bearer CLI 
                    security scanning tool, providing tools to scan code for 
                    security vulnerabilities and sensitive data leaks.</p>
                </div>
            </div>
        </body>
        </html>
        """
        )

    def create_app(self) -> Starlette:
        """Create and configure the Starlette application."""
        self.transport = SseServerTransport("/messages/")

        routes = [
            Route("/", endpoint=self._handle_root, methods=["GET"]),
            Route("/sse", endpoint=self._handle_sse, methods=["GET"]),
            Mount("/messages/", app=self.transport.handle_post_message),
        ]

        self.app = Starlette(routes=routes)
        return self.app

    async def serve(self):
        """Start the SSE server."""
        logger.info(f"Starting SSE server on {self.host}:{self.port}")

        app = self.create_app()
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


async def run_sse_server(server_instance):
    """
    Run the MCP server using SSE transport.

    Args:
        server_instance: The MCP Server instance to run
    """
    host = os.getenv("MCP_SSE_HOST", "localhost")
    port = int(os.getenv("MCP_SSE_PORT", "8000"))

    sse_server = SSETransportServer(server_instance, host, port)
    await sse_server.serve()
