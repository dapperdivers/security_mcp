"""Tool handlers for Bearer MCP Server.

Provides clean, Pythonic implementations of Bearer CLI tool handlers using
abstract base classes, composition, and dependency injection.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import mcp.types as types

from ..core.bearer_executor import executor
from ..core.config import get_logger
from ..utils.path_utils import resolve_scan_path, validate_path


class ToolHandlerBase(ABC):
    """Abstract base class for all tool handlers.

    Provides common functionality and enforces consistent interfaces
    for all Bearer MCP tool handlers.
    """

    def __init__(self, name: str, executor_instance=None, logger=None):
        self.name = name
        self.executor = executor_instance or executor
        self.logger = logger or get_logger(f"{__name__}.{self.name}")

    @abstractmethod
    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Handle the tool invocation.

        Args:
            arguments: Tool arguments from MCP client

        Returns:
            List of TextContent responses

        Raises:
            ValueError: For invalid arguments or execution errors
        """
        pass

    def _create_text_content(self, text: str) -> types.TextContent:
        """Helper to create TextContent response."""
        return types.TextContent(type="text", text=text)

    def _create_error_response(self, error: str | Exception) -> list[types.TextContent]:
        """Create a standardized error response."""
        error_msg = str(error)
        self.logger.error(f"Error in {self.name}: {error_msg}")
        return [self._create_text_content(f"Error executing {self.name}: {error_msg}")]


class ScanHandlerBase(ToolHandlerBase):
    """Base class for scan-related handlers.

    Provides common scanning functionality and result processing.
    """

    def _build_scan_command(
        self, scan_path: Path, arguments: dict[str, Any]
    ) -> list[str]:
        """Build Bearer scan command arguments."""
        cmd_args = ["scan", str(scan_path)]

        # Add scanner types (SAST and secrets detection)
        cmd_args.extend(["--scanner", "sast,secrets"])

        # Add format option
        output_format = arguments.get("format", "json")
        cmd_args.extend(["--format", output_format])

        # Add flags for cleaner output
        cmd_args.extend(["--no-color", "--skip-test=false"])

        # Add optional parameters using walrus operator for conciseness
        if severity := arguments.get("severity"):
            cmd_args.extend(["--severity", severity])

        if rules := arguments.get("rules"):
            cmd_args.extend(["--only-rule", rules])

        if skip_rules := arguments.get("skip_rules"):
            cmd_args.extend(["--skip-rule", skip_rules])

        if output_file := arguments.get("output_file"):
            output_path = validate_path(output_file)
            cmd_args.extend(["--output", str(output_path)])

        if arguments.get("quiet", False):
            cmd_args.append("--quiet")

        return cmd_args

    def _process_scan_result(
        self, result: dict[str, Any], output_format: str
    ) -> list[types.TextContent]:
        """Process Bearer scan results based on exit code and format."""
        # Bearer returns exit code 1 when it finds security issues, which is expected
        # Exit code 0 means no issues found, 1 means issues found, other codes are errors
        has_findings = result["exit_code"] == 1
        no_findings = result["exit_code"] == 0
        scan_success = has_findings or no_findings

        return (
            self._process_successful_scan(result, output_format)
            if scan_success
            else self._process_failed_scan(result, output_format)
        )

    def _process_successful_scan(
        self, result: dict[str, Any], output_format: str
    ) -> list[types.TextContent]:
        """Process successful scan results."""
        output_text = result["stdout"].strip() if result["stdout"] else ""

        return (
            self._process_json_output(output_text)
            if output_format == "json"
            else self._process_text_output(output_text)
        )

    def _process_json_output(self, output_text: str) -> list[types.TextContent]:
        """Process JSON format scan output."""
        if not output_text:
            # No output means no issues found
            empty_result = {"findings": [], "summary": "No security issues detected"}
            return [self._create_text_content(json.dumps(empty_result, indent=2))]

        try:
            scan_results = json.loads(output_text)
            return [self._create_text_content(json.dumps(scan_results, indent=2))]
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Bearer JSON output: {e}")
            self.logger.error(f"Raw output: {output_text[:500]}")
            return [
                self._create_text_content(
                    f"Bearer scan completed but JSON parsing failed. Raw output:\n{output_text}"
                )
            ]

    def _process_text_output(self, output_text: str) -> list[types.TextContent]:
        """Process non-JSON format scan output."""
        return (
            [self._create_text_content(output_text)]
            if output_text
            else [
                self._create_text_content(
                    "Bearer scan completed successfully. No security issues detected."
                )
            ]
        )

    def _process_failed_scan(
        self, result: dict[str, Any], output_format: str
    ) -> list[types.TextContent]:
        """Process failed scan results."""
        error_response = {
            "error": True,
            "message": f"Bearer scan failed with exit code {result['exit_code']}",
            "stderr": result["stderr"],
            "command": result["command"],
        }

        if output_format == "json":
            return [self._create_text_content(json.dumps(error_response, indent=2))]

        error_text = (
            f"Bearer scan failed:\n\n"
            f"Command: {result['command']}\n"
            f"Exit code: {result['exit_code']}\n"
            f"Error: {result['stderr']}"
        )
        return [self._create_text_content(error_text)]


class BearerScanRepoHandler(ScanHandlerBase):
    """Handler for bearer_scan_repo tool.

    Scans the entire repository/workspace without requiring a path parameter.
    """

    def __init__(self, executor_instance=None, logger=None):
        super().__init__("bearer_scan_repo", executor_instance, logger)

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Execute repository-wide Bearer security scan."""
        try:
            scan_path = resolve_scan_path()
            self.logger.info(f"Scanning repository at: {scan_path}")

            cmd_args = self._build_scan_command(scan_path, arguments)
            result = await self.executor.run_command(cmd_args)

            output_format = arguments.get("format", "json")
            return self._process_scan_result(result, output_format)

        except Exception as e:
            return self._create_error_response(e)


class BearerScanHandler(ScanHandlerBase):
    """Handler for bearer_scan tool.

    Scans a specific directory or file path (requires path parameter).
    """

    def __init__(self, executor_instance=None, logger=None):
        super().__init__("bearer_scan", executor_instance, logger)

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Execute Bearer security scan on specific path."""
        path_str = arguments.get("path")

        if not path_str:
            return [
                self._create_text_content(
                    "Error: 'path' parameter is required for bearer_scan. "
                    "Use bearer_scan_repo to scan the entire repository."
                )
            ]

        try:
            scan_path = resolve_scan_path(path_str)
            self.logger.info(f"Scanning path: {scan_path}")

            cmd_args = self._build_scan_command(scan_path, arguments)
            result = await self.executor.run_command(cmd_args)

            output_format = arguments.get("format", "json")
            return self._process_scan_result(result, output_format)

        except Exception as e:
            return self._create_error_response(e)


class BearerVersionHandler(ToolHandlerBase):
    """Handler for bearer_version tool.

    Retrieves Bearer CLI version information.
    """

    def __init__(self, executor_instance=None, logger=None):
        super().__init__("bearer_version", executor_instance, logger)

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Get Bearer CLI version information."""
        try:
            result = await self.executor.run_command(["version"])

            if result["success"]:
                return [
                    self._create_text_content(
                        f"Bearer CLI version:\n{result['stdout']}"
                    )
                ]
            else:
                return [
                    self._create_text_content(
                        f"Failed to get Bearer version:\n{result['stderr']}"
                    )
                ]

        except Exception as e:
            return self._create_error_response(e)


class BearerListRulesHandler(ToolHandlerBase):
    """Handler for bearer_list_rules tool.

    Provides information about Bearer security rules.
    """

    def __init__(self, executor_instance=None, logger=None):
        super().__init__("bearer_list_rules", executor_instance, logger)

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Get Bearer security rules information."""
        try:
            language = arguments.get("language", "")
            rules_info = self._build_rules_info(language)
            return [self._create_text_content(rules_info)]

        except Exception as e:
            return self._create_error_response(e)

    def _build_rules_info(self, language: str = "") -> str:
        """Build comprehensive rules information text."""
        base_info = (
            "Bearer Security Rules Information:\n\n"
            "Bearer has 473+ security rules across multiple programming languages:\n"
            "- Ruby\n"
            "- JavaScript/TypeScript\n"
            "- Java\n"
            "- PHP\n"
            "- Go\n"
            "- Python\n\n"
            "Rules are categorized by:\n"
            "- OWASP Top 10 categories (A01-A10)\n"
            "- CWE (Common Weakness Enumeration) numbers\n"
            "- Language-specific vulnerabilities\n\n"
            "To use specific rules in scans:\n"
            '- Use --only-rule flag: bearer scan --only-rule "rule_id_1,rule_id_2" path/\n'
            '- Use --skip-rule flag: bearer scan --skip-rule "rule_id_1,rule_id_2" path/\n\n'
            "For the complete list of rules and their descriptions, visit:\n"
            "https://docs.bearer.com/reference/rules/"
        )

        if language:
            lang_lower = language.lower()
            language_info = (
                f"\n\nLanguage-specific information for {lang_lower}:\n\n"
                f"To scan only {lang_lower} files, Bearer automatically detects file types.\n"
                f"Common {lang_lower} rule categories include:\n"
                "- Code injection vulnerabilities\n"
                "- Authentication/authorization issues\n"
                "- Data exposure risks\n"
                "- Insecure configurations\n"
                "- Third-party library vulnerabilities\n\n"
                f"Example scan command for {lang_lower} projects:\n"
                "bearer scan --format json your_project_path/"
            )
            base_info += language_info

        return base_info


class BearerInitConfigHandler(ToolHandlerBase):
    """Handler for bearer_init_config tool.

    Initializes Bearer configuration file in a project.
    """

    def __init__(self, executor_instance=None, logger=None):
        super().__init__("bearer_init_config", executor_instance, logger)

    async def handle(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Initialize Bearer configuration in project."""
        config_path = arguments.get("path", ".")

        try:
            target_path = validate_path(config_path, must_exist=True)
            self.logger.info(f"Initializing Bearer config in: {target_path}")

            result = await self.executor.run_command(["init"], cwd=target_path)

            if result["success"]:
                return [
                    self._create_text_content(
                        f"Bearer configuration initialized in {target_path}:\n{result['stdout']}"
                    )
                ]
            else:
                return [
                    self._create_text_content(
                        f"Failed to initialize Bearer configuration:\n{result['stderr']}"
                    )
                ]

        except Exception as e:
            return self._create_error_response(e)


class ToolHandlerRegistry:
    """Registry for managing tool handlers.

    Provides a clean interface for registering and retrieving tool handlers
    using dependency injection and composition patterns.
    """

    def __init__(self, executor_instance=None, logger=None):
        self.executor = executor_instance or executor
        self.logger = logger or get_logger(f"{__name__}.registry")
        self._handlers: dict[str, ToolHandlerBase] = {}
        self._initialize_handlers()

    def _initialize_handlers(self) -> None:
        """Initialize all tool handlers with dependency injection."""
        handler_classes = {
            "bearer_scan_repo": BearerScanRepoHandler,
            "bearer_scan": BearerScanHandler,
            "bearer_version": BearerVersionHandler,
            "bearer_list_rules": BearerListRulesHandler,
            "bearer_init_config": BearerInitConfigHandler,
        }

        for name, handler_class in handler_classes.items():
            self._handlers[name] = handler_class(self.executor, self.logger)
            self.logger.debug(f"Registered handler: {name}")

    def get_handler(self, tool_name: str) -> ToolHandlerBase | None:
        """Get a tool handler by name.

        Args:
            tool_name: Name of the tool handler

        Returns:
            Tool handler instance or None if not found
        """
        return self._handlers.get(tool_name)

    async def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> list[types.TextContent]:
        """Handle a tool call using the appropriate handler.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments

        Returns:
            List of TextContent responses

        Raises:
            ValueError: If tool handler not found
        """
        arguments = arguments or {}

        if not (handler := self.get_handler(tool_name)):
            raise ValueError(f"Unknown tool: {tool_name}")

        try:
            return await handler.handle(arguments)
        except Exception as e:
            self.logger.error(f"Error handling tool {tool_name}: {e}")
            return [
                types.TextContent(type="text", text=f"Error executing {tool_name}: {e}")
            ]

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self._handlers.keys())


# Global handler registry instance
handler_registry = ToolHandlerRegistry()
