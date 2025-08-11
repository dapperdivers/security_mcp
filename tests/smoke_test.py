#!/usr/bin/env python3
"""
Smoke test to verify the MCP server can import and initialize properly
"""

import sys


def test_import():
    """Test that the server can be imported"""
    print("Testing server import...")
    try:
        import bearer_mcp_server

        print("✓ Server imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_server_initialization():
    """Test that the server can be initialized"""
    print("Testing server initialization...")
    try:
        import bearer_mcp_server

        server = bearer_mcp_server.server
        print(f"✓ Server initialized: {server.name}")
        return True
    except Exception as e:
        print(f"✗ Server initialization failed: {e}")
        return False


def test_working_directory():
    """Test working directory functionality"""
    print("Testing working directory setup...")
    try:
        import bearer_mcp_server

        bearer_mcp_server.set_working_directory("/tmp")
        wd = bearer_mcp_server.WORKING_DIRECTORY
        print(f"✓ Working directory set to: {wd}")
        return True
    except Exception as e:
        print(f"✗ Working directory test failed: {e}")
        return False


def main():
    """Run smoke tests"""
    print("Running Bearer MCP Server Smoke Tests\n")

    tests = [test_import, test_server_initialization, test_working_directory]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("✓ All smoke tests passed - server is ready!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
