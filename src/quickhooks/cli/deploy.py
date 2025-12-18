#!/usr/bin/env uv run -S
# /// script
# dependencies = [
#   "cyclopts>=0.3.0",
#   "rich>=13.7.0",
#   "quickhooks>=0.1.0",
# ]
# requires-python = ">=3.12"
# ///
"""Unified hook deployment system for QuickHooks.

This module provides a comprehensive system for discovering, registering,
and deploying hooks throughout the entire system.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from quickhooks.config import get_global_hooks_dir
from quickhooks.db.indexer import HookIndexer
from quickhooks.db.manager import get_global_db
from quickhooks.db.models import (
    HookMetadata,
)

console = Console()
deploy_app = cyclopts.App(help="Deploy hooks throughout the system")


class HookDeployer:
    """Manages deployment of hooks across the system."""

    def __init__(self):
        self.db = get_global_db()
        self.indexer = HookIndexer()
        self.global_hooks_dir = get_global_hooks_dir()
        self.claude_dir = Path.home() / ".claude"
        self.project_hooks_dir = Path.cwd() / "hooks"

    def discover_hooks(self) -> list[Path]:
        """Discover all hooks in the project and global directory.

        Returns:
            List of paths to hook files
        """
        hooks = []

        # Define hooks to skip (templates, tests, examples)
        skip_patterns = [
            "_",
            "test_",
            "example_",
            "template_",
            "__pycache__",
            "base.py",
            "models.py",
            "utils.py",
            "schema.py",
        ]

        # Search in project hooks directory
        if self.project_hooks_dir.exists():
            console.print(f"🔍 Searching project hooks: {self.project_hooks_dir}")
            for hook_file in self.project_hooks_dir.glob("*.py"):
                if not any(
                    hook_file.name.startswith(pattern) for pattern in skip_patterns
                ) and (
                    hook_file.name
                    in [
                        "language_aware_linter.py",
                        "language_aware_formatter.py",
                        "language_aware_build_checker.py",
                        "grep_to_ripgrep_transformer.py",
                        "intelligent_tool_dispatcher.py",
                        "agent_analysis_hook.py",
                    ]
                    or hook_file.name.endswith("_hook.py")
                    or hook_file.name.endswith(".py")
                ):
                    hooks.append(hook_file)
                    console.print(f"  ✅ Found: {hook_file.name}")

        # Search in global hooks directory
        if self.global_hooks_dir.exists():
            console.print(f"🔍 Searching global hooks: {self.global_hooks_dir}")
            for hook_file in self.global_hooks_dir.glob("*.py"):
                if not any(
                    hook_file.name.startswith(pattern) for pattern in skip_patterns
                ):
                    hooks.append(hook_file)
                    console.print(f"  ✅ Found: {hook_file.name}")

        # Remove duplicates (prefer project hooks over global)
        unique_hooks = {}
        for hook in hooks:
            if hook.name not in unique_hooks or (
                "hooks" in str(hook) and self.project_hooks_dir.name in str(hook)
            ):
                unique_hooks[hook.name] = hook

        return list(unique_hooks.values())

    def analyze_hook(self, hook_path: Path) -> HookMetadata | None:
        """Analyze a hook file and extract metadata.

        Args:
            hook_path: Path to the hook file

        Returns:
            HookMetadata if analysis successful, None otherwise
        """
        try:
            # Use the indexer to analyze the hook
            metadata = self.indexer.index_hook(hook_path)
            return metadata
        except Exception as e:
            console.print(f"⚠️  Failed to analyze {hook_path.name}: {e}", style="yellow")
            return None

    def register_hook(self, metadata: HookMetadata) -> bool:
        """Register a hook in the LanceDB registry.

        Args:
            metadata: Hook metadata to register

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if hook already exists
            existing = self.db.get_hook_by_name(metadata.name)

            if existing:
                # Update existing hook
                self.db.update_hook(metadata)
                console.print(f"✅ Updated hook: {metadata.name}")
            else:
                # Add new hook
                self.db.add_hook(metadata)
                console.print(f"✅ Registered hook: {metadata.name}")

            return True
        except Exception as e:
            console.print(f"❌ Failed to register {metadata.name}: {e}", style="red")
            return False

    def deploy_to_claude(self, hook_paths: list[Path]) -> tuple[int, int]:
        """Deploy hooks to Claude Code settings.

        Args:
            hook_paths: List of hook paths to deploy

        Returns:
            Tuple of (successful, failed) deployments
        """
        successful = 0
        failed = 0

        # Ensure Claude directory exists
        self.claude_dir.mkdir(exist_ok=True)
        hooks_dir = self.claude_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        # Get current Claude settings
        settings_file = self.claude_dir / "settings.json"
        settings = {}

        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
            except Exception as e:
                console.print(
                    f"⚠️  Could not read existing settings: {e}", style="yellow"
                )

        # Initialize hooks configuration
        if "hooks" not in settings:
            settings["hooks"] = {}
        if "PreToolUse" not in settings["hooks"]:
            settings["hooks"]["PreToolUse"] = []

        # Copy hooks and update settings
        for hook_path in hook_paths:
            try:
                # Copy hook to Claude hooks directory
                dest_path = hooks_dir / hook_path.name
                shutil.copy2(hook_path, dest_path)

                # Make executable
                os.chmod(dest_path, 0o755)

                # Determine tools based on hook name
                tools = ["*"]  # Default to all tools

                # Specific tool mappings for our hooks
                if "grep" in hook_path.name:
                    tools = ["Bash", "Grep"]
                elif (
                    "linter" in hook_path.name
                    or "lint" in hook_path.name
                    or "formatter" in hook_path.name
                    or "format" in hook_path.name
                    or "build" in hook_path.name
                    or "tool_dispatcher" in hook_path.name
                    or "tool_selector" in hook_path.name
                ):
                    tools = ["Bash"]
                elif "agent_analysis" in hook_path.name:
                    tools = ["Task"]

                # Add to settings if not already present
                hook_config = {
                    "tools": tools,
                    "hooks": [{"command": str(dest_path), "timeout": 30}],
                }

                # Check if hook already in settings
                hook_exists = False
                for config in settings["hooks"]["PreToolUse"]:
                    for hook in config.get("hooks", []):
                        if hook_path.name in hook.get("command", ""):
                            hook_exists = True
                            break

                if not hook_exists:
                    settings["hooks"]["PreToolUse"].append(hook_config)

                successful += 1
                console.print(f"📦 Deployed: {hook_path.name} → {dest_path}")

            except Exception as e:
                console.print(f"❌ Failed to deploy {hook_path.name}: {e}", style="red")
                failed += 1

        # Save updated settings
        try:
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            console.print(f"✅ Updated Claude settings: {settings_file}")
        except Exception as e:
            console.print(f"❌ Failed to update settings: {e}", style="red")
            return successful, failed + len(hook_paths) - successful

        return successful, failed

    def deploy_to_system(self, hook_paths: list[Path]) -> tuple[int, int]:
        """Deploy hooks system-wide (requires appropriate permissions).

        Args:
            hook_paths: List of hook paths to deploy

        Returns:
            Tuple of (successful, failed) deployments
        """
        successful = 0
        failed = 0

        # Check for system-wide QuickHooks installation
        Path("/usr/local/share/quickhooks/hooks")
        user_hooks_dir = Path.home() / ".local" / "share" / "quickhooks" / "hooks"

        # Try user directory first (no sudo required)
        target_dir = user_hooks_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        for hook_path in hook_paths:
            try:
                dest_path = target_dir / hook_path.name
                shutil.copy2(hook_path, dest_path)
                os.chmod(dest_path, 0o755)

                successful += 1
                console.print(f"🌍 System deploy: {hook_path.name} → {dest_path}")

            except Exception as e:
                console.print(f"❌ Failed to deploy {hook_path.name}: {e}", style="red")
                failed += 1

        return successful, failed

    def create_hook_manifest(self, hook_paths: list[Path]) -> Path:
        """Create a manifest of all deployed hooks.

        Args:
            hook_paths: List of deployed hook paths

        Returns:
            Path to the manifest file
        """
        manifest = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "hooks": [],
        }

        for hook_path in hook_paths:
            metadata = self.analyze_hook(hook_path)
            if metadata:
                manifest["hooks"].append(
                    {
                        "name": metadata.name,
                        "type": metadata.hook_type.value,
                        "description": metadata.description,
                        "file": hook_path.name,
                        "complexity": metadata.complexity.value,
                        "tags": metadata.tags,
                        "author": metadata.author,
                        "version": metadata.version,
                    }
                )

        manifest_path = self.global_hooks_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest_path


def deploy_all(
    skip_analysis: Annotated[
        bool, Parameter("--skip-analysis", help="Skip hook analysis")
    ] = False,
    skip_registry: Annotated[
        bool, Parameter("--skip-registry", help="Skip LanceDB registration")
    ] = False,
    skip_claude: Annotated[
        bool, Parameter("--skip-claude", help="Skip Claude Code deployment")
    ] = False,
    skip_system: Annotated[
        bool, Parameter("--skip-system", help="Skip system-wide deployment")
    ] = False,
    force: Annotated[
        bool,
        Parameter("--force", alias="-f", help="Force deployment even if errors occur"),
    ] = False,
):
    """Deploy all hooks throughout the entire system.

    Parameters
    ----------
    skip_analysis
        Skip hook analysis (default: False)
    skip_registry
        Skip LanceDB registration (default: False)
    skip_claude
        Skip Claude Code deployment (default: False)
    skip_system
        Skip system-wide deployment (default: False)
    force
        Force deployment even if errors occur (default: False)
    """
    console.print(
        Panel(
            Text("🚀 QuickHooks System-Wide Deployment", style="bold blue"),
            subtitle="Deploying hooks everywhere they need to be",
        )
    )

    deployer = HookDeployer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Discover hooks
        task = progress.add_task("🔍 Discovering hooks...", total=None)
        hook_paths = deployer.discover_hooks()
        progress.update(task, description=f"✅ Found {len(hook_paths)} hooks")

        if not hook_paths:
            console.print("❌ No hooks found to deploy!", style="red")
            sys.exit(1)

        # Step 2: Analyze and register hooks
        if not skip_analysis:
            task = progress.add_task(
                f"🔬 Analyzing {len(hook_paths)} hooks...", total=len(hook_paths)
            )

            analyzed_hooks = []
            for i, hook_path in enumerate(hook_paths):
                metadata = deployer.analyze_hook(hook_path)
                if metadata:
                    analyzed_hooks.append((hook_path, metadata))
                progress.update(task, completed=i + 1)

            progress.update(
                task,
                description=f"✅ Analyzed {len(analyzed_hooks)} hooks successfully",
            )

            # Register in LanceDB
            if not skip_registry and analyzed_hooks:
                task = progress.add_task(
                    f"📝 Registering {len(analyzed_hooks)} hooks...",
                    total=len(analyzed_hooks),
                )

                registered = 0
                for i, (hook_path, metadata) in enumerate(analyzed_hooks):
                    if deployer.register_hook(metadata):
                        registered += 1
                    progress.update(task, completed=i + 1)

                progress.update(
                    task, description=f"✅ Registered {registered} hooks in database"
                )

        # Step 3: Deploy to Claude Code
        if not skip_claude:
            task = progress.add_task("🔧 Deploying to Claude Code...", total=None)
            successful, failed = deployer.deploy_to_claude(hook_paths)
            progress.update(
                task, description=f"✅ Claude: {successful} deployed, {failed} failed"
            )

            if failed > 0 and not force:
                console.print(
                    "❌ Some deployments failed. Use --force to continue anyway.",
                    style="red",
                )
                sys.exit(1)

        # Step 4: Deploy system-wide
        if not skip_system:
            task = progress.add_task("🌍 Deploying system-wide...", total=None)
            successful, failed = deployer.deploy_to_system(hook_paths)
            progress.update(
                task, description=f"✅ System: {successful} deployed, {failed} failed"
            )

        # Step 5: Create manifest
        task = progress.add_task("📋 Creating deployment manifest...", total=None)
        manifest_path = deployer.create_hook_manifest(hook_paths)
        progress.update(task, description=f"✅ Created manifest: {manifest_path}")

    # Display summary
    console.print("\n" + "=" * 50)
    console.print(
        Panel(
            Text("🎉 Deployment Complete!", style="bold green")
            + Text(f"\n\nDeployed {len(hook_paths)} hooks across the system.\n")
            + Text("\nLocations:\n")
            + Text(f"• Project: {deployer.project_hooks_dir}\n")
            + Text(f"• Global: {deployer.global_hooks_dir}\n")
            + Text(f"• Claude: {deployer.claude_dir / 'hooks'}\n")
            + Text("• System: ~/.local/share/quickhooks/hooks\n")
            + Text(f"\nManifest: {manifest_path}"),
            title="Deployment Summary",
            border_style="green",
        )
    )


def list_deployed(
    location: Annotated[
        str,
        Parameter(
            "--location",
            alias="-l",
            help="Location to list (all/project/global/claude/system)",
        ),
    ] = "all",
    format: Annotated[
        str, Parameter("--format", alias="-f", help="Output format (table/json/simple)")
    ] = "table",
):
    """List all deployed hooks in the system.

    Parameters
    ----------
    location
        Location to list (all/project/global/claude/system) (default: "all")
    format
        Output format (table/json/simple) (default: "table")
    """
    HookDeployer()
    db = get_global_db()

    # Get hooks from database
    all_hooks = db.list_hooks()

    if format == "json":
        # JSON output
        hooks_data = []
        for hook in all_hooks:
            hooks_data.append(
                {
                    "name": hook.name,
                    "type": hook.hook_type.value,
                    "complexity": hook.complexity.value,
                    "description": hook.description,
                    "tags": hook.tags,
                    "file_path": hook.file_path,
                    "usage_count": hook.usage_count,
                }
            )
        console.print_json(data={"hooks": hooks_data, "total": len(hooks_data)})

    elif format == "simple":
        # Simple list
        for hook in all_hooks:
            console.print(f"{hook.name} - {hook.description}")

    else:
        # Table output
        table = Table(title="Deployed Hooks")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Complexity", style="yellow")
        table.add_column("Tags", style="green")
        table.add_column("Usage", style="blue")

        for hook in all_hooks:
            table.add_row(
                hook.name,
                hook.hook_type.value,
                hook.complexity.value,
                ", ".join(hook.tags[:3]),  # First 3 tags
                str(hook.usage_count),
            )

        console.print(table)
        console.print(f"\nTotal hooks: {len(all_hooks)}")


def search_hooks(
    query: str,
    limit: Annotated[
        int, Parameter("--limit", alias="-n", help="Maximum results")
    ] = 10,
):
    """Search for hooks using semantic search.

    Parameters
    ----------
    query
        Search query
    limit
        Maximum results (default: 10)
    """
    db = get_global_db()

    results = db.search_hooks(query, limit)

    if not results:
        console.print("No hooks found matching your query.", style="yellow")
        return

    console.print(f"\n🔍 Search results for '{query}':\n")

    for i, hook in enumerate(results, 1):
        console.print(f"{i}. [bold cyan]{hook.name}[/bold cyan]")
        console.print(
            f"   Type: {hook.hook_type.value} | Complexity: {hook.complexity.value}"
        )
        console.print(f"   Description: {hook.description}")
        console.print(f"   Tags: {', '.join(hook.tags)}")
        console.print(f"   File: {hook.file_path}")
        console.print()


def show_statistics():
    """Show deployment and usage statistics."""
    db = get_global_db()

    # Get statistics
    total_hooks = len(db.list_hooks())
    hooks_by_type = {}
    hooks_by_complexity = {}

    for hook in db.list_hooks():
        # Count by type
        hook_type = hook.hook_type.value
        hooks_by_type[hook_type] = hooks_by_type.get(hook_type, 0) + 1

        # Count by complexity
        complexity = hook.complexity.value
        hooks_by_complexity[complexity] = hooks_by_complexity.get(complexity, 0) + 1

    # Get popular hooks
    popular_hooks = db.get_popular_hooks(5)

    # Display statistics
    console.print(
        Panel(
            Text("📊 QuickHooks Deployment Statistics", style="bold blue"),
            subtitle=f"Total hooks in system: {total_hooks}",
        )
    )

    # Hooks by type
    console.print("\n[bold]Hooks by Type:[/bold]")
    for hook_type, count in hooks_by_type.items():
        console.print(f"  • {hook_type}: {count}")

    # Hooks by complexity
    console.print("\n[bold]Hooks by Complexity:[/bold]")
    for complexity, count in hooks_by_complexity.items():
        console.print(f"  • {complexity}: {count}")

    # Popular hooks
    if popular_hooks:
        console.print("\n[bold]Most Popular Hooks:[/bold]")
        for i, hook in enumerate(popular_hooks, 1):
            analytics = db.get_hook_analytics(hook.name)
            if analytics:
                console.print(
                    f"  {i}. {hook.name} - {analytics.total_executions} executions"
                )


def sync_hooks():
    """Sync hooks between all locations."""
    console.print(
        Panel(
            Text("🔄 Syncing Hooks Across System", style="bold blue"),
            subtitle="Ensuring all locations have the latest hooks",
        )
    )

    deployer = HookDeployer()

    # Discover all hooks
    all_hooks = deployer.discover_hooks()

    # Re-deploy everywhere
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze all hooks
        task = progress.add_task("🔬 Analyzing hooks...", total=len(all_hooks))
        for i, hook_path in enumerate(all_hooks):
            metadata = deployer.analyze_hook(hook_path)
            if metadata:
                deployer.register_hook(metadata)
            progress.update(task, completed=i + 1)

        # Deploy to all locations
        task = progress.add_task("📦 Deploying to all locations...", total=None)

        # Claude
        c_success, c_failed = deployer.deploy_to_claude(all_hooks)

        # System
        s_success, s_failed = deployer.deploy_to_system(all_hooks)

        progress.update(task, description="✅ Sync complete")

    console.print(f"\n✅ Synced {len(all_hooks)} hooks")
    console.print(f"   Claude: {c_success} successful, {c_failed} failed")
    console.print(f"   System: {s_success} successful, {s_failed} failed")


if __name__ == "__main__":
    deploy_app()
