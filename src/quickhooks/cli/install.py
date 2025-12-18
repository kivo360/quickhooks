"""Generic hook installation utilities for Claude Code."""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from quickhooks.schema.models import (
    ClaudeSettings,
    HookCommand,
    HookMatcher,
)
from quickhooks.schema.validator import (
    ClaudeSettingsValidator,
    validate_claude_settings_file,
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
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, timeout=5, check=False
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_uv_python_executable() -> Path | None:
    """Use UV to find and resolve the best Python executable."""
    if not check_uv_available():
        return None

    try:
        # First try to find Python using UV's discovery
        result = subprocess.run(
            ["uv", "python", "find"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            python_path = result.stdout.strip()
            if python_path and Path(python_path).exists():
                console.print(f"🔍 UV found Python: {python_path}")
                return Path(python_path)

        # If find doesn't work, try to install a suitable Python version
        console.print("📦 UV installing suitable Python version...")
        result = subprocess.run(
            ["uv", "python", "install", "3.11"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            # Try to find the installed Python
            result = subprocess.run(
                ["uv", "python", "find", "3.11"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
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


def get_current_venv() -> Path | None:
    """Detect the current virtual environment."""
    # Check for conda environment
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        return Path(conda_prefix)

    # Check for standard virtual environment
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return Path(virtual_env)

    # Check for Poetry virtual environment
    if hasattr(sys, "prefix") and hasattr(sys, "base_prefix"):
        if sys.prefix != sys.base_prefix:
            return Path(sys.prefix)

    # Check for pipenv
    pipenv_active = os.environ.get("PIPENV_ACTIVE")
    if pipenv_active:
        virtual_env = os.environ.get("VIRTUAL_ENV")
        if virtual_env:
            return Path(virtual_env)

    return None


def get_python_executable(venv_path: Path | None = None) -> Path:
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


def create_hook_script(
    source_hook: Path,
    claude_dir: Path | None = None,
    venv_path: Path | None = None,
    hook_name: str | None = None,
) -> Path:
    """Create a hook script in Claude's hooks directory.

    Args:
        source_hook: Path to the source hook file
        claude_dir: Claude config directory (defaults to ~/.claude or .claude)
        venv_path: Virtual environment path (optional)
        hook_name: Name for the hook script (defaults to source_hook.name)

    Returns:
        Path to the created hook script
    """
    if claude_dir is None:
        # Try local .claude first, then global
        local_claude = Path.cwd() / ".claude"
        claude_dir = local_claude if local_claude.exists() else get_claude_config_dir()

    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if not source_hook.exists():
        msg = f"Source hook not found at: {source_hook}"
        raise FileNotFoundError(msg)

    # Use provided name or source hook name
    hook_filename = hook_name or source_hook.name
    hook_script = hooks_dir / hook_filename

    # Check if hook uses PEP 723 (has # /// script marker) or uv run shebang
    is_pep723 = False
    has_uv_shebang = False
    try:
        with open(source_hook, encoding="utf-8") as f:
            first_line = f.readline().strip()
            # Check for uv run shebang (uv run -s or uv run -S)
            uv_in_shebang = "uv run -s" in first_line or "uv run -S" in first_line
            if first_line.startswith("#!") and uv_in_shebang:
                has_uv_shebang = True
            # Check for PEP 723 marker in first 20 lines
            if not has_uv_shebang:
                for i, line in enumerate(f):
                    if i >= 19:  # Already read first line, so 19 more
                        break
                    if "# /// script" in line:
                        is_pep723 = True
                        break
    except (OSError, UnicodeDecodeError):
        pass

    # If PEP 723 or has uv shebang, just copy the file directly (it's self-contained)
    if is_pep723 or has_uv_shebang:
        import shutil

        shutil.copy2(source_hook, hook_script)
        os.chmod(hook_script, 0o755)
        return hook_script

    # Otherwise, create a wrapper script
    python_exe = get_python_executable(venv_path)

    wrapper_content = f'''#!/usr/bin/env python3
"""
Hook wrapper for Claude Code
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
    """Run the hook using the correct Python environment."""
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
                'message': f'Hook error: {{result.stderr}}'
            }}
            print(json.dumps(error_response))

    except Exception as e:
        # Always fail-safe
        error_response = {{
            'allowed': True,
            'modified': False,
            'message': f'Hook error: {{str(e)}}'
        }}
        print(json.dumps(error_response))

if __name__ == '__main__':
    main()
'''

    with open(hook_script, "w") as f:
        f.write(wrapper_content)

    # Make the script executable
    os.chmod(hook_script, 0o755)

    return hook_script


def get_current_claude_settings(claude_dir: Path) -> dict[str, Any]:
    """Get current Claude Code settings."""
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            with open(settings_file) as f:
                return json.load(f)
        except json.JSONDecodeError:
            console.print(
                "⚠️ Warning: Invalid JSON in existing settings.json", style="yellow"
            )
            return {}

    return {}


def update_claude_settings_with_hook(
    hook_script: Path,
    tools: list[str] | None = None,
    hook_type: str = "PreToolUse",
    timeout: int = 30,
    claude_dir: Path | None = None,
    matcher: str | None = None,
) -> None:
    """Update Claude Code settings to include a hook configuration.

    Args:
        hook_script: Path to the hook script
        tools: List of tools to match (defaults to ["*"] for all tools)
        hook_type: Hook event type (defaults to "PreToolUse")
        timeout: Timeout in seconds (defaults to 30)
        claude_dir: Claude config directory (defaults to ~/.claude or .claude)
        matcher: Custom matcher pattern (overrides tools if provided)
    """
    if claude_dir is None:
        # Try local .claude first, then global
        local_claude = Path.cwd() / ".claude"
        claude_dir = local_claude if local_claude.exists() else get_claude_config_dir()

    settings_file = claude_dir / "settings.json"
    settings_dict = get_current_claude_settings(claude_dir)

    # Convert to ClaudeSettings model for type-safe manipulation
    try:
        claude_settings = ClaudeSettings(**settings_dict)
    except Exception as e:
        console.print(
            f"⚠️  Warning: Existing settings have validation issues: {e}",
            style="yellow",
        )
        console.print("Attempting to fix and continue...")
        # Create minimal valid settings
        claude_settings = ClaudeSettings()

    # Ensure hooks configuration exists
    if claude_settings.hooks is None:
        claude_settings.hooks = {}

    # Determine hook command
    is_pep723 = False
    has_uv_shebang = False
    try:
        with open(hook_script, encoding="utf-8") as f:
            first_line = f.readline().strip()
            # Check for uv run shebang (uv run -s or uv run -S)
            uv_in_shebang = "uv run -s" in first_line or "uv run -S" in first_line
            if first_line.startswith("#!") and uv_in_shebang:
                has_uv_shebang = True
            # Check for PEP 723 marker in first 20 lines
            if not has_uv_shebang:
                for i, line in enumerate(f):
                    if i >= 19:  # Already read first line, so 19 more
                        break
                    if "# /// script" in line:
                        is_pep723 = True
                        break
    except (OSError, UnicodeDecodeError):
        pass

    # Use explicit uv run -s for PEP 723 hooks or hooks with uv shebang
    if is_pep723 or has_uv_shebang:
        hook_command = f"uv run -s {hook_script}"
    else:
        hook_command = str(hook_script)

    # Create matcher pattern
    if matcher:
        hook_matcher_pattern = matcher
    elif tools:
        if len(tools) == 1:
            hook_matcher_pattern = tools[0]
        elif "*" in tools or len(tools) == 0:
            hook_matcher_pattern = "*"
        else:
            hook_matcher_pattern = "|".join(tools)
    else:
        hook_matcher_pattern = "*"

    # Create HookCommand and HookMatcher using Pydantic models
    hook_cmd = HookCommand(type="command", command=hook_command, timeout=timeout)
    hook_matcher = HookMatcher(matcher=hook_matcher_pattern, hooks=[hook_cmd])

    # Get or create hook list for this event type
    if hook_type not in claude_settings.hooks:
        claude_settings.hooks[hook_type] = []

    # Check if hook already exists (by script name)
    hook_name = hook_script.name
    existing_hook_idx = None
    for i, existing_matcher in enumerate(claude_settings.hooks[hook_type]):
        for hook in existing_matcher.hooks:
            if hook_name in hook.command:
                existing_hook_idx = i
                break
        if existing_hook_idx is not None:
            break

    if existing_hook_idx is not None:
        # Update existing hook matcher
        claude_settings.hooks[hook_type][existing_hook_idx] = hook_matcher
        console.print(f"✅ Updated existing hook configuration: {hook_name}")
    else:
        # Add new hook matcher to the list
        claude_settings.hooks[hook_type].append(hook_matcher)
        console.print(f"✅ Added hook configuration: {hook_name}")

    # Validate settings with JSON schema validator
    validator = ClaudeSettingsValidator()
    settings_dict = claude_settings.model_dump(by_alias=True, exclude_none=False)
    is_valid, errors = validator.validate_settings(settings_dict)
    if not is_valid:
        console.print(
            "❌ Generated settings failed JSON schema validation:", style="red"
        )
        for error in errors:
            console.print(f"   {error}", style="red")
        sys.exit(1)

    console.print("✅ Settings passed Pydantic and schema validation")

    # Write updated settings (using model_dump to preserve aliases and structure)
    with open(settings_file, "w") as f:
        json.dump(settings_dict, f, indent=2)

    console.print(f"📝 Updated Claude settings: {settings_file}")
    console.print("✅ Settings validated against official schema")


# CLI commands - functions are registered in main.py
# Keeping install_app for backwards compatibility but commands are registered in main CLI
install_app = cyclopts.App(help="Hook installation and management commands")


def install_hook(
    hook_path: Annotated[str, Parameter(help="Path to the source hook file")],
    tools: Annotated[
        str | None,
        Parameter("--tools", alias="-t", help="Comma-separated list of tools"),
    ] = None,
    hook_type: Annotated[
        str, Parameter("--hook-type", help="Hook event type")
    ] = "PreToolUse",
    timeout: Annotated[int, Parameter("--timeout", help="Timeout in seconds")] = 30,
    claude_dir: Annotated[
        str | None, Parameter("--claude-dir", help="Claude config directory")
    ] = None,
    matcher: Annotated[
        str | None, Parameter("--matcher", alias="-m", help="Custom matcher pattern")
    ] = None,
    venv_path: Annotated[
        str | None, Parameter("--venv", help="Virtual environment path")
    ] = None,
    hook_name: Annotated[
        str | None, Parameter("--name", alias="-n", help="Name for the hook script")
    ] = None,
    local: Annotated[
        bool, Parameter("--local", alias="-l", help="Use local .claude directory")
    ] = False,
    global_install: Annotated[
        bool, Parameter("--global", alias="-g", help="Use global ~/.claude directory")
    ] = False,
) -> None:
    """Install a hook to Claude Code hooks directory.

    Args:
        hook_path: Path to the source hook file
        tools: Comma-separated list of tools to match (e.g., "Bash,Edit,Write")
        hook_type: Hook event type (defaults to "PreToolUse")
        timeout: Timeout in seconds (defaults to 30)
        claude_dir: Claude config directory (defaults to ~/.claude or .claude)
        matcher: Custom matcher pattern (overrides tools if provided)
        venv_path: Virtual environment path (optional)
        hook_name: Name for the hook script (defaults to source hook name)
        local: Use local .claude directory instead of global
        global_install: Use global ~/.claude directory (overrides local)
    """
    source_hook = Path(hook_path)
    if not source_hook.exists():
        console.print(f"❌ Hook file not found: {hook_path}", style="red")
        sys.exit(1)

    # Parse tools if provided
    tools_list = None
    if tools:
        tools_list = [t.strip() for t in tools.split(",")]

    # Determine claude directory
    target_claude_dir = None
    if claude_dir:
        target_claude_dir = Path(claude_dir)
    elif global_install:
        target_claude_dir = get_claude_config_dir()
    elif local:
        target_claude_dir = Path.cwd() / ".claude"

    # Parse venv path if provided
    venv_path_obj = None
    if venv_path:
        venv_path_obj = Path(venv_path)

    console.print(
        Panel(
            Text("🪝 Installing Hook", style="bold blue"),
            subtitle=f"Installing {source_hook.name} to Claude Code",
        )
    )

    try:
        # Create hook script
        hook_script = create_hook_script(
            source_hook=source_hook,
            claude_dir=target_claude_dir,
            venv_path=venv_path_obj,
            hook_name=hook_name,
        )
        console.print(f"✅ Created hook script: {hook_script}")

        # Update settings
        update_claude_settings_with_hook(
            hook_script=hook_script,
            tools=tools_list,
            hook_type=hook_type,
            timeout=timeout,
            claude_dir=target_claude_dir,
            matcher=matcher,
        )

        console.print(
            Panel(
                Text("✅ Hook Installation Complete!", style="bold green")
                + Text(f"\n\nHook installed: {hook_script}\n")
                + Text(f"Event type: {hook_type}\n")
                + Text(f"Matcher: {matcher or (tools_list if tools_list else '*')}"),
                title="Success",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"❌ Installation failed: {e}", style="bold red")
        sys.exit(1)


def validate_settings(
    claude_dir: Annotated[
        str | None, Parameter("--claude-dir", help="Claude config directory")
    ] = None,
    local: Annotated[
        bool, Parameter("--local", alias="-l", help="Use local .claude directory")
    ] = False,
) -> None:
    """Validate Claude Code settings file.

    Args:
        claude_dir: Claude config directory (defaults to ~/.claude or .claude)
        local: Use local .claude directory instead of global
    """
    # Determine claude directory
    if claude_dir:
        target_claude_dir = Path(claude_dir)
    elif local:
        target_claude_dir = Path.cwd() / ".claude"
    else:
        local_claude = Path.cwd() / ".claude"
        target_claude_dir = (
            local_claude if local_claude.exists() else get_claude_config_dir()
        )

    settings_file = target_claude_dir / "settings.json"

    console.print(
        Panel(
            Text("🔍 Validating Settings", style="bold blue"),
            subtitle=f"Validating {settings_file}",
        )
    )

    if not settings_file.exists():
        console.print(f"❌ Settings file not found: {settings_file}", style="red")
        sys.exit(1)

    # Validate using both methods
    is_valid, errors = validate_claude_settings_file(settings_file)

    if is_valid:
        # Also try Pydantic validation
        try:
            settings = get_current_claude_settings(target_claude_dir)
            ClaudeSettings(**settings)
            console.print(
                Panel(
                    Text("✅ Settings are valid!", style="bold green")
                    + Text("\n\nPassed both JSON schema and Pydantic validation."),
                    title="Validation Successful",
                    border_style="green",
                )
            )
        except Exception as e:
            console.print(
                Panel(
                    Text(
                        "⚠️  Schema valid but Pydantic validation failed", style="yellow"
                    )
                    + Text(f"\n\nError: {e}"),
                    title="Partial Validation",
                    border_style="yellow",
                )
            )
    else:
        console.print(
            Panel(
                Text("❌ Settings validation failed", style="bold red")
                + Text("\n\nErrors:")
                + Text("\n".join(f"  • {error}" for error in errors)),
                title="Validation Failed",
                border_style="red",
            )
        )
        sys.exit(1)


def show_status(
    claude_dir: Annotated[
        str | None, Parameter("--claude-dir", help="Claude config directory")
    ] = None,
    local: Annotated[
        bool, Parameter("--local", alias="-l", help="Use local .claude directory")
    ] = False,
) -> None:
    """Show Claude Code hooks installation status.

    Args:
        claude_dir: Claude config directory (defaults to ~/.claude or .claude)
        local: Use local .claude directory instead of global
    """
    # Determine claude directory
    if claude_dir:
        target_claude_dir = Path(claude_dir)
    elif local:
        target_claude_dir = Path.cwd() / ".claude"
    else:
        local_claude = Path.cwd() / ".claude"
        target_claude_dir = (
            local_claude if local_claude.exists() else get_claude_config_dir()
        )

    console.print(
        Panel(
            Text("📊 Hook Installation Status", style="bold blue"),
            subtitle=f"Status for {target_claude_dir}",
        )
    )

    hooks_dir = target_claude_dir / "hooks"
    settings_file = target_claude_dir / "settings.json"

    # Check hooks directory
    hooks_installed = hooks_dir.exists() and list(hooks_dir.glob("*.py"))
    hook_count = len(list(hooks_dir.glob("*.py"))) if hooks_dir.exists() else 0

    # Check settings
    settings_exists = settings_file.exists()
    settings_valid = False
    hooks_configured = False
    hook_configs = []

    if settings_exists:
        settings_valid, _ = validate_claude_settings_file(settings_file)
        try:
            settings_dict = get_current_claude_settings(target_claude_dir)
            claude_settings = ClaudeSettings(**settings_dict)

            if claude_settings.hooks:
                for hook_type, hook_list in claude_settings.hooks.items():
                    for hook_matcher in hook_list:
                        for hook_cmd in hook_matcher.hooks:
                            hook_configs.append(
                                {
                                    "type": hook_type,
                                    "command": hook_cmd.command,
                                    "timeout": hook_cmd.timeout,
                                    "matcher": hook_matcher.matcher or "*",
                                }
                            )
                hooks_configured = len(hook_configs) > 0
        except Exception as e:
            console.print(f"⚠️  Warning: Could not parse settings: {e}", style="yellow")

    # Display status
    hooks_dir_status = "✅ Exists" if hooks_dir.exists() else "❌ Not found"
    hooks_installed_status = "✅" if hooks_installed else "❌"
    settings_exists_status = "✅ Exists" if settings_exists else "❌ Not found"
    settings_valid_status = "✅ Valid" if settings_valid else "❌ Invalid"
    hooks_configured_status = "✅" if hooks_configured else "❌"

    status_lines = [
        f"Hooks Directory: {hooks_dir_status} ({hooks_dir})",
        f"Hooks Installed: {hooks_installed_status} ({hook_count} files)",
        f"Settings File: {settings_exists_status} ({settings_file})",
        f"Settings Valid: {settings_valid_status}",
        f"Hooks Configured: {hooks_configured_status} "
        f"({len(hook_configs)} configurations)",
    ]

    console.print("\n" + "\n".join(f"   {line}" for line in status_lines))

    if hook_configs:
        console.print("\n[bold]Configured Hooks:[/bold]")
        for i, config in enumerate(hook_configs, 1):
            console.print(f"   {i}. {Path(config['command']).name}")
            console.print(f"      Type: {config['type']}")
            console.print(f"      Matcher: {config['matcher']}")
            console.print(f"      Timeout: {config['timeout']}s")
            console.print()


if __name__ == "__main__":
    install_app()
