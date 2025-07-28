#!/usr/bin/env python3
"""Test UV Python installation capabilities."""

import subprocess
import sys
from pathlib import Path

def test_uv_python_commands():
    """Test various UV Python commands."""
    print("🧪 Testing UV Python Commands")
    print("=" * 50)
    
    commands = [
        ("uv python list", "List installed Python versions"),
        ("uv python find", "Find current Python"),
        ("uv python find 3.11", "Find Python 3.11"),
        ("uv python find 3.12", "Find Python 3.12"), 
        ("uv python find 3.13", "Find Python 3.13")
    ]
    
    for command, description in commands:
        print(f"\n📝 {description}")
        print(f"Command: {command}")
        
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"Exit code: {result.returncode}")
            if result.stdout.strip():
                # Limit output to first few lines
                lines = result.stdout.strip().split('\n')[:5]
                for line in lines:
                    print(f"  {line}")
                if len(result.stdout.strip().split('\n')) > 5:
                    print("  ...")
            
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print("⚠️  Command timed out")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def test_uv_install_simulation():
    """Test what UV install command would do (without actually installing)."""
    print("\n🔧 UV Install Simulation")
    print("=" * 50)
    
    # Check what versions are available for install
    try:
        result = subprocess.run(
            ["uv", "python", "list", "--only-installed"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print("Currently installed Python versions:")
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        else:
            print("  No UV-managed Python versions found")
            
    except Exception as e:
        print(f"❌ Error checking installed versions: {e}")
    
    # Check available versions (without installing)
    print("\n📦 Available Python versions for download:")
    try:
        result = subprocess.run(
            ["uv", "python", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')[:10]  # Show first 10
            for line in lines:
                print(f"  {line}")
            if len(result.stdout.strip().split('\n')) > 10:
                print("  ... (and more)")
        
    except Exception as e:
        print(f"❌ Error checking available versions: {e}")

if __name__ == "__main__":
    test_uv_python_commands()
    test_uv_install_simulation()
    print("\n✅ UV Python capabilities test complete!")