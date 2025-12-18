#!/usr/bin/env python3
"""
QuickHooks Deployment Script - One-Command Deployment

This script provides a one-command deployment solution for QuickHooks
with UV package manager integration, version management, and PyPI publishing.

Usage:
    python scripts/deploy.py --env [dev|prod] --version [patch|minor|major]
    python scripts/deploy.py --help
"""

import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cyclopts
from cyclopts import Parameter
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class Environment(str, Enum):
    """Deployment environments."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class VersionBump(str, Enum):
    """Version bump types."""

    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


@dataclass
class DeploymentConfig:
    """Deployment configuration."""

    project_root: Path
    version: str
    environment: Environment
    publish_to_pypi: bool = False
    run_tests: bool = True
    validate_build: bool = True
    enable_parallel_agents: bool = True


class DeploymentResult(BaseModel):
    """Deployment result data."""

    success: bool
    version: str
    environment: str
    duration: float
    errors: list[str] = []
    warnings: list[str] = []
    artifacts: list[str] = []


class DeploymentAgent:
    """Individual deployment agent for parallel execution."""

    def __init__(self, name: str, config: DeploymentConfig):
        self.name = name
        self.config = config
        self.console = Console()

    async def execute_task(
        self, task_name: str, command: list[str]
    ) -> tuple[bool, str]:
        """Execute a deployment task asynchronously."""
        try:
            self.console.print(f"[blue]Agent {self.name}[/blue]: Starting {task_name}")

            result = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.project_root,
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                self.console.print(
                    f"[green]Agent {self.name}[/green]: {task_name} completed"
                )
                return True, stdout.decode()
            self.console.print(f"[red]Agent {self.name}[/red]: {task_name} failed")
            return False, stderr.decode()

        except Exception as e:
            self.console.print(
                f"[red]Agent {self.name}[/red]: Error in {task_name}: {e}"
            )
            return False, str(e)


class DeploymentOrchestrator:
    """Main deployment orchestrator."""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.console = Console()
        self.agents: list[DeploymentAgent] = []
        self.result = DeploymentResult(
            success=False,
            version=config.version,
            environment=config.environment.value,
            duration=0.0,
        )

    def setup_agents(self) -> None:
        """Setup parallel deployment agents."""
        if self.config.enable_parallel_agents:
            self.agents = [
                DeploymentAgent("BuildAgent", self.config),
                DeploymentAgent("TestAgent", self.config),
                DeploymentAgent("ValidationAgent", self.config),
            ]
        else:
            self.agents = [DeploymentAgent("MainAgent", self.config)]

    def get_version_from_pyproject(self) -> str:
        """Extract current version from pyproject.toml."""
        pyproject_path = self.config.project_root / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError("pyproject.toml not found")

        with open(pyproject_path) as f:
            content = f.read()

        for line in content.split("\n"):
            if line.strip().startswith("version = "):
                return line.split("=")[1].strip().strip("\"'")

        raise ValueError("Version not found in pyproject.toml")

    def bump_version(self, bump_type: VersionBump) -> str:
        """Bump version using UV version command."""
        try:
            cmd = ["uv", "version", "--bump", bump_type.value]
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract new version from output
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines:
                if "=>" in line:
                    new_version = line.split("=>")[1].strip()
                    return new_version

            # Fallback: get version from pyproject.toml
            return self.get_version_from_pyproject()

        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Version bump failed: {e}")
            raise

    def validate_environment(self) -> bool:
        """Validate deployment environment."""
        self.console.print("[blue]Validating deployment environment...[/blue]")

        # Check UV installation
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.result.errors.append("UV package manager not installed")
            return False

        # Check project structure
        required_files = ["pyproject.toml", "src/quickhooks/__init__.py"]
        for file_path in required_files:
            if not (self.config.project_root / file_path).exists():
                self.result.errors.append(f"Required file missing: {file_path}")
                return False

        # Check Git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip() and self.config.environment == Environment.PROD:
                self.result.warnings.append(
                    "Uncommitted changes detected in production deployment"
                )
        except subprocess.CalledProcessError:
            self.result.warnings.append("Git status check failed")

        return True

    async def run_tests(self) -> bool:
        """Run test suite using UV."""
        if not self.config.run_tests:
            return True

        self.console.print("[blue]Running test suite...[/blue]")

        test_agent = DeploymentAgent("TestRunner", self.config)
        success, output = await test_agent.execute_task(
            "pytest", ["uv", "run", "pytest", "--cov=src/quickhooks", "-v"]
        )

        if not success:
            self.result.errors.append(f"Tests failed: {output}")
            return False

        self.console.print("[green]All tests passed[/green]")
        return True

    async def build_package(self) -> bool:
        """Build package using UV."""
        self.console.print("[blue]Building package...[/blue]")

        build_agent = DeploymentAgent("PackageBuilder", self.config)
        success, output = await build_agent.execute_task(
            "build", ["uv", "build", "--wheel", "--sdist"]
        )

        if not success:
            self.result.errors.append(f"Build failed: {output}")
            return False

        # List built artifacts
        dist_path = self.config.project_root / "dist"
        if dist_path.exists():
            artifacts = [f.name for f in dist_path.iterdir() if f.is_file()]
            self.result.artifacts.extend(artifacts)
            self.console.print(
                f"[green]Built artifacts: {', '.join(artifacts)}[/green]"
            )

        return True

    async def validate_build(self) -> bool:
        """Validate built packages."""
        if not self.config.validate_build:
            return True

        self.console.print("[blue]Validating build artifacts...[/blue]")

        # Run validation script
        validation_script = self.config.project_root / "scripts" / "validate-build.py"
        if validation_script.exists():
            validation_agent = DeploymentAgent("BuildValidator", self.config)
            success, output = await validation_agent.execute_task(
                "validation", ["python", str(validation_script)]
            )

            if not success:
                self.result.errors.append(f"Build validation failed: {output}")
                return False

        return True

    async def publish_package(self) -> bool:
        """Publish package to PyPI using UV."""
        if not self.config.publish_to_pypi:
            return True

        index_name = (
            "testpypi" if self.config.environment != Environment.PROD else "pypi"
        )
        self.console.print(f"[blue]Publishing to {index_name}...[/blue]")

        # Check for API token
        token_env = (
            f"UV_PUBLISH_TOKEN_{index_name.upper()}"
            if index_name != "pypi"
            else "UV_PUBLISH_TOKEN"
        )
        if not os.getenv(token_env):
            self.result.errors.append(
                f"PyPI token not found in environment variable {token_env}"
            )
            return False

        publish_agent = DeploymentAgent("Publisher", self.config)

        if index_name == "pypi":
            cmd = ["uv", "publish"]
        else:
            cmd = ["uv", "publish", "--index", index_name]

        success, output = await publish_agent.execute_task("publish", cmd)

        if not success:
            self.result.errors.append(f"Publishing failed: {output}")
            return False

        self.console.print(f"[green]Successfully published to {index_name}[/green]")
        return True

    async def parallel_deployment_tasks(self) -> bool:
        """Execute deployment tasks in parallel where possible."""
        if not self.config.enable_parallel_agents:
            # Sequential execution
            return (
                await self.run_tests()
                and await self.build_package()
                and await self.validate_build()
            )

        # Parallel execution
        self.console.print("[blue]Running parallel deployment tasks...[/blue]")

        tasks = [
            self.run_tests(),
            self.build_package(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.result.errors.append(f"Parallel task {i} failed: {result}")
                return False
            if not result:
                return False

        # Run validation after build completes
        return await self.validate_build()

    def create_deployment_summary(self) -> Table:
        """Create deployment summary table."""
        table = Table(title="Deployment Summary")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Version", self.result.version)
        table.add_row("Environment", self.result.environment)
        table.add_row("Duration", f"{self.result.duration:.2f}s")
        table.add_row(
            "Status",
            "[green]Success[/green]" if self.result.success else "[red]Failed[/red]",
        )

        if self.result.artifacts:
            table.add_row("Artifacts", ", ".join(self.result.artifacts))

        if self.result.warnings:
            table.add_row("Warnings", str(len(self.result.warnings)))

        if self.result.errors:
            table.add_row("Errors", str(len(self.result.errors)))

        return table

    async def run_deployment(self) -> DeploymentResult:
        """Run complete deployment process."""
        start_time = time.time()

        try:
            self.console.print(
                Panel.fit(
                    f"[bold blue]QuickHooks Deployment[/bold blue]\n"
                    f"Version: {self.config.version}\n"
                    f"Environment: {self.config.environment.value}\n"
                    f"Parallel Agents: {'Enabled' if self.config.enable_parallel_agents else 'Disabled'}"
                )
            )

            # Setup agents
            self.setup_agents()

            # Validate environment
            if not self.validate_environment():
                return self.result

            # Run deployment tasks
            if not await self.parallel_deployment_tasks():
                return self.result

            # Publish if enabled
            if not await self.publish_package():
                return self.result

            self.result.success = True
            self.console.print("[green]Deployment completed successfully![/green]")

        except Exception as e:
            self.result.errors.append(f"Deployment failed: {e}")
            self.console.print(f"[red]Deployment failed: {e}[/red]")

        finally:
            self.result.duration = time.time() - start_time

            # Display summary
            self.console.print("\n")
            self.console.print(self.create_deployment_summary())

            # Display errors and warnings
            if self.result.errors:
                self.console.print("\n[red]Errors:[/red]")
                for error in self.result.errors:
                    self.console.print(f"  • {error}")

            if self.result.warnings:
                self.console.print("\n[yellow]Warnings:[/yellow]")
                for warning in self.result.warnings:
                    self.console.print(f"  • {warning}")

        return self.result


app = cyclopts.App(help="QuickHooks Deployment System")


@app.command
def deploy(
    environment: Environment = Parameter(
        Environment.DEV, "--env", "-e", help="Deployment environment"
    ),
    version_bump: VersionBump | None = Parameter(
        None, "--version", "-v", help="Version bump type"
    ),
    publish: bool = Parameter(False, "--publish", "-p", help="Publish to PyPI"),
    skip_tests: bool = Parameter(False, "--skip-tests", help="Skip test execution"),
    skip_validation: bool = Parameter(
        False, "--skip-validation", help="Skip build validation"
    ),
    sequential: bool = Parameter(
        False, "--sequential", help="Disable parallel agents"
    ),
    dry_run: bool = Parameter(
        False, "--dry-run", help="Show what would be done without executing"
    ),
):
    """Deploy QuickHooks package with UV package manager."""

    project_root = Path(__file__).parent.parent

    # Get or bump version
    if version_bump:
        try:
            # Create temporary orchestrator to bump version
            temp_config = DeploymentConfig(
                project_root=project_root, version="current", environment=environment
            )
            temp_orchestrator = DeploymentOrchestrator(temp_config)
            new_version = temp_orchestrator.bump_version(version_bump)
            console.print(f"[green]Version bumped to: {new_version}[/green]")
        except Exception as e:
            console.print(f"[red]Version bump failed: {e}[/red]")
            sys.exit(1)
    else:
        # Get current version
        temp_config = DeploymentConfig(
            project_root=project_root, version="current", environment=environment
        )
        temp_orchestrator = DeploymentOrchestrator(temp_config)
        new_version = temp_orchestrator.get_version_from_pyproject()

    # Create deployment configuration
    config = DeploymentConfig(
        project_root=project_root,
        version=new_version,
        environment=environment,
        publish_to_pypi=publish,
        run_tests=not skip_tests,
        validate_build=not skip_validation,
        enable_parallel_agents=not sequential,
    )

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
        console.print(f"Would deploy version {new_version} to {environment.value}")
        if publish:
            console.print(
                f"Would publish to {'PyPI' if environment == Environment.PROD else 'TestPyPI'}"
            )
        return

    # Run deployment
    orchestrator = DeploymentOrchestrator(config)
    result = asyncio.run(orchestrator.run_deployment())

    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


@app.command()
def status():
    """Show current deployment status."""
    project_root = Path(__file__).parent.parent

    # Get current version
    config = DeploymentConfig(
        project_root=project_root, version="current", environment=Environment.DEV
    )
    orchestrator = DeploymentOrchestrator(config)

    try:
        current_version = orchestrator.get_version_from_pyproject()

        table = Table(title="QuickHooks Status")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Current Version", current_version)
        table.add_row("Project Root", str(project_root))

        # Check Git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            git_status = "Clean" if not result.stdout.strip() else "Modified"
            table.add_row("Git Status", git_status)
        except subprocess.CalledProcessError:
            table.add_row("Git Status", "Unknown")

        # Check dist artifacts
        dist_path = project_root / "dist"
        if dist_path.exists():
            artifacts = [f.name for f in dist_path.iterdir() if f.is_file()]
            table.add_row("Built Artifacts", str(len(artifacts)))
        else:
            table.add_row("Built Artifacts", "0")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
