"""Bearer MCP tool definitions module.

This module contains the MCP tool definitions for all Bearer CLI tools.
It provides a centralized, maintainable way to define tool schemas that
comply with the MCP protocol specification.
"""

from mcp import types


# Tool definition constants
BEARER_SCAN_REPO_TOOL = types.Tool(
    name="bearer_scan_repo",
    description="Run Bearer security scan on the entire repository/workspace (no path parameter needed)",
    inputSchema={
        "type": "object",
        "properties": {
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
)

BEARER_SCAN_TOOL = types.Tool(
    name="bearer_scan",
    description="Run Bearer security scan on a specific directory or file path (path parameter required)",
    inputSchema={
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to scan (directory or file). Relative paths are resolved from /workspace."
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
)

BEARER_VERSION_TOOL = types.Tool(
    name="bearer_version",
    description="Get Bearer CLI version information",
    inputSchema={
        "type": "object",
        "properties": {}
    }
)

BEARER_LIST_RULES_TOOL = types.Tool(
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
)

BEARER_INIT_CONFIG_TOOL = types.Tool(
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


class ToolRegistry:
    """Registry for Bearer MCP tools.
    
    This class provides a centralized way to manage and access tool definitions
    while maintaining compatibility with the MCP protocol.
    """
    
    def __init__(self):
        """Initialize the tool registry with Bearer tools."""
        self._tools: dict[str, types.Tool] = {
            "bearer_scan_repo": BEARER_SCAN_REPO_TOOL,
            "bearer_scan": BEARER_SCAN_TOOL,
            "bearer_version": BEARER_VERSION_TOOL,
            "bearer_list_rules": BEARER_LIST_RULES_TOOL,
            "bearer_init_config": BEARER_INIT_CONFIG_TOOL,
        }
    
    def get_tool(self, name: str) -> types.Tool | None:
        """Get a specific tool by name.
        
        Args:
            name: The tool name to retrieve
            
        Returns:
            The tool definition or None if not found
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> list[types.Tool]:
        """Get all registered tool definitions.
        
        Returns:
            List of all tool definitions for MCP
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> list[str]:
        """Get all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            name: The tool name to check
            
        Returns:
            True if the tool is registered, False otherwise
        """
        return name in self._tools


def get_tool_registry() -> ToolRegistry:
    """Get a tool registry instance."""
    return ToolRegistry()


# Global registry instance (for backward compatibility)
tool_registry = get_tool_registry()


def get_mcp_tools() -> list[types.Tool]:
    """Get all Bearer MCP tool definitions.
    
    This is the main function used by the MCP server to retrieve
    all available tool definitions.
    
    Returns:
        List of types.Tool objects for MCP protocol
    """
    return tool_registry.get_all_tools()


def get_tool_definition(name: str) -> types.Tool | None:
    """Get a specific tool definition by name.
    
    Args:
        name: The tool name to retrieve
        
    Returns:
        The tool definition or None if not found
    """
    return tool_registry.get_tool(name)


# Export all tools as constants for direct access if needed
__all__ = [
    "BEARER_SCAN_REPO_TOOL",
    "BEARER_SCAN_TOOL", 
    "BEARER_VERSION_TOOL",
    "BEARER_LIST_RULES_TOOL",
    "BEARER_INIT_CONFIG_TOOL",
    "ToolRegistry",
    "tool_registry",
    "get_tool_registry",
    "get_mcp_tools",
    "get_tool_definition",
]