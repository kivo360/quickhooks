#!/usr/bin/env python3
"""Test UV integration for Python resolution."""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from quickhooks.cli.install import (
    check_uv_available,
    get_python_executable,
    get_uv_python_executable,
)


def test_uv_availability():
    """Test UV availability and basic functionality."""
    print("🧪 Testing UV Integration")
    print("=" * 50)

    # Test UV availability
    uv_available = check_uv_available()
    print(f"UV Available: {'✅ Yes' if uv_available else '❌ No'}")

    if uv_available:
        # Test UV Python discovery
        print("\n🔍 Testing UV Python discovery...")
        uv_python = get_uv_python_executable()
        if uv_python:
            print(f"UV found Python: ✅ {uv_python}")

            # Verify it works
            import subprocess

            try:
                result = subprocess.run(
                    [str(uv_python), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    print(f"Version check: ✅ {result.stdout.strip()}")
                else:
                    print("Version check: ❌ Failed")
            except Exception as e:
                print(f"Version check: ❌ Error: {e}")
        else:
            print("UV Python discovery: ❌ Failed")

    # Test the main function
    print("\n🔧 Testing get_python_executable()...")
    python_exe = get_python_executable()
    print(f"Selected Python: {python_exe}")

    # Test different scenarios
    print("\n📊 Testing different scenarios:")

    # Scenario 1: Current environment
    print("1. Current environment:")
    current_python = get_python_executable()
    print(f"   Result: {current_python}")

    # Scenario 2: No virtual environment specified
    print("2. No venv specified:")
    no_venv_python = get_python_executable(None)
    print(f"   Result: {no_venv_python}")

    print("\n✅ UV integration test complete!")


if __name__ == "__main__":
    test_uv_availability()
