#!/usr/bin/env python3
# /// script
# dependencies = [
#   "cyclopts>=0.3.0",
#   "rich>=13.7.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Setup script for QuickHooks PEP 723 Claude Code integration.

This script automates the installation of QuickHooks hooks with PEP 723 inline
dependencies into your Claude Code project.

Features:
- Installs self-contained hooks with inline dependencies
- Creates proper Claude Code settings.json
- Validates UV installation
- Tests hook execution
- Configures environment variables

Usage:
    # Install to current project
    uv run -s setup_pep723_hooks.py install

    # Install to specific directory
    uv run -s setup_pep723_hooks.py install --target /path/to/project

    # Test hooks
    uv run -s setup_pep723_hooks.py test

    # Uninstall
    uv run -s setup_pep723_hooks.py uninstall
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

console = Console()
app = cyclopts.App(help="Setup QuickHooks PEP 723 hooks for Claude Code")


def check_uv_installed() -> bool:
    """Check if UV is installed and available."""
    try:
        result = subprocess.run(
            ["uv", "--version"], check=False, capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def display_requirements_check() -> dict[str, bool]:
    """Display and return requirements check results."""
    table = Table(
        title="Requirements Check", show_header=True, header_style="bold magenta"
    )
    table.add_column("Requirement", style="cyan", width=30)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Description", width=50)

    checks = {}

    # Check UV
    checks["uv_installed"] = check_uv_installed()
    status_icon = "✅" if checks["uv_installed"] else "❌"
    status_color = "green" if checks["uv_installed"] else "red"
    table.add_row(
        "UV Package Manager",
        f"[{status_color}]{status_icon}[/]",
        "UV must be installed to run PEP 723 hooks",
    )

    # Check Python version
    import sys

    checks["python_version"] = sys.version_info >= (3, 12)
    py_status_icon = "✅" if checks["python_version"] else "❌"
    py_status_color = "green" if checks["python_version"] else "red"
    py_version_str = f"{sys.version_info.major}.{sys.version_info.minor}"
    table.add_row(
        "Python Version",
        f"[{py_status_color}]{py_status_icon}[/]",
        f"Python 3.12+ required (found {py_version_str})",
    )

    # Check GROQ API key (optional)
    checks["groq_api_key"] = bool(os.getenv("GROQ_API_KEY"))
    groq_status_icon = "✅" if checks["groq_api_key"] else "⚠️"
    groq_status_color = "green" if checks["groq_api_key"] else "yellow"
    table.add_row(
        "GROQ API Key",
        f"[{groq_status_color}]{groq_status_icon}[/]",
        "Optional - Required for agent analysis hook",
    )

    console.print(table)
    return checks


def get_quickhooks_dir() -> Path:
    """Get the QuickHooks repository directory."""
    # Assuming this script is in quickhooks/scripts/
    return Path(__file__).parent.parent


def install_hooks(target_dir: Path | None = None):
    """Install QuickHooks PEP 723 hooks to target directory."""
    if target_dir is None:
        target_dir = Path.cwd()

    console.print(
        f"\n[bold blue]Installing QuickHooks PEP 723 hooks to: {target_dir}[/bold blue]"
    )

    # Create .claude/hooks directory
    hooks_dir = target_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"✅ Created hooks directory: {hooks_dir}")

    # Copy hook files
    source_hooks_dir = get_quickhooks_dir() / ".claude" / "hooks"

    if not source_hooks_dir.exists():
        console.print(
            f"[red]❌ Source hooks directory not found: {source_hooks_dir}[/red]"
        )
        sys.exit(1)

    hook_files = [
        "example_hook_pep723.py",
        "agent_analysis_hook_pep723.py",
        "README.md",
    ]

    for hook_file in hook_files:
        source = source_hooks_dir / hook_file
        dest = hooks_dir / hook_file

        if not source.exists():
            console.print(f"[yellow]⚠️  Hook file not found: {source}[/yellow]")
            continue

        shutil.copy2(source, dest)
        if hook_file.endswith(".py"):
            dest.chmod(0o755)  # Make executable
        console.print(f"✅ Installed: {hook_file}")

    # Create or update settings.json
    settings_file = target_dir / ".claude" / "settings.json"
    source_settings = get_quickhooks_dir() / ".claude" / "settings.json"

    if settings_file.exists():
        overwrite_msg = (
            f"\n[yellow]Settings file already exists at "
            f"{settings_file}. Overwrite?[/yellow]"
        )
        if not Confirm.ask(overwrite_msg):
            console.print(
                "[yellow]Skipping settings.json (existing file preserved)[/yellow]"
            )
        else:
            shutil.copy2(source_settings, settings_file)
            console.print(f"✅ Updated settings: {settings_file}")
    else:
        shutil.copy2(source_settings, settings_file)
        console.print(f"✅ Created settings: {settings_file}")

    # Display next steps
    console.print("\n[bold green]✅ Installation complete![/bold green]")

    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("1. Edit .claude/settings.json to configure hooks")
    console.print("2. Set GROQ_API_KEY environment variable (for agent analysis)")
    console.print("3. Enable desired hooks by setting 'enabled: true'")
    console.print("4. Test hooks with: uv run -s setup_pep723_hooks.py test")

    # Show hook configuration
    console.print("\n[bold blue]Hook Configuration:[/bold blue]")
    console.print(
        Panel(
            """To enable a hook, edit .claude/settings.json:

{
  "hooks": {
    "user-prompt-submit": {
      "command": "uv run -s ${workspace}/.claude/hooks/example_hook_pep723.py",
      "enabled": true  // <-- Set to true
    }
  }
}""",
            title="Example Configuration",
            border_style="green",
        )
    )


def test_hooks(target_dir: Path | None = None):
    """Test QuickHooks PEP 723 hooks."""
    if target_dir is None:
        target_dir = Path.cwd()

    console.print(
        f"\n[bold blue]Testing QuickHooks PEP 723 hooks in: {target_dir}[/bold blue]"
    )

    hooks_dir = target_dir / ".claude" / "hooks"

    if not hooks_dir.exists():
        console.print(f"[red]❌ Hooks directory not found: {hooks_dir}[/red]")
        console.print("Run 'uv run -s setup_pep723_hooks.py install' first")
        sys.exit(1)

    # Test each hook
    hook_files = [
        "example_hook_pep723.py",
    ]

    # Test agent analysis only if GROQ_API_KEY is set
    if os.getenv("GROQ_API_KEY"):
        hook_files.append("agent_analysis_hook_pep723.py")

    test_input = {
        "session_id": "test_session",
        "tool_name": "test_tool",
        "tool_input": {},
        "hook_event_name": "user-prompt-submit",
        "transcript_path": "",
        "cwd": str(target_dir),
        "prompt": "Write a Python function that sorts a list",
        "context": "",
    }

    for hook_file in hook_files:
        hook_path = hooks_dir / hook_file

        if not hook_path.exists():
            console.print(f"[yellow]⚠️  Hook not found: {hook_file}[/yellow]")
            continue

        console.print(f"\n[bold cyan]Testing: {hook_file}[/bold cyan]")

        try:
            # Run hook with UV
            result = subprocess.run(
                ["uv", "run", "-s", str(hook_path)],
                check=False,
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse response
                try:
                    response = json.loads(result.stdout)
                    console.print("  ✅ Status: Success")
                    console.print(f"  📋 Response: {response}")

                    if result.stderr:
                        console.print(f"  📝 Logs: {result.stderr[:200]}")
                except json.JSONDecodeError:
                    console.print(f"  ⚠️  Invalid JSON response: {result.stdout[:200]}")
            else:
                console.print(f"  ❌ Status: Failed (exit code {result.returncode})")
                if result.stderr:
                    console.print(f"  📝 Error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            console.print("  ❌ Status: Timeout (>30s)")
        except Exception as e:
            console.print(f"  ❌ Status: Error - {e}")

    console.print("\n[bold green]✅ Testing complete![/bold green]")


def uninstall_hooks(target_dir: Path | None = None):
    """Uninstall QuickHooks PEP 723 hooks."""
    if target_dir is None:
        target_dir = Path.cwd()

    hooks_dir = target_dir / ".claude" / "hooks"

    if not hooks_dir.exists():
        console.print(f"[yellow]No hooks directory found at: {hooks_dir}[/yellow]")
        return

    if not Confirm.ask(
        f"\n[bold red]Remove all QuickHooks hooks from {hooks_dir}?[/bold red]"
    ):
        console.print("Uninstall cancelled.")
        return

    console.print(
        f"\n[bold blue]Uninstalling QuickHooks PEP 723 hooks from: "
        f"{target_dir}[/bold blue]"
    )

    # Remove hook files
    hook_files = [
        "example_hook_pep723.py",
        "agent_analysis_hook_pep723.py",
    ]

    for hook_file in hook_files:
        hook_path = hooks_dir / hook_file
        if hook_path.exists():
            hook_path.unlink()
            console.print(f"✅ Removed: {hook_file}")

    # Optionally remove settings.json
    settings_file = target_dir / ".claude" / "settings.json"
    if settings_file.exists() and Confirm.ask(
        "\n[yellow]Remove .claude/settings.json?[/yellow]"
    ):
        settings_file.unlink()
        console.print("✅ Removed: settings.json")

    console.print("\n[bold green]✅ Uninstall complete![/bold green]")


@app.command
def install(
    target: str | None = Parameter(
        None, "--target", "-t", help="Target directory (default: current directory)"
    ),
    skip_check: bool = Parameter(False, "--skip-check", help="Skip requirements check"),
):
    """Install QuickHooks PEP 723 hooks to Claude Code project."""
    console.print(
        Panel.fit(
            "[bold blue]QuickHooks PEP 723 Hooks - Installation[/bold blue]",
            border_style="blue",
        )
    )

    # Check requirements
    if not skip_check:
        console.print("\n[bold yellow]Checking requirements...[/bold yellow]")
        checks = display_requirements_check()

        if not checks.get("uv_installed"):
            console.print("\n[red]❌ UV is required but not installed[/red]")
            console.print("\nInstall UV:")
            console.print(
                "  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh"
            )
            console.print(
                "  Windows: powershell -ExecutionPolicy ByPass -c "
                '"irm https://astral.sh/uv/install.ps1 | iex"'
            )
            sys.exit(1)

        if not checks.get("python_version"):
            console.print("\n[red]❌ Python 3.12+ is required[/red]")
            sys.exit(1)

        if not Confirm.ask("\nProceed with installation?"):
            console.print("Installation cancelled.")
            sys.exit(0)

    # Install hooks
    target_dir = Path(target) if target else None
    install_hooks(target_dir)


@app.command
def test(
    target: str | None = Parameter(
        None, "--target", "-t", help="Target directory (default: current directory)"
    ),
):
    """Test QuickHooks PEP 723 hooks."""
    console.print(
        Panel.fit(
            "[bold blue]QuickHooks PEP 723 Hooks - Testing[/bold blue]",
            border_style="blue",
        )
    )

    target_dir = Path(target) if target else None
    test_hooks(target_dir)


@app.command
def uninstall(
    target: str | None = Parameter(
        None, "--target", "-t", help="Target directory (default: current directory)"
    ),
):
    """Uninstall QuickHooks PEP 723 hooks."""
    console.print(
        Panel.fit(
            "[bold blue]QuickHooks PEP 723 Hooks - Uninstall[/bold blue]",
            border_style="blue",
        )
    )

    target_dir = Path(target) if target else None
    uninstall_hooks(target_dir)


@app.command
def check():
    """Check system requirements for QuickHooks PEP 723 hooks."""
    console.print(
        Panel.fit(
            "[bold blue]QuickHooks PEP 723 Hooks - Requirements Check[/bold blue]",
            border_style="blue",
        )
    )

    display_requirements_check()


if __name__ == "__main__":
    app()
