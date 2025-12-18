#!/usr/bin/env python3
"""
Manual test script to validate the grep-to-ripgrep hook functionality.
This provides a quick way to verify the hook works correctly.
"""

import json
import subprocess
from pathlib import Path


def test_hook(input_data, expected_contains=None, should_modify=True):
    """Test the hook with given input data."""
    hook_path = Path(__file__).parent / "hooks" / "grep_to_ripgrep.py"

    process = subprocess.run(
        ["python", str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if process.returncode != 0:
        print(f"❌ Hook failed: {process.stderr}")
        return False

    try:
        result = json.loads(process.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON output: {e}")
        print(f"Raw output: {process.stdout}")
        return False

    # Basic checks
    if not result.get("allowed", False):
        print("❌ Hook blocked execution unexpectedly")
        return False

    if result.get("modified", False) != should_modify:
        print(f"❌ Expected modified={should_modify}, got {result.get('modified')}")
        return False

    if expected_contains and expected_contains not in result.get("tool_input", {}).get(
        "command", ""
    ):
        print(f"❌ Expected command to contain '{expected_contains}'")
        print(f"   Got: {result.get('tool_input', {}).get('command')}")
        return False

    print("✅ Test passed")
    if should_modify:
        print(f"   Original: {input_data['tool_input']['command']}")
        print(f"   Transformed: {result['tool_input']['command']}")

    return True


def main():
    """Run manual tests."""
    print("🧪 Testing Grep to Ripgrep Hook\n")

    tests = [
        {
            "name": "Basic grep transformation",
            "input": {
                "tool_name": "Bash",
                "tool_input": {"command": "grep hello file.txt"},
            },
            "expected_contains": "rg hello file.txt",
            "should_modify": True,
        },
        {
            "name": "Grep with flags",
            "input": {
                "tool_name": "Bash",
                "tool_input": {"command": 'grep -rni "pattern" /src'},
            },
            "expected_contains": "rg -n -i pattern /src",
            "should_modify": True,
        },
        {
            "name": "Non-Bash tool (should not modify)",
            "input": {
                "tool_name": "NotBash",
                "tool_input": {"command": "grep pattern file.txt"},
            },
            "expected_contains": "grep pattern file.txt",
            "should_modify": False,
        },
        {
            "name": "Non-grep command (should not modify)",
            "input": {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
            "expected_contains": "ls -la",
            "should_modify": False,
        },
        {
            "name": "Complex grep with include pattern",
            "input": {
                "tool_name": "Bash",
                "tool_input": {"command": 'grep --include="*.py" "TODO" /src'},
            },
            "expected_contains": "rg --glob",
            "should_modify": True,
        },
        {
            "name": "Grep with sudo prefix",
            "input": {
                "tool_name": "Bash",
                "tool_input": {"command": "sudo grep -i pattern file.txt"},
            },
            "expected_contains": "sudo rg -i pattern file.txt",
            "should_modify": True,
        },
    ]

    passed = 0
    total = len(tests)

    for i, test in enumerate(tests, 1):
        print(f"Test {i}/{total}: {test['name']}")
        if test_hook(
            test["input"],
            test.get("expected_contains"),
            test.get("should_modify", True),
        ):
            passed += 1
        print()

    print(f"🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The hook is working correctly.")
        return True
    print("❌ Some tests failed. Check the implementation.")
    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
