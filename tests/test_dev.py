"""Tests for the development server functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quickhooks.dev import DevServer, run_dev_server


class TestDevServer:
    """Tests for the DevServer class."""

    @pytest.fixture
    def mock_target(self):
        """Create a mock target function."""
        return AsyncMock()

    @pytest.fixture
    def dev_server(self, mock_target, tmp_path):
        """Create a DevServer instance for testing."""
        # Create a test file to watch
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        return DevServer(
            watch_paths=[str(tmp_path)],
            target=mock_target,
            reload_delay=0.1,
            startup_messages=["Test server"],
        )

    @pytest.mark.asyncio
    async def test_run_calls_target(self, dev_server, mock_target):
        """Test that the target function is called when run."""
        # Create a task for the server
        server_task = asyncio.create_task(dev_server.run())

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Signal the server to stop
        dev_server._stop_event.set()
        dev_server._should_reload.set()

        # Wait for the server to stop
        await server_task

        # Verify the target was called
        mock_target.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_file_change_triggers_reload(self, dev_server, mock_target, tmp_path):
        """Test that file changes trigger a reload."""
        # Create a task for the server
        server_task = asyncio.create_task(dev_server.run())

        # Wait for the server to start
        await asyncio.sleep(0.1)

        # Modify the test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("modified")

        # Wait for the watcher to detect the change
        await asyncio.sleep(0.2)

        # Signal the server to stop
        dev_server._stop_event.set()

        # Wait for the server to stop
        await server_task

        # The target should be called twice: once on start, once after reload
        assert mock_target.await_count == 2


@pytest.mark.asyncio
async def test_run_dev_server():
    """Test the run_dev_server convenience function."""
    mock_target = AsyncMock()

    # Create a task for the server
    server_task = asyncio.create_task(
        run_dev_server(
            target=mock_target,
            watch_paths=["."],
            reload_delay=0.1,
        )
    )

    # Give it a moment to start
    await asyncio.sleep(0.1)

    # Cancel the server
    server_task.cancel()

    try:
        await server_task
    except asyncio.CancelledError:
        pass

    # Verify the target was called
    mock_target.assert_awaited_once()


@pytest.mark.asyncio
async def test_dev_cli(runner, monkeypatch):
    """Test the dev CLI command."""
    # Mock the run_dev_server function
    mock_run = AsyncMock()
    monkeypatch.setattr("quickhooks.dev.run_dev_server", mock_run)

    # Import the CLI module to get the app
    from quickhooks.dev import dev_cli

    # Create a mock for the Typer app
    mock_app = MagicMock()

    # Patch the app to use our mock
    with patch("quickhooks.dev.app", mock_app):
        # Call the dev_cli function
        dev_cli()

    # Verify the app was called
    mock_app.assert_called_once()
