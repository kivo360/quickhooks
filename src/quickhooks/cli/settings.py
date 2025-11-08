"""CLI commands for managing Claude Code settings.json files."""

import json
from pathlib import Path
from typing import Optional

import typer
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

app = typer.Typer(help="Manage Claude Code settings.json files")
console = Console()


@app.command()
def init(
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
):
    """Initialize a new Claude Code settings.json file."""
    settings_path = Path(path)

    if settings_path.exists() and not force:
        console.print(
            f"[yellow]Settings file already exists at {settings_path}[/yellow]"
        )
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Create default settings
    settings = ClaudeCodeSettings(
        schema_="https://json.schemastore.org/claude-code-settings.json",
    )

    manager = SettingsManager(settings_path)
    manager.settings = settings
    manager.save()

    console.print(f"[green]✅ Created settings file at {settings_path}[/green]")


@app.command()
def validate(
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
):
    """Validate a Claude Code settings.json file."""
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
            console.print("[yellow]⚠️  Schema file not found, skipped schema validation[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show(
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
):
    """Display current settings."""
    settings_path = Path(path)

    try:
        manager = SettingsManager(settings_path)
        manager.load()

        # Display as formatted JSON
        json_str = manager.to_json(indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)

        console.print(Panel(syntax, title=f"Settings: {settings_path}", border_style="blue"))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add_hook(
    event: str = typer.Argument(..., help="Hook event name (e.g., UserPromptSubmit)"),
    command: str = typer.Argument(..., help="Command to execute"),
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
    matcher: Optional[str] = typer.Option(
        None,
        "--matcher",
        "-m",
        help="Optional tool name matcher pattern",
    ),
    timeout: Optional[float] = typer.Option(
        None,
        "--timeout",
        "-t",
        help="Optional timeout in seconds",
    ),
):
    """Add a hook to settings.

    Examples:
        quickhooks settings add-hook UserPromptSubmit ".claude/hooks/my_hook.py"
        quickhooks settings add-hook PostToolUse "prettier --write" --matcher "Edit|Write"
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
            raise typer.Exit(1)

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
        raise typer.Exit(1)


@app.command()
def remove_hook(
    event: str = typer.Argument(..., help="Hook event name"),
    command_pattern: str = typer.Argument(..., help="Command pattern to remove"),
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
    matcher: Optional[str] = typer.Option(
        None,
        "--matcher",
        "-m",
        help="Optional tool name matcher pattern",
    ),
):
    """Remove hooks matching a pattern.

    Example:
        quickhooks settings remove-hook UserPromptSubmit "my_hook.py"
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
            raise typer.Exit(1)

        removed = manager.remove_hook(event_enum, command_pattern, matcher=matcher)
        manager.save()

        if removed:
            console.print(f"[green]✅ Removed hooks matching '{command_pattern}' from {event}[/green]")
        else:
            console.print(f"[yellow]No hooks found matching '{command_pattern}'[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_hooks(
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
    event: Optional[str] = typer.Option(
        None,
        "--event",
        "-e",
        help="Filter by event name",
    ),
):
    """List all hooks."""
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
                raise typer.Exit(1)

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
        raise typer.Exit(1)


@app.command()
def set_env(
    key: str = typer.Argument(..., help="Environment variable name"),
    value: str = typer.Argument(..., help="Environment variable value"),
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
):
    """Set an environment variable.

    Example:
        quickhooks settings set-env ANTHROPIC_MODEL claude-opus-4-1
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
        raise typer.Exit(1)


@app.command()
def list_env(
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
):
    """List all environment variables."""
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
        raise typer.Exit(1)


@app.command()
def add_permission(
    permission_type: str = typer.Argument(..., help="Permission type: allow, ask, or deny"),
    rule: str = typer.Argument(..., help="Permission rule (e.g., 'Bash(git add:*)')"),
    path: str = typer.Option(
        ".claude/settings.json",
        "--path",
        "-p",
        help="Path to settings.json file",
    ),
):
    """Add a permission rule.

    Examples:
        quickhooks settings add-permission allow "Bash(git add:*)"
        quickhooks settings add-permission deny "Read(*.env)"
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
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
