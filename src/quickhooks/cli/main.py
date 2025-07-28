"""Main CLI module for QuickHooks.

This module defines the root command and sets up the CLI interface.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Optional

import typer

from quickhooks import __version__, console
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput
from quickhooks.runner import TestRunner
from quickhooks.cli.install import install_app
from quickhooks.agent_analysis.command import app as agent_analysis_app

# Create the main Typer app
app = typer.Typer(
    name="quickhooks",
    help="A streamlined TDD framework for Claude Code hooks with real-time feedback",
    add_completion=False,
)

# Add installation subcommands
app.add_typer(install_app, name="install")

# Add agent analysis subcommands
app.add_typer(agent_analysis_app, name="agents")


@app.command()
def version() -> None:
    """Show the version and exit."""
    console.print(f"QuickHooks v{__version__}")


@app.command()
def hello(name: Optional[str] = None) -> None:
    """Say hello.

    Args:
        name: Optional name to greet
    """
    if name:
        console.print(f"Hello, {name}!")
    else:
        console.print("Hello, World!")


@app.command()
def run(
    hook_path: Path = typer.Argument(..., help="Path to the hook file to execute"),
    input_data: str = typer.Option(
        "{}", "--input", "-i", help="JSON input data for the hook"
    ),
) -> None:
    """Run a hook with the provided input data.

    Args:
        hook_path: Path to the hook file to execute
        input_data: JSON input data for the hook
    """
    # Load the hook module
    spec = importlib.util.spec_from_file_location("hook_module", hook_path)
    if spec is None or spec.loader is None:
        console.print(
            f"Error: Could not load module from {hook_path}", style="bold red"
        )
        raise typer.Exit(code=1)

    hook_module = importlib.util.module_from_spec(spec)
    sys.modules["hook_module"] = hook_module
    spec.loader.exec_module(hook_module)

    # Find the hook class
    hook_class = None
    for attr_name in dir(hook_module):
        attr = getattr(hook_module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseHook) and attr != BaseHook:
            hook_class = attr
            break

    if hook_class is None:
        console.print("Error: No hook class found in the module", style="bold red")
        raise typer.Exit(code=1)

    # Parse input data
    try:
        input_dict = json.loads(input_data)
    except json.JSONDecodeError as e:
        console.print(f"Error: Invalid JSON input - {e}", style="bold red")
        raise typer.Exit(code=1)

    # Create hook instance and run
    hook_instance = hook_class()
    hook_input = HookInput(**input_dict)

    async def run_hook():
        result = await hook_instance.run(hook_input)
        console.print(json.dumps(result.dict(), indent=2))

    asyncio.run(run_hook())


@app.command()
def test(
    hooks_directory: Path = typer.Option(
        "./hooks", "--hooks-dir", "-d", help="Directory containing hook files"
    ),
    tests_directory: Path = typer.Option(
        "./tests", "--tests-dir", "-t", help="Directory containing test files"
    ),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter test files by name"
    ),
    parallel: bool = typer.Option(
        False, "--parallel", "-P", help="Run tests in parallel"
    ),
    timeout: int = typer.Option(
        30, "--timeout", "-T", help="Timeout for each test in seconds"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Report format: text, json, or junit"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """Run tests for hooks and generate reports.

    Args:
        hooks_directory: Directory containing hook files
        tests_directory: Directory containing test files
        pattern: Pattern to filter test files by name
        parallel: Run tests in parallel
        timeout: Timeout for each test in seconds
        format: Report format: text, json, or junit
        verbose: Enable verbose output
    """
    # Initialize the test runner
    runner = TestRunner(
        hooks_directory=hooks_directory,
        tests_directory=tests_directory,
        timeout=timeout,
    )

    # Run tests
    results = runner.run_tests(
        pattern=pattern,
        parallel=parallel,
        verbose=verbose,
    )

    # Generate and print report
    if format == "json":
        report = runner.generate_json_report(results)
        console.print(report)
    elif format == "junit":
        report = runner.generate_junit_report(results)
        console.print(report)
    else:  # text format
        report = runner.generate_text_report(results)
        console.print(report)

    # Exit with error code if there were test failures
    if any(not result.passed for result in results.values()):
        raise typer.Exit(code=1)


# This ensures the CLI works when run with `python -m quickhooks.cli.main`
if __name__ == "__main__":
    app()
