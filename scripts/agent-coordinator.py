#!/usr/bin/env python3
"""
QuickHooks Agent Coordinator - Parallel Execution Manager

This script manages parallel agent coordination for deployment tasks,
build processes, testing, and validation workflows.

Agents:
- BuildAgent: Handles package building and artifact creation
- TestAgent: Runs test suites and coverage analysis
- ValidationAgent: Validates builds and security compliance
- DeploymentAgent: Manages deployment to various environments
- MonitoringAgent: Tracks deployment status and health

Usage:
    python scripts/agent-coordinator.py --task [build|test|deploy|validate]
    python scripts/agent-coordinator.py --orchestrate --config config.yml
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import typer
import yaml
from pydantic import BaseModel
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Types of tasks that can be executed."""

    BUILD = "build"
    TEST = "test"
    VALIDATE = "validate"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    CLEANUP = "cleanup"


@dataclass
class AgentTask:
    """Represents a task to be executed by an agent."""

    id: str
    task_type: TaskType
    command: list[str]
    environment: dict[str, str] = field(default_factory=dict)
    working_dir: Path | None = None
    timeout: int = 300  # 5 minutes default
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: list[str] = field(default_factory=list)
    retries: int = 3
    retry_delay: int = 5

    def __post_init__(self):
        if self.working_dir is None:
            self.working_dir = Path.cwd()


class TaskResult(BaseModel):
    """Result of task execution."""

    task_id: str
    status: AgentStatus
    start_time: float
    end_time: float | None = None
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    error_message: str | None = None

    @property
    def duration(self) -> float:
        """Get task execution duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class Agent:
    """Individual agent for executing tasks."""

    def __init__(self, name: str, agent_type: str, max_concurrent: int = 1):
        self.name = name
        self.agent_type = agent_type
        self.max_concurrent = max_concurrent
        self.status = AgentStatus.IDLE
        self.current_tasks: set[str] = set()
        self.completed_tasks: list[TaskResult] = []
        self.logger = logging.getLogger(f"agent.{name}")

        # Performance metrics
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.total_execution_time = 0.0

    async def execute_task(self, task: AgentTask) -> TaskResult:
        """Execute a single task."""
        result = TaskResult(
            task_id=task.id, status=AgentStatus.RUNNING, start_time=time.time()
        )

        self.current_tasks.add(task.id)
        self.status = AgentStatus.RUNNING
        self.total_tasks += 1

        self.logger.info(f"Starting task {task.id}: {' '.join(task.command)}")

        try:
            # Execute with retries
            for attempt in range(task.retries):
                try:
                    process = await asyncio.create_subprocess_exec(
                        *task.command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=task.working_dir,
                        env={**os.environ, **task.environment},
                    )

                    # Wait for completion with timeout
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=task.timeout
                    )

                    result.stdout = stdout.decode("utf-8", errors="replace")
                    result.stderr = stderr.decode("utf-8", errors="replace")
                    result.return_code = process.returncode

                    if process.returncode == 0:
                        result.status = AgentStatus.SUCCESS
                        self.successful_tasks += 1
                        self.logger.info(f"Task {task.id} completed successfully")
                        break
                    else:
                        if attempt < task.retries - 1:
                            self.logger.warning(
                                f"Task {task.id} failed (attempt {attempt + 1}/{task.retries}), "
                                f"retrying in {task.retry_delay}s"
                            )
                            await asyncio.sleep(task.retry_delay)
                        else:
                            result.status = AgentStatus.FAILED
                            result.error_message = (
                                f"Command failed with return code {process.returncode}"
                            )
                            self.failed_tasks += 1
                            self.logger.error(
                                f"Task {task.id} failed after {task.retries} attempts"
                            )

                except TimeoutError:
                    if attempt < task.retries - 1:
                        self.logger.warning(f"Task {task.id} timed out, retrying...")
                        await asyncio.sleep(task.retry_delay)
                    else:
                        result.status = AgentStatus.FAILED
                        result.error_message = f"Task timed out after {task.timeout}s"
                        self.failed_tasks += 1
                        self.logger.error(f"Task {task.id} timed out")

                except Exception as e:
                    if attempt < task.retries - 1:
                        self.logger.warning(
                            f"Task {task.id} failed with exception: {e}, retrying..."
                        )
                        await asyncio.sleep(task.retry_delay)
                    else:
                        result.status = AgentStatus.FAILED
                        result.error_message = str(e)
                        self.failed_tasks += 1
                        self.logger.error(f"Task {task.id} failed with exception: {e}")

        except Exception as e:
            result.status = AgentStatus.FAILED
            result.error_message = str(e)
            self.failed_tasks += 1
            self.logger.error(f"Unexpected error in task {task.id}: {e}")

        finally:
            result.end_time = time.time()
            self.total_execution_time += result.duration
            self.current_tasks.remove(task.id)
            self.completed_tasks.append(result)

            if not self.current_tasks:
                self.status = AgentStatus.IDLE

        return result

    def can_accept_task(self) -> bool:
        """Check if agent can accept new tasks."""
        return len(self.current_tasks) < self.max_concurrent

    def get_stats(self) -> dict[str, Any]:
        """Get agent performance statistics."""
        success_rate = (
            (self.successful_tasks / self.total_tasks * 100)
            if self.total_tasks > 0
            else 0
        )
        avg_execution_time = (
            (self.total_execution_time / self.total_tasks)
            if self.total_tasks > 0
            else 0
        )

        return {
            "name": self.name,
            "type": self.agent_type,
            "status": self.status.value,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(success_rate, 2),
            "avg_execution_time": round(avg_execution_time, 2),
            "current_tasks": len(self.current_tasks),
            "max_concurrent": self.max_concurrent,
        }


class TaskScheduler:
    """Schedules and prioritizes tasks for execution."""

    def __init__(self):
        self.pending_tasks: list[AgentTask] = []
        self.running_tasks: dict[str, AgentTask] = {}
        self.completed_tasks: dict[str, TaskResult] = {}
        self.task_dependencies: dict[str, set[str]] = {}

    def add_task(self, task: AgentTask) -> None:
        """Add a task to the scheduler."""
        self.pending_tasks.append(task)
        if task.dependencies:
            self.task_dependencies[task.id] = set(task.dependencies)

        # Sort by priority
        self.pending_tasks.sort(
            key=lambda t: {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.NORMAL: 2,
                TaskPriority.LOW: 3,
            }[t.priority]
        )

    def get_ready_tasks(self) -> list[AgentTask]:
        """Get tasks that are ready to execute (dependencies satisfied)."""
        ready_tasks = []

        for task in self.pending_tasks:
            if task.id not in self.task_dependencies:
                # No dependencies
                ready_tasks.append(task)
            else:
                # Check if all dependencies are completed
                deps = self.task_dependencies[task.id]
                if all(
                    dep_id in self.completed_tasks
                    and self.completed_tasks[dep_id].status == AgentStatus.SUCCESS
                    for dep_id in deps
                ):
                    ready_tasks.append(task)

        # Remove ready tasks from pending
        for task in ready_tasks:
            self.pending_tasks.remove(task)

        return ready_tasks

    def mark_running(self, task: AgentTask) -> None:
        """Mark a task as running."""
        self.running_tasks[task.id] = task

    def mark_completed(self, result: TaskResult) -> None:
        """Mark a task as completed."""
        if result.task_id in self.running_tasks:
            del self.running_tasks[result.task_id]
        self.completed_tasks[result.task_id] = result

    def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks."""
        return len(self.pending_tasks) > 0 or len(self.running_tasks) > 0


class AgentCoordinator:
    """Main coordinator managing multiple agents."""

    def __init__(self, config_path: Path | None = None):
        self.agents: dict[str, Agent] = {}
        self.scheduler = TaskScheduler()
        self.logger = logging.getLogger("coordinator")
        self.start_time = time.time()

        # Load configuration
        if config_path and config_path.exists():
            self.load_config(config_path)
        else:
            self.setup_default_agents()

    def load_config(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Create agents from config
        for agent_config in config.get("agents", []):
            agent = Agent(
                name=agent_config["name"],
                agent_type=agent_config["type"],
                max_concurrent=agent_config.get("max_concurrent", 1),
            )
            self.agents[agent.name] = agent

    def setup_default_agents(self) -> None:
        """Setup default agents for QuickHooks deployment."""
        default_agents = [
            ("BuildAgent", "build", 1),
            ("TestAgent", "test", 2),
            ("ValidationAgent", "validate", 1),
            ("DeploymentAgent", "deploy", 1),
            ("MonitoringAgent", "monitor", 1),
        ]

        for name, agent_type, max_concurrent in default_agents:
            agent = Agent(name, agent_type, max_concurrent)
            self.agents[name] = agent

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the coordinator."""
        self.agents[agent.name] = agent

    def find_available_agent(self, task_type: TaskType) -> Agent | None:
        """Find an available agent for the given task type."""
        # First, try to find agents of the matching type
        matching_agents = [
            agent
            for agent in self.agents.values()
            if agent.agent_type == task_type.value and agent.can_accept_task()
        ]

        if matching_agents:
            # Return the agent with the lowest current load
            return min(matching_agents, key=lambda a: len(a.current_tasks))

        # Fallback: find any available agent
        available_agents = [
            agent for agent in self.agents.values() if agent.can_accept_task()
        ]

        if available_agents:
            return min(available_agents, key=lambda a: len(a.current_tasks))

        return None

    async def execute_tasks(self, tasks: list[AgentTask]) -> dict[str, TaskResult]:
        """Execute a list of tasks using available agents."""
        # Add tasks to scheduler
        for task in tasks:
            self.scheduler.add_task(task)

        results = {}
        running_futures = {}

        while self.scheduler.has_pending_tasks() or running_futures:
            # Get ready tasks
            ready_tasks = self.scheduler.get_ready_tasks()

            # Assign tasks to available agents
            for task in ready_tasks:
                agent = self.find_available_agent(task.task_type)
                if agent:
                    self.scheduler.mark_running(task)
                    future = asyncio.create_task(agent.execute_task(task))
                    running_futures[task.id] = (future, agent)
                    self.logger.info(f"Assigned task {task.id} to agent {agent.name}")
                else:
                    # No available agent, put task back
                    self.scheduler.pending_tasks.insert(0, task)

            # Wait for any task to complete
            if running_futures:
                done, pending = await asyncio.wait(
                    [future for future, _ in running_futures.values()],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Process completed tasks
                for future in done:
                    result = await future
                    results[result.task_id] = result
                    self.scheduler.mark_completed(result)

                    # Remove from running futures
                    del running_futures[result.task_id]

                    self.logger.info(
                        f"Task {result.task_id} completed with status {result.status.value}"
                    )
            else:
                # No tasks running, wait a bit
                await asyncio.sleep(0.1)

        return results

    def create_status_display(self) -> Panel:
        """Create real-time status display."""
        # Create agent status table
        agent_table = Table(title="Agent Status")
        agent_table.add_column("Agent", style="cyan")
        agent_table.add_column("Type", style="magenta")
        agent_table.add_column("Status", style="white")
        agent_table.add_column("Tasks", style="yellow")
        agent_table.add_column("Success Rate", style="green")

        for agent in self.agents.values():
            stats = agent.get_stats()
            status_color = {
                "idle": "[blue]IDLE[/blue]",
                "running": "[yellow]RUNNING[/yellow]",
                "success": "[green]SUCCESS[/green]",
                "failed": "[red]FAILED[/red]",
            }.get(stats["status"], stats["status"])

            agent_table.add_row(
                stats["name"],
                stats["type"],
                status_color,
                f"{stats['current_tasks']}/{stats['max_concurrent']}",
                f"{stats['success_rate']:.1f}%",
            )

        # Create task queue info
        queue_info = (
            f"Pending Tasks: {len(self.scheduler.pending_tasks)}\n"
            f"Running Tasks: {len(self.scheduler.running_tasks)}\n"
            f"Completed Tasks: {len(self.scheduler.completed_tasks)}\n"
            f"Uptime: {time.time() - self.start_time:.1f}s"
        )

        return Panel.fit(
            f"{agent_table}\n\n{queue_info}",
            title="[bold blue]Agent Coordinator Status[/bold blue]",
            border_style="blue",
        )

    def get_summary_stats(self) -> dict[str, Any]:
        """Get overall coordinator statistics."""
        total_tasks = sum(agent.total_tasks for agent in self.agents.values())
        successful_tasks = sum(agent.successful_tasks for agent in self.agents.values())
        failed_tasks = sum(agent.failed_tasks for agent in self.agents.values())

        return {
            "total_agents": len(self.agents),
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (successful_tasks / total_tasks * 100)
            if total_tasks > 0
            else 0,
            "uptime": time.time() - self.start_time,
            "pending_tasks": len(self.scheduler.pending_tasks),
            "running_tasks": len(self.scheduler.running_tasks),
        }


app = typer.Typer(help="QuickHooks Agent Coordinator")


@app.command()
def orchestrate(
    config: Path | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Configuration file path"
    ),
    monitor: bool = typer.Option(
        False, "--monitor", "-m", help="Enable real-time monitoring"
    ),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format (table|json)"
    ),
):
    """Orchestrate parallel agent execution."""

    project_root = Path(__file__).parent.parent
    coordinator = AgentCoordinator(config)

    # Create sample tasks for demonstration
    sample_tasks = [
        AgentTask(
            id="build_package",
            task_type=TaskType.BUILD,
            command=["uv", "build"],
            working_dir=project_root,
            priority=TaskPriority.HIGH,
        ),
        AgentTask(
            id="run_tests",
            task_type=TaskType.TEST,
            command=["uv", "run", "pytest", "-v"],
            working_dir=project_root,
            priority=TaskPriority.HIGH,
        ),
        AgentTask(
            id="validate_build",
            task_type=TaskType.VALIDATE,
            command=["python", "scripts/validate-build.py", "--verbose"],
            working_dir=project_root,
            dependencies=["build_package"],
            priority=TaskPriority.NORMAL,
        ),
        AgentTask(
            id="security_scan",
            task_type=TaskType.VALIDATE,
            command=["ruff", "check", "src/"],
            working_dir=project_root,
            priority=TaskPriority.LOW,
        ),
    ]

    async def run_orchestration():
        if monitor:
            # Run with live monitoring
            with Live(
                coordinator.create_status_display(), refresh_per_second=2
            ) as live:
                results = await coordinator.execute_tasks(sample_tasks)
                live.update(coordinator.create_status_display())
                return results
        else:
            # Run without monitoring
            return await coordinator.execute_tasks(sample_tasks)

    # Execute tasks
    results = asyncio.run(run_orchestration())

    # Display results
    if output_format == "json":
        output = {
            "summary": coordinator.get_summary_stats(),
            "results": {
                task_id: {
                    "status": result.status.value,
                    "duration": result.duration,
                    "return_code": result.return_code,
                    "error_message": result.error_message,
                }
                for task_id, result in results.items()
            },
        }
        console.print_json(json.dumps(output, indent=2))
    else:
        # Table format
        results_table = Table(title="Execution Results")
        results_table.add_column("Task ID", style="cyan")
        results_table.add_column("Status", style="magenta")
        results_table.add_column("Duration", style="yellow")
        results_table.add_column("Return Code", style="white")
        results_table.add_column("Error", style="red")

        for task_id, result in results.items():
            status_color = {
                "success": "[green]SUCCESS[/green]",
                "failed": "[red]FAILED[/red]",
                "cancelled": "[yellow]CANCELLED[/yellow]",
            }.get(result.status.value, result.status.value)

            results_table.add_row(
                task_id,
                status_color,
                f"{result.duration:.2f}s",
                str(result.return_code) if result.return_code is not None else "N/A",
                result.error_message or "None",
            )

        console.print(results_table)

        # Summary
        stats = coordinator.get_summary_stats()
        console.print(
            f"\nSummary: {stats['successful_tasks']}/{stats['total_tasks']} tasks succeeded "
            f"({stats['success_rate']:.1f}% success rate)"
        )


@app.command()
def status():
    """Show current agent coordinator status."""
    coordinator = AgentCoordinator()
    console.print(coordinator.create_status_display())


@app.command()
def build():
    """Run build tasks using agent coordination."""

    project_root = Path(__file__).parent.parent
    coordinator = AgentCoordinator()

    build_tasks = [
        AgentTask(
            id="clean_dist",
            task_type=TaskType.CLEANUP,
            command=["rm", "-rf", "dist/"],
            working_dir=project_root,
            priority=TaskPriority.HIGH,
        ),
        AgentTask(
            id="build_wheel",
            task_type=TaskType.BUILD,
            command=["uv", "build", "--wheel"],
            working_dir=project_root,
            dependencies=["clean_dist"],
            priority=TaskPriority.HIGH,
        ),
        AgentTask(
            id="build_sdist",
            task_type=TaskType.BUILD,
            command=["uv", "build", "--sdist"],
            working_dir=project_root,
            dependencies=["clean_dist"],
            priority=TaskPriority.NORMAL,
        ),
    ]

    results = asyncio.run(coordinator.execute_tasks(build_tasks))

    # Check if all builds succeeded
    success = all(result.status == AgentStatus.SUCCESS for result in results.values())

    if success:
        console.print("[green]✅ All build tasks completed successfully![/green]")
    else:
        console.print("[red]❌ Some build tasks failed[/red]")
        for task_id, result in results.items():
            if result.status != AgentStatus.SUCCESS:
                console.print(f"  {task_id}: {result.error_message}")

    sys.exit(0 if success else 1)


@app.command()
def test():
    """Run test tasks using agent coordination."""

    project_root = Path(__file__).parent.parent
    coordinator = AgentCoordinator()

    test_tasks = [
        AgentTask(
            id="unit_tests",
            task_type=TaskType.TEST,
            command=["uv", "run", "pytest", "tests/", "-v"],
            working_dir=project_root,
            priority=TaskPriority.HIGH,
        ),
        AgentTask(
            id="coverage_report",
            task_type=TaskType.TEST,
            command=[
                "uv",
                "run",
                "pytest",
                "--cov=src/quickhooks",
                "--cov-report=html",
            ],
            working_dir=project_root,
            priority=TaskPriority.NORMAL,
        ),
        AgentTask(
            id="type_check",
            task_type=TaskType.VALIDATE,
            command=["uv", "run", "mypy", "src/quickhooks"],
            working_dir=project_root,
            priority=TaskPriority.LOW,
        ),
    ]

    results = asyncio.run(coordinator.execute_tasks(test_tasks))

    # Display results
    success = all(result.status == AgentStatus.SUCCESS for result in results.values())

    if success:
        console.print("[green]✅ All test tasks completed successfully![/green]")
    else:
        console.print("[red]❌ Some test tasks failed[/red]")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app()
