#!/usr/bin/env python3
"""Simple test script to verify CLI commands are working."""

import subprocess
import sys
from pathlib import Path


def test_cli_commands():
    """Test the CLI commands."""
    # Get the project root directory
    project_root = Path(__file__).parent

    # Test the version command
    print("Testing version command...")
    result = subprocess.run(
        [sys.executable, "-m", "quickhooks.cli.main", "version"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Version command output: {result.stdout}")
    print(f"Version command error: {result.stderr}")
    print(f"Version command return code: {result.returncode}")

    # Test the hello command
    print("\nTesting hello command...")
    result = subprocess.run(
        [sys.executable, "-m", "quickhooks.cli.main", "hello", "Test"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Hello command output: {result.stdout}")
    print(f"Hello command error: {result.stderr}")
    print(f"Hello command return code: {result.returncode}")

    # Test the hello command without name
    print("\nTesting hello command without name...")
    result = subprocess.run(
        [sys.executable, "-m", "quickhooks.cli.main", "hello"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Hello command output: {result.stdout}")
    print(f"Hello command error: {result.stderr}")
    print(f"Hello command return code: {result.returncode}")

    print("\nCLI command tests completed.")


if __name__ == "__main__":
    test_cli_commands()
