#!/usr/bin/env python3
"""
Bearer CLI MCP Server

An MCP server that wraps the Bearer CLI security scanning tool, providing
tools to scan code for security vulnerabilities and sensitive data leaks.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import mcp.server.stdio
from mcp.server.sse import SseServerTransport
import mcp.types as types
from mcp.server import Server, InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability
from starlette.responses import HTMLResponse
import uvicorn

# Configure logging to stderr (required for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("bearer-mcp-server")

# Initialize the MCP server
server = Server("bearer-mcp-server")

# Global configuration
WORKING_DIRECTORY: Optional[Path] = None
BEARER_BINARY = "bearer"  # Assume bearer is in PATH or will be installed


def set_working_directory(path: str) -> None:
    """Set the working directory from MCP configuration."""
    global WORKING_DIRECTORY
    WORKING_DIRECTORY = Path(path).resolve()
    logger.info(f"Working directory set to: {WORKING_DIRECTORY}")


async def run_bearer_command(
    args: List[str], 
    cwd: Optional[Path] = None,
    capture_output: bool = True
) -> Dict[str, Any]:
    """
    Run a Bearer CLI command and return the result.
    
    Args:
        args: Command arguments (excluding 'bearer')
        cwd: Working directory for the command
        capture_output: Whether to capture stdout/stderr
        
    Returns:
        Dictionary with exit_code, stdout, stderr, and success status
    """
    if cwd is None:
        cwd = WORKING_DIRECTORY or Path.cwd()
    
    cmd = [BEARER_BINARY] + args
    logger.info(f"Running command: {' '.join(cmd)} in {cwd}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None
        )
        
        stdout, stderr = await process.communicate()
        
        result = {
            "exit_code": process.returncode,
            "stdout": stdout.decode('utf-8') if stdout else "",
            "stderr": stderr.decode('utf-8') if stderr else "",
            "success": process.returncode == 0,
            "command": " ".join(cmd),
            "working_directory": str(cwd)
        }
        
        if not result["success"]:
            logger.error(f"Bearer command failed: {result['stderr']}")
        
        return result
    
    except FileNotFoundError:
        error_msg = f"Bearer CLI not found. Please ensure 'bearer' is installed and in PATH."
        logger.error(error_msg)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": error_msg,
            "success": False,
            "command": " ".join(cmd),
            "working_directory": str(cwd)
        }
    except Exception as e:
        error_msg = f"Error running Bearer command: {str(e)}"
        logger.error(error_msg)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": error_msg,
            "success": False,
            "command": " ".join(cmd),
            "working_directory": str(cwd)
        }


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
        if not path.is_absolute() and WORKING_DIRECTORY:
            path = WORKING_DIRECTORY / path
        
        path = path.resolve()
        
        if must_exist and not path.exists():
            raise ValueError(f"Path does not exist: {path}")
            
        return path
    except Exception as e:
        raise ValueError(f"Invalid path '{path_str}': {str(e)}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Bearer CLI tools."""
    return [
        types.Tool(
            name="bearer_scan",
            description="Run Bearer security scan on a directory or file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to scan (directory or file). Defaults to /workspace. Relative paths are resolved from /workspace."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "yaml", "sarif", "html"],
                        "default": "json",
                        "description": "Output format for the scan results"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                        "description": "Minimum severity level to report"
                    },
                    "rules": {
                        "type": "string",
                        "description": "Comma-separated list of rule IDs to run (e.g., 'javascript_lang_eval,ruby_rails_logger')"
                    },
                    "skip_rules": {
                        "type": "string",
                        "description": "Comma-separated list of rule IDs to skip"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Path to save scan results to file"
                    },
                    "quiet": {
                        "type": "boolean",
                        "default": False,
                        "description": "Suppress progress output"
                    }
                }
            }
        ),
        types.Tool(
            name="bearer_version",
            description="Get Bearer CLI version information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="bearer_list_rules",
            description="Get information about Bearer security rules (rules are documented online at docs.bearer.com/reference/rules/)",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Optional: Language to get information about (e.g., javascript, python, java, ruby, php, go)"
                    }
                }
            }
        ),
        types.Tool(
            name="bearer_init_config",
            description="Initialize Bearer configuration file in the project",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to create configuration in (defaults to working directory)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Handle tool calls for Bearer CLI operations."""
    if arguments is None:
        arguments = {}
    
    try:
        if name == "bearer_scan":
            return await handle_bearer_scan(arguments)
        elif name == "bearer_version":
            return await handle_bearer_version(arguments)
        elif name == "bearer_list_rules":
            return await handle_bearer_list_rules(arguments)
        elif name == "bearer_init_config":
            return await handle_bearer_init_config(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def handle_bearer_scan(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle Bearer security scan tool."""
    path_str = arguments.get("path")
    
    try:
        # Default to /workspace if no path provided (Docker container volume)
        if not path_str:
            # When running in Docker, /workspace is the mounted volume
            scan_path = Path("/workspace")
            if not scan_path.exists():
                # Fallback to working directory if /workspace doesn't exist
                scan_path = WORKING_DIRECTORY or Path.cwd()
        else:
            # If a specific path is provided, resolve it relative to /workspace
            if not Path(path_str).is_absolute():
                # Make relative paths relative to /workspace
                scan_path = Path("/workspace") / path_str
            else:
                scan_path = Path(path_str)
            
            # Validate the path exists
            if not scan_path.exists():
                raise ValueError(f"Path does not exist: {scan_path}")
        
        # Build command arguments
        cmd_args = ["scan", str(scan_path)]
        
        # Add scanner types (SAST and secrets detection)
        cmd_args.extend(["--scanner", "sast,secrets"])
        
        # Add format option
        output_format = arguments.get("format", "json")
        cmd_args.extend(["--format", output_format])
        
        # Add no-color flag for cleaner output
        cmd_args.append("--no-color")
        
        # Don't skip test files
        cmd_args.append("--skip-test=false")
        
        # Add severity filter
        if severity := arguments.get("severity"):
            cmd_args.extend(["--severity", severity])
        
        # Add rules filter
        if rules := arguments.get("rules"):
            cmd_args.extend(["--only-rule", rules])
        
        # Add skip rules
        if skip_rules := arguments.get("skip_rules"):
            cmd_args.extend(["--skip-rule", skip_rules])
        
        # Add output file
        if output_file := arguments.get("output_file"):
            output_path = validate_path(output_file)
            cmd_args.extend(["--output", str(output_path)])
        
        # Add quiet flag
        if arguments.get("quiet", False):
            cmd_args.append("--quiet")
        
        # Run the scan
        result = await run_bearer_command(cmd_args)
        
        # Bearer returns exit code 1 when it finds security issues, which is expected behavior
        # Exit code 0 means no issues found, 1 means issues found, other codes are errors
        has_findings = result["exit_code"] == 1
        no_findings = result["exit_code"] == 0
        scan_success = has_findings or no_findings
        
        if scan_success:
            # Check stdout for JSON output (Bearer outputs JSON to stdout)
            output_text = result["stdout"].strip() if result["stdout"] else ""
            
            if output_format == "json":
                if output_text:
                    try:
                        # Parse the JSON output
                        scan_results = json.loads(output_text)
                        
                        # Return the raw JSON data for the calling LLM
                        # The LLM can then process this structured data
                        return [types.TextContent(
                            type="text",
                            text=json.dumps(scan_results, indent=2)
                        )]
                    except json.JSONDecodeError as e:
                        # If JSON parsing fails, log the error and return what we have
                        logger.error(f"Failed to parse Bearer JSON output: {e}")
                        logger.error(f"Raw output: {output_text[:500]}")
                        
                        # Still return the output, but note the parsing issue
                        return [types.TextContent(
                            type="text",
                            text=f"Bearer scan completed but JSON parsing failed. Raw output:\n{output_text}"
                        )]
                else:
                    # No output means no issues found - return empty JSON structure
                    empty_result = {
                        "findings": [],
                        "summary": "No security issues detected"
                    }
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(empty_result, indent=2)
                    )]
            else:
                # Non-JSON format - return as is
                if output_text:
                    return [types.TextContent(
                        type="text",
                        text=output_text
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="Bearer scan completed successfully. No security issues detected."
                    )]
        else:
            # Real error (not exit code 1)
            error_response = {
                "error": True,
                "message": f"Bearer scan failed with exit code {result['exit_code']}",
                "stderr": result["stderr"],
                "command": result["command"]
            }
            return [types.TextContent(
                type="text",
                text=json.dumps(error_response, indent=2) if output_format == "json" else f"Bearer scan failed:\n\nCommand: {result['command']}\nExit code: {result['exit_code']}\nError: {result['stderr']}"
            )]
    
    except Exception as e:
        raise ValueError(f"Bearer scan error: {str(e)}")


async def handle_bearer_version(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle Bearer version tool."""
    result = await run_bearer_command(["version"])
    
    if result["success"]:
        return [types.TextContent(
            type="text",
            text=f"Bearer CLI version:\n{result['stdout']}"
        )]
    else:
        return [types.TextContent(
            type="text",
            text=f"Failed to get Bearer version:\n{result['stderr']}"
        )]


async def handle_bearer_list_rules(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle Bearer list rules tool."""
    language = arguments.get("language", "")
    
    # Bearer CLI doesn't have a rules list command, so provide documentation info
    rules_info = """
Bearer Security Rules Information:

Bearer has 473+ security rules across multiple programming languages:
- Ruby
- JavaScript/TypeScript  
- Java
- PHP
- Go
- Python

Rules are categorized by:
- OWASP Top 10 categories (A01-A10)
- CWE (Common Weakness Enumeration) numbers
- Language-specific vulnerabilities

To use specific rules in scans:
- Use --only-rule flag: bearer scan --only-rule "rule_id_1,rule_id_2" path/
- Use --skip-rule flag: bearer scan --skip-rule "rule_id_1,rule_id_2" path/

For the complete list of rules and their descriptions, visit:
https://docs.bearer.com/reference/rules/
"""
    
    if language:
        language_specific_info = f"""
Language-specific information for {language.lower()}:

To scan only {language.lower()} files, Bearer automatically detects file types.
Common {language.lower()} rule categories include:
- Code injection vulnerabilities
- Authentication/authorization issues
- Data exposure risks
- Insecure configurations
- Third-party library vulnerabilities

Example scan command for {language.lower()} projects:
bearer scan --format json your_project_path/
"""
        rules_info += language_specific_info
    
    return [types.TextContent(
        type="text",
        text=rules_info
    )]


async def handle_bearer_init_config(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle Bearer init config tool."""
    config_path = arguments.get("path", ".")
    
    try:
        target_path = validate_path(config_path, must_exist=True)
        result = await run_bearer_command(["init"], cwd=target_path)
        
        if result["success"]:
            return [types.TextContent(
                type="text",
                text=f"Bearer configuration initialized in {target_path}:\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Failed to initialize Bearer configuration:\n{result['stderr']}"
            )]
    
    except Exception as e:
        raise ValueError(f"Config initialization error: {str(e)}")


async def create_sse_app():
    """Create Starlette app with SSE transport for Bearer MCP server."""
    # Check for working directory from environment variable
    if working_dir := os.getenv("MCP_WORKING_DIRECTORY"):
        set_working_directory(working_dir)
        logger.info(f"Working directory set from environment: {working_dir}")
    
    # Create SSE transport
    sse_transport = SseServerTransport("/messages/")
    
    # Import required Starlette components
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import Response
    
    # Define SSE handler
    async def handle_sse(request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="bearer-mcp-server",
                    server_version="1.0.1",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    )
                )
            )
        # Return empty response to avoid NoneType error
        return Response()
    
    # Define root handler
    async def root(request):
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bearer MCP Server</title>
        </head>
        <body>
            <h1>Bearer MCP Server</h1>
            <p>This is an MCP server that wraps the Bearer CLI security scanning tool.</p>
            <p>SSE endpoint: <code>/sse</code></p>
            <p>Messages endpoint: <code>/messages/</code></p>
            <p>Status: Running</p>
        </body>
        </html>
        """)
    
    # Create Starlette routes
    routes = [
        Route("/", endpoint=root, methods=["GET"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ]
    
    # Create and return Starlette app
    app = Starlette(routes=routes)
    return app


async def main():
    """Main entry point for the MCP server."""
    # Determine transport type from environment variable
    transport_type = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    if transport_type == "sse":
        # Run SSE server
        host = os.getenv("MCP_SSE_HOST", "localhost")
        port = int(os.getenv("MCP_SSE_PORT", "8000"))
        logger.info(f"Starting SSE server on {host}:{port}")
        
        app = await create_sse_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server_instance = uvicorn.Server(config)
        await server_instance.serve()
        
    else:
        # Run stdio server (default)
        logger.info("Starting stdio server")
        # Check for working directory from environment variable
        if working_dir := os.getenv("MCP_WORKING_DIRECTORY"):
            set_working_directory(working_dir)
            logger.info(f"Working directory set from environment: {working_dir}")
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="bearer-mcp-server",
                    server_version="1.0.1",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    )
                )
            )


if __name__ == "__main__":
    asyncio.run(main())