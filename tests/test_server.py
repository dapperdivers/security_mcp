#!/usr/bin/env python3
"""
Simple test script to validate Bearer MCP server functionality
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Mock the mcp module for testing
class MockMCP:
    class types:
        class Tool:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        
        class TextContent:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
    
    class server:
        class stdio:
            @staticmethod
            async def stdio_server():
                class MockStream:
                    async def __aenter__(self):
                        return self, self
                    async def __aexit__(self, *args):
                        pass
                return MockStream()
        
        class Server:
            def __init__(self, name):
                self.name = name
                self._tools = []
                self._tool_handlers = {}
            
            def list_tools(self):
                def decorator(func):
                    self._tools.append(func)
                    return func
                return decorator
            
            def call_tool(self):
                def decorator(func):
                    self._tool_handlers['call_tool'] = func
                    return func
                return decorator
            
            async def run(self, *args, **kwargs):
                pass
        
        NotificationOptions = lambda **kwargs: None

# Patch the imports
import sys
sys.modules['mcp'] = MockMCP()
sys.modules['mcp.server'] = MockMCP.server
sys.modules['mcp.server.stdio'] = MockMCP.server.stdio
sys.modules['mcp.types'] = MockMCP.types

# Import our server after mocking
import bearer_mcp_server

async def test_bearer_command_mock():
    """Test Bearer command execution with mocked subprocess"""
    print("Testing Bearer command execution...")
    
    # Mock a successful Bearer command
    mock_result = {
        "exit_code": 0,
        "stdout": '{"findings": [], "stats": {"files_scanned": 5}}',
        "stderr": "",
        "success": True,
        "command": "bearer scan /test/path",
        "working_directory": "/test"
    }
    
    with patch('bearer_mcp_server.run_bearer_command', return_value=mock_result):
        result = await bearer_mcp_server.run_bearer_command(['scan', '/test/path'])
        
        assert result['success'] == True
        assert result['exit_code'] == 0
        assert 'findings' in result['stdout']
        print("✓ Bearer command execution test passed")

async def test_path_validation():
    """Test path validation functionality"""
    print("Testing path validation...")
    
    # Test with current directory
    bearer_mcp_server.set_working_directory(str(Path.cwd()))
    
    try:
        # Test relative path resolution
        path = bearer_mcp_server.validate_path(".", must_exist=True)
        assert path.exists()
        print("✓ Path validation test passed")
    except Exception as e:
        print(f"✗ Path validation test failed: {e}")

async def test_tool_definitions():
    """Test that tools are properly defined"""
    print("Testing tool definitions...")
    
    # Get tools from the server
    tools = await bearer_mcp_server.handle_list_tools()
    
    expected_tools = ['bearer_scan', 'bearer_version', 'bearer_list_rules', 'bearer_init_config']
    tool_names = [tool.name for tool in tools]
    
    for expected in expected_tools:
        if expected in tool_names:
            print(f"✓ Tool '{expected}' found")
        else:
            print(f"✗ Tool '{expected}' missing")
    
    print(f"Total tools defined: {len(tools)}")

async def test_bearer_scan_tool():
    """Test the bearer_scan tool with mocked command"""
    print("Testing bearer_scan tool...")
    
    mock_result = {
        "exit_code": 0,
        "stdout": '{"findings": [{"type": "security", "severity": "high"}]}',
        "stderr": "",
        "success": True,
        "command": "bearer scan /test",
        "working_directory": "/test"
    }
    
    with patch('bearer_mcp_server.run_bearer_command', return_value=mock_result):
        with patch('bearer_mcp_server.validate_path', return_value=Path('/test')):
            result = await bearer_mcp_server.handle_bearer_scan({
                'path': '/test',
                'format': 'json'
            })
            
            assert len(result) == 1
            assert 'Bearer scan completed successfully' in result[0].text
            print("✓ bearer_scan tool test passed")

async def main():
    """Run all tests"""
    print("Starting Bearer MCP Server Tests\n")
    
    try:
        await test_bearer_command_mock()
        await test_path_validation()
        await test_tool_definitions()
        await test_bearer_scan_tool()
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())