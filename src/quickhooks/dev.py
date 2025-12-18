"""Development server with hot-reload for quickhooks.

This module provides a development server that automatically reloads when files change.
It's designed to be used during development for a smooth workflow.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from watchfiles import Change, awatch

console = Console()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
)
logger = logging.getLogger("quickhooks.dev")

# Type variables
T = TypeVar("T")


class DevServer:
    """Development server with hot-reload functionality."""

    def __init__(
        self,
        watch_paths: list[str | Path],
        target: Callable[[], Awaitable[None]],
        reload_delay: float = 0.5,
        startup_messages: list[str] | None = None,
    ) -> None:
        """Initialize the development server.

        Args:
            watch_paths: List of paths to watch for changes
            target: Async function to run when starting/reloading
            reload_delay: Delay in seconds before reloading after file change
            startup_messages: Optional messages to display on startup
        """
        self.watch_paths = [Path(p) for p in watch_paths]
        self.target = target
        self.reload_delay = reload_delay
        self.startup_messages = startup_messages or []
        self.console = Console()
        self._current_task: asyncio.Task[None] | None = None
        self._should_reload = asyncio.Event()
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        """Run the development server."""
        self._register_signal_handlers()
        await self._print_startup_messages()

        # Start the initial task
        self._current_task = asyncio.create_task(self._run_target())

        # Start the file watcher
        asyncio.create_task(self._watch_files())

        try:
            while not self._stop_event.is_set():
                await self._should_reload.wait()
                self._should_reload.clear()

                # Cancel the current task if it's running
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._current_task

                # Add a small delay to ensure files are fully written
                await asyncio.sleep(self.reload_delay)

                # Clear the console and restart the target
                self.console.clear()
                self._current_task = asyncio.create_task(self._run_target())

        except asyncio.CancelledError:
            # Clean up on keyboard interrupt
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._current_task

            self.console.print("\n[green]Development server stopped[/green]")

    async def _run_target(self) -> None:
        """Run the target function with error handling."""
        try:
            await self.target()
        except Exception as e:
            self.console.print(f"\n[red]Error in target function: {e}[/red]")
            logger.exception("Error in target function")

    async def _watch_files(self) -> None:
        """Watch files for changes and trigger reloads."""
        # Convert Path objects to strings for watchfiles
        watch_dirs = [str(p) for p in self.watch_paths if p.is_dir()]
        watch_files = [str(p) for p in self.watch_paths if p.is_file()]

        async for changes in awatch(*watch_dirs, *watch_files):
            # Filter out temporary files and directories
            changes = [
                (change, path)
                for change, path in changes
                if not any(
                    part.startswith(".") and part not in {"__pycache__"}
                    for part in Path(path).parts
                )
            ]

            if changes:
                self.console.print("\n[blue]Detected changes:[/blue]")
                for change, path in changes:
                    change_type = {
                        Change.added: "[green]Added[/green]",
                        Change.modified: "[yellow]Modified[/yellow]",
                        Change.deleted: "[red]Deleted[/red]",
                    }.get(change, str(change))
                    self.console.print(f"  {change_type}: {path}")

                self._should_reload.set()

    async def _print_startup_messages(self) -> None:
        """Print startup messages."""
        if not self.startup_messages:
            return

        table = Table(show_header=False, box=None, show_edge=False, padding=(0, 1))
        table.add_column(style="cyan")

        for msg in self.startup_messages:
            table.add_row(msg)

        self.console.print("\n" + "=" * 50)
        self.console.print(Panel(table, border_style="blue"))
        self.console.print("=" * 50 + "\n")

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        def handle_signal():
            self.console.print("\n[yellow]Shutting down...[/yellow]")
            self._stop_event.set()
            if self._current_task:
                self._current_task.cancel()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)


async def run_dev_server(
    target: Callable[[], Awaitable[None]],
    watch_paths: list[str | Path] | None = None,
    reload_delay: float = 0.5,
    startup_messages: list[str] | None = None,
) -> None:
    """Run a development server with hot-reload.

    Args:
        target: Async function to run when starting/reloading
        watch_paths: List of paths to watch for changes (defaults to current directory)
        reload_delay: Delay in seconds before reloading after file change
        startup_messages: Optional messages to display on startup
    """
    if watch_paths is None:
        watch_paths = ["."]

    server = DevServer(
        watch_paths=watch_paths,
        target=target,
        reload_delay=reload_delay,
        startup_messages=startup_messages,
    )

    await server.run()


def dev_cli() -> None:
    """CLI entry point for the development server."""
    app = cyclopts.App(help="Development server with hot-reload")

    @app.command
    def run(
        path: str = Parameter(
            ".",
            help="Path to watch for changes (file or directory)",
        ),
        delay: float = Parameter(
            0.5,
            "--delay",
            "-d",
            help="Delay in seconds before reloading after file change",
        ),
    ) -> None:
        """Run the development server with hot-reload."""
        watch_path = Path(path).absolute()
        if not watch_path.exists():
            console.print(f"Error: Path {watch_path} does not exist", style="red")
            sys.exit(1)

        async def target():
            console = Console()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("Running development server...", total=None)
                console.print("\n[green]Development server started![/green]")
                console.print("  - Press Ctrl+C to stop")
                console.print(f"  - Watching: {watch_path}")
                console.print("  - Auto-reload enabled\n")

                # Keep the task running until cancelled
                try:
                    while True:
                        await asyncio.sleep(3600)  # Sleep for a long time
                except asyncio.CancelledError:
                    pass

        startup_messages = [
            "🚀 QuickHooks Development Server",
            "",
            f"Watching: {watch_path}",
            f"Reload delay: {delay}s",
            "",
            "[yellow]Press Ctrl+C to stop[/yellow]",
        ]

        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(
                run_dev_server(
                    target=target,
                    watch_paths=[str(watch_path)],
                    reload_delay=delay,
                    startup_messages=startup_messages,
                )
            )

    app()


if __name__ == "__main__":
    dev_cli()
