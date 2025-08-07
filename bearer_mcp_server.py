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
import mcp.types as types
from mcp.server import NotificationOptions, Server

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
                        "description": "Path to scan (directory or file). Relative paths are resolved from working directory."
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
                },
                "required": ["path"]
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
            description="List available Bearer security rules",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Filter rules by programming language (e.g., javascript, python, java)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter rules by category (e.g., security, privacy)"
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
    if not path_str:
        raise ValueError("Path is required for Bearer scan")
    
    try:
        # Validate and resolve path
        scan_path = validate_path(path_str, must_exist=True)
        
        # Build command arguments
        cmd_args = ["scan", str(scan_path)]
        
        # Add format option
        output_format = arguments.get("format", "json")
        cmd_args.extend(["--format", output_format])
        
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
        
        if result["success"]:
            if output_format == "json" and result["stdout"]:
                try:
                    # Try to parse and format JSON output
                    scan_results = json.loads(result["stdout"])
                    formatted_output = json.dumps(scan_results, indent=2)
                    return [types.TextContent(
                        type="text",
                        text=f"Bearer scan completed successfully:\n\n```json\n{formatted_output}\n```"
                    )]
                except json.JSONDecodeError:
                    pass
            
            return [types.TextContent(
                type="text",
                text=f"Bearer scan completed successfully:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Bearer scan failed:\n\nCommand: {result['command']}\nExit code: {result['exit_code']}\nError: {result['stderr']}"
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
    cmd_args = ["rules", "list"]
    
    # Add language filter
    if language := arguments.get("language"):
        cmd_args.extend(["--language", language])
    
    # Add category filter  
    if category := arguments.get("category"):
        cmd_args.extend(["--category", category])
    
    result = await run_bearer_command(cmd_args)
    
    if result["success"]:
        return [types.TextContent(
            type="text",
            text=f"Bearer rules:\n{result['stdout']}"
        )]
    else:
        return [types.TextContent(
            type="text",
            text=f"Failed to list Bearer rules:\n{result['stderr']}"
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


async def main():
    """Main entry point for the MCP server."""
    # Check for working directory from environment variable
    if working_dir := os.getenv("MCP_WORKING_DIRECTORY"):
        set_working_directory(working_dir)
        logger.info(f"Working directory set from environment: {working_dir}")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            NotificationOptions(prompts_changed=False, resources_changed=False, tools_changed=False),
        )


if __name__ == "__main__":
    asyncio.run(main())