#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruff>=0.1.0",
#   "mypy>=1.0.0",
#   "pytest>=7.0.0",
#   "rich>=13.0.0",
# ]
# ///

"""
Post-task validation hook for Claude Code.

Runs quality checks on code changes:
- Linting with ruff
- Type checking with mypy
- Tests with pytest

Exit codes:
- 0: All checks passed
- 1: One or more checks failed
"""

import subprocess
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_ruff() -> tuple[bool, str]:
    """Run ruff linting and formatting check."""
    console.print("  [dim]Running ruff check...[/dim]")

    result = subprocess.run(
        ["ruff", "check", "."],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0, result.stdout + result.stderr


def run_mypy() -> tuple[bool, str]:
    """Run mypy type checking."""
    console.print("  [dim]Running mypy...[/dim]")

    result = subprocess.run(
        ["mypy", "."],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0, result.stdout


def run_pytest() -> tuple[bool, str]:
    """Run pytest test suite."""
    console.print("  [dim]Running pytest...[/dim]")

    result = subprocess.run(
        ["pytest", "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0, result.stdout


def main() -> int:
    """Run all validation checks."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Post-Task Validation[/bold cyan]\n"
            "Checking code quality and correctness",
            border_style="cyan",
        )
    )
    console.print()

    checks = [
        ("Linting (ruff)", run_ruff),
        ("Type Checking (mypy)", run_mypy),
        ("Tests (pytest)", run_pytest),
    ]

    results = []
    all_passed = True

    # Run all checks
    for name, check_fn in checks:
        console.print(f"[cyan]▶[/cyan] {name}")
        try:
            passed, output = check_fn()
            results.append((name, passed, output))
            all_passed = all_passed and passed

            if passed:
                console.print("  [green]✓[/green] Passed\n")
            else:
                console.print("  [red]✗[/red] Failed\n")

        except FileNotFoundError as e:
            console.print(f"  [yellow]⚠[/yellow] Tool not found: {e}\n")
            results.append((name, False, str(e)))
            all_passed = False
        except Exception as e:
            console.print(f"  [red]✗[/red] Error: {e}\n")
            results.append((name, False, str(e)))
            all_passed = False

    # Display summary table
    table = Table(title="Validation Summary", show_header=True)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")

    for name, passed, _ in results:
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        table.add_row(name, status)

    console.print(table)
    console.print()

    # Show detailed output for failures
    if not all_passed:
        console.print(
            Panel(
                "[bold red]Validation Failed[/bold red]\nReview the issues below:",
                border_style="red",
            )
        )
        console.print()

        for name, passed, output in results:
            if not passed and output:
                console.print(f"[bold yellow]━━━ {name} ━━━[/bold yellow]")
                console.print(output)
                console.print()

        return 1

    # Success!
    console.print(
        Panel(
            "[bold green]✓ All Validation Checks Passed![/bold green]\n"
            "Code is ready to commit.",
            border_style="green",
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
