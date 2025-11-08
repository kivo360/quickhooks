#!/usr/bin/env python3
"""
Version Bumping Utility for QuickHooks

This script handles version bumping for the project since UV doesn't
have a built-in version command.

Usage:
    python scripts/bump_version.py patch
    python scripts/bump_version.py minor
    python scripts/bump_version.py major
    python scripts/bump_version.py --get-version
"""

import re
import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console

console = Console()


class VersionPart(str, Enum):
    """Version bump types."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch) tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version tuple into string."""
    return f"{major}.{minor}.{patch}"


def bump_version_part(
    current_version: str, part: str
) -> str:
    """Bump a specific part of the version."""
    major, minor, patch = parse_version(current_version)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1

    return format_version(major, minor, patch)


def get_version_from_pyproject(pyproject_path: Path) -> str:
    """Extract version from pyproject.toml."""
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    content = pyproject_path.read_text()

    # Look for version in [project] section
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("version = "):
            # Extract version from quotes
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', line)
            if version_match:
                return version_match.group(1)

    raise ValueError("Version not found in pyproject.toml")


def update_version_in_pyproject(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    content = pyproject_path.read_text()

    # Replace version line
    updated_content = re.sub(
        r'(version\s*=\s*)["\']([^"\']+)["\']',
        f'version = "{new_version}"',
        content,
        count=1,
    )

    pyproject_path.write_text(updated_content)


def update_version_in_init(package_path: Path, new_version: str) -> None:
    """Update version in __init__.py if it exists."""
    init_file = package_path / "src" / "quickhooks" / "__init__.py"

    if not init_file.exists():
        return

    content = init_file.read_text()

    # Check if __version__ exists
    if "__version__" in content:
        # Update existing version
        updated_content = re.sub(
            r'__version__\s*=\s*["\']([^"\']+)["\']',
            f'__version__ = "{new_version}"',
            content,
        )
        init_file.write_text(updated_content)
    else:
        # Add version if not present
        lines = content.split("\n")
        # Insert after module docstring if present, otherwise at the top
        insert_index = 0
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                else:
                    insert_index = i + 1
                    break
            elif in_docstring and (
                line.strip().endswith('"""') or line.strip().endswith("'''")
            ):
                insert_index = i + 1
                break

        lines.insert(insert_index, f'__version__ = "{new_version}"')
        init_file.write_text("\n".join(lines))


app = typer.Typer(help="Version Bumping Utility for QuickHooks")


@app.command()
def bump(
    part: str = typer.Argument(
        ..., help="Part of version to bump (major, minor, or patch)"
    ),
    project_root: Path = typer.Option(
        None, "--root", "-r", help="Project root directory"
    ),
) -> None:
    """Bump the version in pyproject.toml and __init__.py."""
    if project_root is None:
        # Assume script is in scripts/ directory
        project_root = Path(__file__).parent.parent

    # Validate part argument
    if part not in ["major", "minor", "patch"]:
        console.print(
            f"[red]Error: Invalid version part '{part}'. Must be major, minor, or patch[/red]",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    pyproject_path = project_root / "pyproject.toml"

    try:
        # Get current version
        current_version = get_version_from_pyproject(pyproject_path)
        console.print(f"Current version: [cyan]{current_version}[/cyan]")

        # Bump version
        new_version = bump_version_part(current_version, part)
        console.print(f"New version: [green]{new_version}[/green]")

        # Update files
        update_version_in_pyproject(pyproject_path, new_version)
        console.print(f"✅ Updated {pyproject_path}")

        update_version_in_init(project_root, new_version)
        console.print(f"✅ Updated __init__.py")

        # Output the new version (for CI/CD)
        print(new_version)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def get(
    project_root: Path = typer.Option(
        None, "--root", "-r", help="Project root directory"
    ),
) -> None:
    """Get the current version from pyproject.toml."""
    if project_root is None:
        project_root = Path(__file__).parent.parent

    pyproject_path = project_root / "pyproject.toml"

    try:
        version = get_version_from_pyproject(pyproject_path)
        console.print(f"Current version: [cyan]{version}[/cyan]")
        print(version)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def set_version(
    version: str = typer.Argument(..., help="Version to set (e.g., 1.2.3)"),
    project_root: Path = typer.Option(
        None, "--root", "-r", help="Project root directory"
    ),
) -> None:
    """Set a specific version in pyproject.toml."""
    if project_root is None:
        project_root = Path(__file__).parent.parent

    pyproject_path = project_root / "pyproject.toml"

    try:
        # Validate version format
        parse_version(version)

        # Get current version
        current_version = get_version_from_pyproject(pyproject_path)
        console.print(f"Current version: [cyan]{current_version}[/cyan]")
        console.print(f"Setting version to: [green]{version}[/green]")

        # Update files
        update_version_in_pyproject(pyproject_path, version)
        console.print(f"✅ Updated {pyproject_path}")

        update_version_in_init(project_root, version)
        console.print(f"✅ Updated __init__.py")

        print(version)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
