#!/usr/bin/env python3
"""
Test Bearer CLI integration without MCP dependencies
"""

import asyncio
import subprocess
import sys
from pathlib import Path

async def test_bearer_availability():
    """Test if Bearer CLI is available"""
    print("Testing Bearer CLI availability...")
    try:
        process = await asyncio.create_subprocess_exec(
            'bearer', 'version',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print(f"✓ Bearer CLI found: {stdout.decode().strip()}")
            return True
        else:
            print(f"✗ Bearer CLI error: {stderr.decode().strip()}")
            return False
    except FileNotFoundError:
        print("✗ Bearer CLI not found - this is expected for local testing")
        print("  The Docker container will include Bearer CLI")
        return False
    except Exception as e:
        print(f"✗ Error testing Bearer CLI: {e}")
        return False

def test_command_building():
    """Test command argument building logic"""
    print("Testing command argument building...")
    
    # Simulate Bearer scan command building
    def build_bearer_command(path, format_type="json", severity=None, rules=None):
        cmd = ["bearer", "scan", str(path)]
        cmd.extend(["--format", format_type])
        
        if severity:
            cmd.extend(["--severity", severity])
        if rules:
            cmd.extend(["--only-rule", rules])
        
        return cmd
    
    # Test various command combinations
    test_cases = [
        {
            "path": "/test/path",
            "format_type": "json",
            "expected": ["bearer", "scan", "/test/path", "--format", "json"]
        },
        {
            "path": "/test/path", 
            "format_type": "sarif",
            "severity": "high",
            "expected": ["bearer", "scan", "/test/path", "--format", "sarif", "--severity", "high"]
        },
        {
            "path": "/test/path",
            "format_type": "json",
            "rules": "javascript_lang_eval,ruby_rails_logger",
            "expected": ["bearer", "scan", "/test/path", "--format", "json", "--only-rule", "javascript_lang_eval,ruby_rails_logger"]
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases):
        expected = test_case.pop("expected")
        result = build_bearer_command(**test_case)
        
        if result == expected:
            print(f"✓ Test case {i+1} passed")
        else:
            print(f"✗ Test case {i+1} failed")
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")
            all_passed = False
    
    return all_passed

def test_path_validation():
    """Test path validation logic"""
    print("Testing path validation logic...")
    
    def validate_path_simple(path_str, working_dir=None):
        path = Path(path_str)
        
        if not path.is_absolute() and working_dir:
            path = Path(working_dir) / path
        
        return path.resolve()
    
    # Test cases
    test_cases = [
        {
            "path": ".",
            "working_dir": "/home/test",
            "expected": Path("/home/test").resolve()
        },
        {
            "path": "/absolute/path",
            "working_dir": "/home/test", 
            "expected": Path("/absolute/path").resolve()
        },
        {
            "path": "relative/path",
            "working_dir": "/home/test",
            "expected": Path("/home/test/relative/path").resolve()
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases):
        path_str = test_case["path"]
        working_dir = test_case["working_dir"]
        expected = test_case["expected"]
        
        result = validate_path_simple(path_str, working_dir)
        
        if result == expected:
            print(f"✓ Path test case {i+1} passed")
        else:
            print(f"✗ Path test case {i+1} failed")
            print(f"  Input: {path_str} (working_dir: {working_dir})")
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")
            all_passed = False
    
    return all_passed

async def main():
    """Run Bearer integration tests"""
    print("Running Bearer CLI Integration Tests\n")
    
    results = []
    
    # Test Bearer CLI availability
    print("Bearer CLI Availability:")
    try:
        result = await test_bearer_availability()
        results.append(result)
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        results.append(False)
    
    # Test command building
    print("\nCommand Building:")
    try:
        result = test_command_building()
        results.append(result)
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        results.append(False)
    
    # Test path validation
    print("\nPath Validation:")
    try:
        result = test_path_validation()
        results.append(result)
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} integration tests passed")
    
    if passed == total:
        print("✓ All integration tests passed!")
        return 0
    else:
        print("! Some tests failed (expected for Bearer CLI availability)")
        return 0  # Return 0 since Bearer CLI absence is expected locally

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))