"""QuickHooks - A streamlined TDD framework for Claude Code hooks.

This package provides a framework for developing and testing Claude Code hooks with
a focus on test-driven development and developer experience.
"""

from pathlib import Path

from rich.console import Console

# Version of quickhooks
__version__ = "0.2.0"

# Export main components
from .core import (
    ParallelProcessor,
    ProcessingMode,
    ProcessingPriority,
    ProcessingResult,
    ProcessingTask,
)
from .exceptions import (
    HookExecutionError,
    ProcessingError,
    QuickHooksError,
    ValidationError,
)
from .executor import ExecutionError, ExecutionResult, HookExecutor, PreToolUseInput
from .hooks import (
    BaseHook,
    DataParallelHook,
    MultiHookProcessor,
    ParallelHook,
    PipelineHook,
)
from .visualization import MermaidWorkflowGenerator

__all__ = [
    # Hook classes
    "BaseHook",
    "DataParallelHook",
    # Core execution
    "ExecutionError",
    "ExecutionResult",
    "HookExecutionError",
    "HookExecutor",
    # Visualization
    "MermaidWorkflowGenerator",
    "MultiHookProcessor",
    "ParallelHook",
    # Parallel processing
    "ParallelProcessor",
    "PipelineHook",
    "PreToolUseInput",
    "ProcessingError",
    "ProcessingMode",
    "ProcessingPriority",
    "ProcessingResult",
    "ProcessingTask",
    # Exceptions
    "QuickHooksError",
    "ValidationError",
    "__version__",
    "hello",
    "quickhooks_path",
]

# Path to the package root
quickhooks_path = Path(__file__).parent.absolute()

# Configure console output
console = Console()


def print_banner() -> None:
    """Print the QuickHooks banner."""
    banner = """
    \x1b[38;5;39m╔═╗╦ ╦╦═╗╦ ╦╔═╗╦ ╦╔╗╔╔═╗╔╦╗╔═╗╦  ╔═╗
    ╠╣ ║ ║╠╦╝║║║╠═╝╠═╣║║║╠╣  ║ ║ ║║  ╠╣
    ╚  ╚═╝╩╚═╚╩╝╩  ╩ ╩╝╚╝╚   ╩ ╚═╝╩  ╚  \x1b[0m
    """
    console.print(banner)
    console.print(f"[bold blue]QuickHooks v{__version__}[/bold blue]")
    console.print("A streamlined TDD framework for Claude Code hooks\n")


def hello() -> str:
    return "Hello from quickhooks!"


if __name__ == "__main__":
    print_banner()
