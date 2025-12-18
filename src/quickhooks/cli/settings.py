"""CLI commands for managing Claude Code settings.json files."""

import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from quickhooks.claude_code import (
    ClaudeCodeSettings,
    HookCommand,
    HookEventName,
    SettingsManager,
)

app = cyclopts.App(help="Manage Claude Code settings.json files")
console = Console()


@app.command
def init(
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
    force: Annotated[
        bool, Parameter("--force", alias="-f", help="Overwrite existing file")
    ] = False,
):
    """Initialize a new Claude Code settings.json file.

    Parameters
    ----------
    path
        Path to settings.json file (default: ".claude/settings.json")
    force
        Overwrite existing file (default: False)
    """
    settings_path = Path(path)

    if settings_path.exists() and not force:
        console.print(
            f"[yellow]Settings file already exists at {settings_path}[/yellow]"
        )
        console.print("Use --force to overwrite")
        sys.exit(1)

    # Create default settings
    settings = ClaudeCodeSettings(
        schema_="https://json.schemastore.org/claude-code-settings.json",
    )

    manager = SettingsManager(settings_path)
    manager.settings = settings
    manager.save()

    console.print(f"[green]✅ Created settings file at {settings_path}[/green]")


@app.command
def validate(
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
):
    """Validate a Claude Code settings.json file.

    Parameters
    ----------
    path
        Path to settings.json file (default: ".claude/settings.json")
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()
        console.print(f"[green]✅ Settings file is valid: {settings_path}[/green]")

        # Try schema validation if available
        try:
            manager.validate_schema()
            console.print("[green]✅ Schema validation passed[/green]")
        except FileNotFoundError:
            console.print(
                "[yellow]⚠️  Schema file not found, skipped schema validation[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        sys.exit(1)


@app.command
def show(
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
):
    """Display current settings.

    Parameters
    ----------
    path
        Path to settings.json file (default: ".claude/settings.json")
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()

        # Display as formatted JSON
        json_str = manager.to_json(indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)

        console.print(
            Panel(syntax, title=f"Settings: {settings_path}", border_style="blue")
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def add_hook(
    event: str,
    command: str,
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
    matcher: Annotated[
        str | None,
        Parameter("--matcher", alias="-m", help="Optional tool name matcher pattern"),
    ] = None,
    timeout: Annotated[
        float | None, Parameter("--timeout", alias="-t", help="Optional timeout in seconds")
    ] = None,
):
    """Add a hook to settings.

    Examples:
        quickhooks settings add-hook UserPromptSubmit ".claude/hooks/my_hook.py"
        quickhooks settings add-hook PostToolUse "prettier --write" --matcher "Edit|Write"

    Parameters
    ----------
    event
        Hook event name (e.g., UserPromptSubmit)
    command
        Command to execute
    path
        Path to settings.json file (default: ".claude/settings.json")
    matcher
        Optional tool name matcher pattern
    timeout
        Optional timeout in seconds
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load(create_if_missing=True)

        # Validate event name
        try:
            event_enum = HookEventName(event)
        except ValueError:
            console.print(f"[red]Invalid event name: {event}[/red]")
            console.print("Valid events:")
            for e in HookEventName:
                console.print(f"  - {e.value}")
            sys.exit(1)

        # Create hook command
        hook_cmd = HookCommand(
            type="command",
            command=command,
            timeout=timeout,
        )

        manager.add_hook(event_enum, hook_cmd, matcher=matcher)
        manager.save()

        console.print(f"[green]✅ Added hook to {event}[/green]")
        console.print(f"   Command: {command}")
        if matcher:
            console.print(f"   Matcher: {matcher}")
        if timeout:
            console.print(f"   Timeout: {timeout}s")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def remove_hook(
    event: str,
    command_pattern: str,
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
    matcher: Annotated[
        str | None,
        Parameter("--matcher", alias="-m", help="Optional tool name matcher pattern"),
    ] = None,
):
    """Remove hooks matching a pattern.

    Example:
        quickhooks settings remove-hook UserPromptSubmit "my_hook.py"

    Parameters
    ----------
    event
        Hook event name
    command_pattern
        Command pattern to remove
    path
        Path to settings.json file (default: ".claude/settings.json")
    matcher
        Optional tool name matcher pattern
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()

        # Validate event name
        try:
            event_enum = HookEventName(event)
        except ValueError:
            console.print(f"[red]Invalid event name: {event}[/red]")
            sys.exit(1)

        removed = manager.remove_hook(event_enum, command_pattern, matcher=matcher)
        manager.save()

        if removed:
            console.print(
                f"[green]✅ Removed hooks matching '{command_pattern}' from {event}[/green]"
            )
        else:
            console.print(
                f"[yellow]No hooks found matching '{command_pattern}'[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def list_hooks(
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
    event: Annotated[
        str | None, Parameter("--event", alias="-e", help="Filter by event name")
    ] = None,
):
    """List all hooks.

    Parameters
    ----------
    path
        Path to settings.json file (default: ".claude/settings.json")
    event
        Filter by event name
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()

        event_enum = None
        if event:
            try:
                event_enum = HookEventName(event)
            except ValueError:
                console.print(f"[red]Invalid event name: {event}[/red]")
                sys.exit(1)

        hooks = manager.list_hooks(event_enum)

        if not hooks:
            console.print("[yellow]No hooks configured[/yellow]")
            return

        for event_name, matchers in hooks.items():
            console.print(f"\n[bold cyan]{event_name}[/bold cyan]")

            for matcher in matchers:
                if matcher.matcher:
                    console.print(f"  [dim]Matcher: {matcher.matcher}[/dim]")

                for cmd in matcher.hooks:
                    console.print(f"    • {cmd.command}")
                    if cmd.timeout:
                        console.print(f"      [dim]Timeout: {cmd.timeout}s[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def set_env(
    key: str,
    value: str,
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
):
    """Set an environment variable.

    Example:
        quickhooks settings set-env ANTHROPIC_MODEL claude-opus-4-1

    Parameters
    ----------
    key
        Environment variable name
    value
        Environment variable value
    path
        Path to settings.json file (default: ".claude/settings.json")
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load(create_if_missing=True)

        manager.set_env(key, value)
        manager.save()

        console.print(f"[green]✅ Set {key}={value}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def list_env(
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
):
    """List all environment variables.

    Parameters
    ----------
    path
        Path to settings.json file (default: ".claude/settings.json")
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()

        env_vars = manager.list_env()

        if not env_vars:
            console.print("[yellow]No environment variables configured[/yellow]")
            return

        table = Table(title="Environment Variables", show_header=True)
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="green")

        for key, value in sorted(env_vars.items()):
            table.add_row(key, value)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command
def add_permission(
    permission_type: str,
    rule: str,
    path: Annotated[
        str, Parameter("--path", alias="-p", help="Path to settings.json file")
    ] = ".claude/settings.json",
):
    """Add a permission rule.

    Examples:
        quickhooks settings add-permission allow "Bash(git add:*)"
        quickhooks settings add-permission deny "Read(*.env)"

    Parameters
    ----------
    permission_type
        Permission type: allow, ask, or deny
    rule
        Permission rule (e.g., 'Bash(git add:*)')
    path
        Path to settings.json file (default: ".claude/settings.json")
    """
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load(create_if_missing=True)

        manager.add_permission(permission_type, rule)
        manager.save()

        console.print(f"[green]✅ Added {permission_type} rule: {rule}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
