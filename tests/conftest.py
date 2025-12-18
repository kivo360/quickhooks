"""Test configuration and fixtures for QuickHooks."""

import asyncio
from collections.abc import Generator
from pathlib import Path

import pytest

from quickhooks import __version__
from quickhooks.cli.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session.

    This is needed for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def test_app():
    """Fixture for testing Cyclopts apps."""
    return app


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="module")
def src_dir(project_root: Path) -> Path:
    """Return the source directory."""
    return project_root / "src"


@pytest.fixture(scope="module")
def version() -> str:
    """Return the current version of the package."""
    return __version__
