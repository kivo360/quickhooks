"""Global installation commands for Context Portal integration with Claude Code."""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import platform

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from quickhooks.schema.validator import ClaudeSettingsValidator, validate_claude_settings_file
from quickhooks.schema.models import (
    ClaudeSettings, create_context_portal_hook_config, validate_settings_file
)

console = Console()

def get_claude_config_dir() -> Path:
    """Get the Claude Code configuration directory."""
    home = Path.home()
    claude_dir = home / ".claude"
    
    if not claude_dir.exists():
        claude_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"📁 Created Claude config directory: {claude_dir}")
    
    return claude_dir

def check_uv_available() -> bool:
    """Check if UV is available in PATH."""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def get_uv_python_executable() -> Optional[Path]:
    """Use UV to find and resolve the best Python executable."""
    if not check_uv_available():
        return None
    
    try:
        # First try to find Python using UV's discovery
        result = subprocess.run(['uv', 'python', 'find'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            python_path = result.stdout.strip()
            if python_path and Path(python_path).exists():
                console.print(f"🔍 UV found Python: {python_path}")
                return Path(python_path)
        
        # If find doesn't work, try to install a suitable Python version
        console.print("📦 UV installing suitable Python version...")
        result = subprocess.run(['uv', 'python', 'install', '3.11'], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            # Try to find the installed Python
            result = subprocess.run(['uv', 'python', 'find', '3.11'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python_path = result.stdout.strip()
                if python_path and Path(python_path).exists():
                    console.print(f"✅ UV installed and found Python: {python_path}")
                    return Path(python_path)
    
    except subprocess.TimeoutExpired:
        console.print("⚠️  UV Python resolution timed out")
    except Exception as e:
        console.print(f"⚠️  UV Python resolution error: {e}")
    
    return None

def get_current_venv() -> Optional[Path]:
    """Detect the current virtual environment."""
    # Check for conda environment
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix:
        return Path(conda_prefix)
    
    # Check for standard virtual environment
    virtual_env = os.environ.get('VIRTUAL_ENV')
    if virtual_env:
        return Path(virtual_env)
    
    # Check for Poetry virtual environment
    if hasattr(sys, 'prefix') and hasattr(sys, 'base_prefix'):
        if sys.prefix != sys.base_prefix:
            return Path(sys.prefix)
    
    # Check for pipenv
    pipenv_active = os.environ.get('PIPENV_ACTIVE')
    if pipenv_active:
        virtual_env = os.environ.get('VIRTUAL_ENV')
        if virtual_env:
            return Path(virtual_env)
    
    return None

def get_python_executable(venv_path: Optional[Path] = None) -> Path:
    """Get the best Python executable path, preferring UV resolution."""
    # First try UV for Python resolution if available
    if check_uv_available():
        console.print("🔍 Using UV for Python resolution...")
        uv_python = get_uv_python_executable()
        if uv_python:
            return uv_python
        console.print("⚠️  UV resolution failed, falling back to manual detection")
    else:
        console.print("ℹ️  UV not available, using manual Python detection")
    
    # Fallback to manual virtual environment detection
    if venv_path:
        if platform.system() == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
            if not python_exe.exists():
                python_exe = venv_path / "Scripts" / "python3.exe"
        else:
            python_exe = venv_path / "bin" / "python"
            if not python_exe.exists():
                python_exe = venv_path / "bin" / "python3"
        
        if python_exe.exists():
            return python_exe
    
    # Final fallback to system Python
    return Path(sys.executable)

def create_context_portal_hook_script(venv_path: Optional[Path], claude_dir: Path) -> Path:
    """Create the Context Portal hook script in Claude's directory."""
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    python_exe = get_python_executable(venv_path)
    
    # Get the source hook file
    source_hook = Path(__file__).parent.parent.parent.parent / "hooks" / "context_portal_memory.py"
    
    if not source_hook.exists():
        raise FileNotFoundError(f"Context Portal hook not found at: {source_hook}")
    
    # Create a wrapper script that uses the correct Python environment
    hook_script = hooks_dir / "context_portal_memory.py"
    
    # Create a wrapper that ensures the correct Python environment
    wrapper_content = f'''#!/usr/bin/env python3
"""
Global Context Portal Memory Hook for Claude Code
Auto-generated wrapper that uses the correct Python environment.

Original hook location: {source_hook}
Python executable: {python_exe}
Virtual environment: {venv_path or "System Python"}
"""

import sys
import os
import subprocess
import json

# Ensure we use the correct Python environment
PYTHON_EXECUTABLE = r"{python_exe}"
HOOK_SCRIPT = r"{source_hook}"

def main():
    """Run the Context Portal hook using the correct Python environment."""
    try:
        # Always use subprocess to run the hook with correct Python
        input_data = sys.stdin.read()
        
        result = subprocess.run(
            [PYTHON_EXECUTABLE, HOOK_SCRIPT],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            # Fallback to allow original command
            error_response = {{
                'allowed': True,
                'modified': False,
                'message': f'Context Portal hook error: {{result.stderr}}'
            }}
            print(json.dumps(error_response))
    
    except Exception as e:
        # Always fail-safe
        error_response = {{
            'allowed': True,
            'modified': False,
            'message': f'Context Portal hook error: {{str(e)}}'
        }}
        print(json.dumps(error_response))

if __name__ == '__main__':
    main()
'''
    
    with open(hook_script, 'w') as f:
        f.write(wrapper_content)
    
    # Make the script executable
    os.chmod(hook_script, 0o755)
    
    return hook_script


def get_current_claude_settings(claude_dir: Path) -> Dict[str, Any]:
    """Get current Claude Code settings."""
    settings_file = claude_dir / "settings.json"
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            console.print("⚠️ Warning: Invalid JSON in existing settings.json", style="yellow")
            return {}
    
    return {}

def update_claude_settings_with_hooks(claude_dir: Path, hook_script: Path) -> None:
    """Update Claude Code settings to include Context Portal hooks using schema validation."""
    settings_file = claude_dir / "settings.json"
    settings = get_current_claude_settings(claude_dir)
    
    # Initialize schema validator
    validator = ClaudeSettingsValidator()
    
    # Create Pydantic-validated hook configuration
    context_portal_tools = ["Bash", "Edit", "Write", "Read", "Grep", "Glob", "Task", "WebFetch", "WebSearch"]
    
    try:
        hook_config = create_context_portal_hook_config(
            tools=context_portal_tools,
            command=str(hook_script),
            timeout=30
        )
        console.print("✅ Created Pydantic-validated hook configuration")
    except ValueError as e:
        console.print(f"❌ Hook configuration error: {e}", style="red")
        raise typer.Exit(code=1)
    
    # Ensure hooks configuration exists
    if 'hooks' not in settings:
        settings['hooks'] = {}
    
    # Add PreToolUse hooks
    if 'PreToolUse' not in settings['hooks']:
        settings['hooks']['PreToolUse'] = []
    
    # Context Portal hook configuration using schema-generated structure
    context_portal_config = hook_config['PreToolUse'][0]
    
    # Check if Context Portal hook already exists
    existing_hook = None
    for i, existing_hook_config in enumerate(settings['hooks']['PreToolUse']):
        if any('context_portal_memory' in str(hook.get('command', '')) 
               for hook in existing_hook_config.get('hooks', [])):
            existing_hook = i
            break
    
    if existing_hook is not None:
        # Update existing hook
        settings['hooks']['PreToolUse'][existing_hook] = context_portal_config
        console.print("✅ Updated existing Context Portal hook configuration")
    else:
        # Add new hook
        settings['hooks']['PreToolUse'].append(context_portal_config)
        console.print("✅ Added Context Portal hook configuration")
    
    # Validate settings with both JSON schema and Pydantic
    is_valid, errors = validator.validate_settings(settings)
    if not is_valid:
        console.print("❌ Generated settings failed JSON schema validation:", style="red")
        for error in errors:
            console.print(f"   {error}", style="red")
        raise typer.Exit(code=1)
    
    # Additional Pydantic validation
    try:
        ClaudeSettings(**settings)
        console.print("✅ Settings passed Pydantic validation")
    except Exception as e:
        console.print(f"❌ Generated settings failed Pydantic validation: {e}", style="red")
        raise typer.Exit(code=1)
    
    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    console.print(f"📝 Updated Claude settings: {settings_file}")
    console.print("✅ Settings validated against official schema")

def install_context_portal_global() -> None:
    """Install Context Portal integration globally for Claude Code."""
    console.print(Panel(
        Text("🚀 Context Portal Global Installation", style="bold blue"),
        subtitle="Setting up automatic project memory for Claude Code"
    ))
    
    # Check UV availability first
    uv_available = check_uv_available()
    if uv_available:
        console.print("✅ UV package manager detected - using advanced Python resolution")
    else:
        console.print("ℹ️  UV not available - using manual environment detection")
    
    # Detect virtual environment
    venv_path = get_current_venv()
    if venv_path:
        console.print(f"🐍 Detected virtual environment: {venv_path}")
    else:
        console.print("⚠️  No virtual environment detected")
    
    # Get the best Python executable
    python_exe = get_python_executable(venv_path)
    console.print(f"🐍 Selected Python executable: {python_exe}")
    
    # Verify Python executable works
    try:
        result = subprocess.run([str(python_exe), '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            console.print(f"✅ Python version: {result.stdout.strip()}")
        else:
            console.print("⚠️  Warning: Python executable may not be working correctly")
    except Exception as e:
        console.print(f"⚠️  Warning: Could not verify Python executable: {e}")
    
    # Get Claude configuration directory
    claude_dir = get_claude_config_dir()
    console.print(f"📁 Claude config directory: {claude_dir}")
    
    try:
        # Create the hook script
        console.print("📝 Creating Context Portal hook script...")
        hook_script = create_context_portal_hook_script(venv_path, claude_dir)
        console.print(f"✅ Created hook script: {hook_script}")
        
        # Update Claude settings
        console.print("⚙️  Updating Claude Code settings...")
        update_claude_settings_with_hooks(claude_dir, hook_script)
        
        # Create global config template
        global_config_file = claude_dir / "context_portal_config.json"
        global_config = {
            "context_portal": {
                "database": {
                    "path": ".context-portal/project.db",
                    "max_size": "100MB",
                    "backup_interval": "daily"
                },
                "memory": {
                    "max_decisions": 1000,
                    "max_tasks": 500,
                    "max_patterns": 200,
                    "max_context_entries": 2000,
                    "cleanup_interval": "monthly"
                },
                "search": {
                    "default_limit": 10,
                    "max_limit": 50,
                    "enable_fuzzy_search": True
                },
                "categories": {
                    "decisions": [
                        "architecture", "technical", "tooling", 
                        "deployment", "security", "performance"
                    ],
                    "patterns": [
                        "design_patterns", "code_patterns", "test_patterns",
                        "deployment_patterns", "security_patterns"
                    ],
                    "tasks": [
                        "development", "testing", "deployment", 
                        "documentation", "maintenance", "refactoring"
                    ]
                }
            }
        }
        
        with open(global_config_file, 'w') as f:
            json.dump(global_config, f, indent=2)
        
        console.print(f"📋 Created global configuration: {global_config_file}")
        
        # Success message
        console.print(Panel(
            Text("🎉 Context Portal Installation Complete!", style="bold green") + 
            Text("\n\nThe Context Portal is now globally configured for Claude Code.\n") +
            Text("It will automatically:\n") +
            Text("• Capture context from all Claude Code tool usage\n") +
            Text("• Store decisions, patterns, and project knowledge\n") +
            Text("• Enhance future tool calls with relevant history\n") +
            Text("• Build a searchable project memory database\n\n") +
            Text("Next steps:\n") +
            Text("• Use Claude Code normally - context capture is automatic\n") +
            Text("• Check ") + Text(".context-portal/", style="code") + Text(" directories in your projects\n") +
            Text("• Use ") + Text("claude config", style="code") + Text(" to customize hook settings"),
            title="Installation Successful",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"❌ Installation failed: {e}", style="bold red")
        raise typer.Exit(code=1)

def uninstall_context_portal_global() -> None:
    """Uninstall Context Portal integration from Claude Code."""
    console.print(Panel(
        Text("🗑️  Context Portal Global Uninstallation", style="bold red"),
        subtitle="Removing Context Portal integration from Claude Code"
    ))
    
    claude_dir = get_claude_config_dir()
    
    try:
        # Remove hook script
        hook_script = claude_dir / "hooks" / "context_portal_memory.py"
        if hook_script.exists():
            hook_script.unlink()
            console.print(f"🗑️  Removed hook script: {hook_script}")
        
        # Update Claude settings to remove hooks
        settings_file = claude_dir / "settings.json"
        if settings_file.exists():
            settings = get_current_claude_settings(claude_dir)
            
            if 'hooks' in settings and 'PreToolUse' in settings['hooks']:
                # Remove Context Portal hooks
                original_count = len(settings['hooks']['PreToolUse'])
                settings['hooks']['PreToolUse'] = [
                    hook_config for hook_config in settings['hooks']['PreToolUse']
                    if not any('context_portal_memory' in str(hook.get('command', ''))
                             for hook in hook_config.get('hooks', []))
                ]
                
                removed_count = original_count - len(settings['hooks']['PreToolUse'])
                if removed_count > 0:
                    # Write updated settings
                    with open(settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)
                    console.print(f"🗑️  Removed {removed_count} Context Portal hook(s) from settings")
                else:
                    console.print("ℹ️  No Context Portal hooks found in settings")
        
        # Remove global config
        global_config_file = claude_dir / "context_portal_config.json"
        if global_config_file.exists():
            global_config_file.unlink()
            console.print(f"🗑️  Removed global configuration: {global_config_file}")
        
        console.print(Panel(
            Text("✅ Context Portal Uninstallation Complete!", style="bold green") +
            Text("\n\nContext Portal has been removed from Claude Code.\n") +
            Text("Existing project databases in ") + Text(".context-portal/", style="code") +
            Text(" directories are preserved."),
            title="Uninstallation Successful",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"❌ Uninstallation failed: {e}", style="bold red")
        raise typer.Exit(code=1)

def show_context_portal_status() -> None:
    """Show the current status of Context Portal installation."""
    console.print(Panel(
        Text("📊 Context Portal Status", style="bold blue"),
        subtitle="Current installation and configuration status"
    ))
    
    claude_dir = get_claude_config_dir()
    
    # Validate existing settings file
    settings_file = claude_dir / "settings.json"
    settings_valid = False
    validation_errors = []
    if settings_file.exists():
        settings_valid, validation_errors = validate_claude_settings_file(settings_file)
    
    # Check hook script
    hook_script = claude_dir / "hooks" / "context_portal_memory.py"
    hook_installed = hook_script.exists()
    
    # Check settings
    settings = get_current_claude_settings(claude_dir)
    hooks_configured = False
    if 'hooks' in settings and 'PreToolUse' in settings['hooks']:
        hooks_configured = any(
            any('context_portal_memory' in str(hook.get('command', ''))
                for hook in hook_config.get('hooks', []))
            for hook_config in settings['hooks']['PreToolUse']
        )
    
    # Check global config
    global_config_file = claude_dir / "context_portal_config.json"
    config_exists = global_config_file.exists()
    
    # Check UV availability
    uv_available = check_uv_available()
    uv_version = ""
    if uv_available:
        try:
            result = subprocess.run(['uv', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                uv_version = result.stdout.strip()
        except Exception:
            pass
    
    # Check virtual environment
    venv_path = get_current_venv()
    
    # Get Python executable with UV resolution info
    python_exe = get_python_executable(venv_path)
    
    # Display status
    status_lines = [
        f"Hook Script: {'✅ Installed' if hook_installed else '❌ Not found'} ({hook_script})",
        f"Claude Settings: {'✅ Configured' if hooks_configured else '❌ Not configured'}",
        f"Settings Schema: {'✅ Valid' if settings_valid else '❌ Invalid'}",
        f"Global Config: {'✅ Present' if config_exists else '❌ Missing'} ({global_config_file})",
        f"UV Package Manager: {'✅ Available' if uv_available else '❌ Not available'} ({uv_version})",
        f"Virtual Environment: {'✅ Detected' if venv_path else '⚠️  System Python'} ({venv_path or 'N/A'})",
        f"Python Executable: {python_exe}"
    ]
    
    # Verify Python executable
    try:
        result = subprocess.run([str(python_exe), '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            status_lines.append(f"Python Version: ✅ {result.stdout.strip()}")
        else:
            status_lines.append("Python Version: ❌ Not working")
    except Exception:
        status_lines.append("Python Version: ❌ Could not verify")
    
    overall_status = "✅ Fully Installed" if all([hook_installed, hooks_configured, config_exists, settings_valid]) else "⚠️  Partially Installed"
    
    console.print(f"\n📊 Overall Status: {overall_status}\n")
    for line in status_lines:
        console.print(f"   {line}")
    
    # Show validation errors if any
    if validation_errors:
        console.print("\n❌ Schema Validation Errors:", style="red")
        for error in validation_errors[:3]:  # Show first 3 errors
            console.print(f"   • {error}", style="red")
        if len(validation_errors) > 3:
            console.print(f"   ... and {len(validation_errors) - 3} more", style="red")
    
    if uv_available:
        console.print("\n🚀 UV Features: Advanced Python resolution and automatic downloads")
    else:
        console.print("\n💡 Install UV for better Python resolution: curl -LsSf https://astral.sh/uv/install.sh | sh")
    
    if not all([hook_installed, hooks_configured, config_exists, settings_valid]):
        console.print("\n💡 To fix issues, run: quickhooks install-global")

# CLI commands
install_app = typer.Typer(help="Context Portal installation commands")

@install_app.command("install-global")
def install_global():
    """Install Context Portal globally for Claude Code."""
    install_context_portal_global()

@install_app.command("uninstall-global")
def uninstall_global():
    """Uninstall Context Portal from Claude Code."""
    uninstall_context_portal_global()

@install_app.command("status")
def status():
    """Show Context Portal installation status."""
    show_context_portal_status()

if __name__ == "__main__":
    install_app()