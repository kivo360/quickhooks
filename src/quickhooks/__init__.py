"""QuickHooks - A streamlined TDD framework for Claude Code hooks with real-time feedback.

This package provides a framework for developing and testing Claude Code hooks with
a focus on test-driven development and developer experience.
"""

from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console

# Version of quickhooks
__version__ = "0.1.0"

# Export main components
from .executor import ExecutionError, ExecutionResult, HookExecutor, PreToolUseInput

__all__ = [
    "__version__",
    "quickhooks_path",
    "hello",
    "ExecutionError",
    "ExecutionResult", 
    "HookExecutor",
    "PreToolUseInput",
]

# Path to the package root
quickhooks_path = Path(__file__).parent.absolute()

# Configure console output
console = Console()


def print_banner() -> None:
    """Print the QuickHooks banner."""
    banner = """
    [38;5;39m╔═╗╦ ╦╦═╗╦ ╦╔═╗╦ ╦╔╗╔╔═╗╔╦╗╔═╗╦  ╔═╗
    ╠╣ ║ ║╠╦╝║║║╠═╝╠═╣║║║╠╣  ║ ║ ║║  ╠╣ 
    ╚  ╚═╝╩╚═╚╩╝╩  ╩ ╩╝╚╝╚   ╩ ╚═╝╩  ╚  [0m
    """
    console.print(banner)
    console.print(f"[bold blue]QuickHooks v{__version__}[/bold blue]")
    console.print("A streamlined TDD framework for Claude Code hooks\n")


def hello() -> str:
    return "Hello from quickhooks!"


if __name__ == "__main__":
    print_banner()
