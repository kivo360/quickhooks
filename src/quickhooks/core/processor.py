"""Core parallel processing engine for QuickHooks framework.

This module provides advanced parallel processing capabilities with support for
concurrent hook execution, pipeline processing, and workflow visualization.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from quickhooks.executor import ExecutionResult, HookExecutor


class ProcessingMode(str, Enum):
    """Processing execution modes."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    BATCH = "batch"


class ProcessingPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProcessingTask:
    """Individual processing task definition."""

    task_id: str
    hook_path: str | Path
    input_data: dict[str, Any]
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    timeout: float | None = None
    context: dict[str, Any] | None = None
    dependencies: set[str] = field(default_factory=set)
    retries: int = 0
    max_retries: int = 3

    def __hash__(self) -> int:
        return hash(self.task_id)


@dataclass
class ProcessingResult:
    """Result of processing task execution."""

    task_id: str
    execution_result: ExecutionResult
    success: bool
    start_time: float
    end_time: float
    attempts: int = 1

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class ProcessingStats:
    """Statistics for processing session."""

    def __init__(self):
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_duration = 0.0
        self.concurrent_peak = 0
        self.retry_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.completed_tasks / max(self.total_tasks, 1),
            "total_duration": self.total_duration,
            "average_duration": self.total_duration / max(self.completed_tasks, 1),
            "concurrent_peak": self.concurrent_peak,
            "retry_count": self.retry_count,
        }


class ParallelProcessor:
    """Advanced parallel processing engine for QuickHooks.

    Features:
    - Concurrent hook execution with configurable limits
    - Task priority and dependency management
    - Pipeline processing with intermediate results
    - Retry mechanisms with exponential backoff
    - Resource usage monitoring and throttling
    - Comprehensive statistics and reporting
    """

    def __init__(
        self,
        max_workers: int = 4,
        default_timeout: float = 30.0,
        enable_monitoring: bool = True,
    ):
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.enable_monitoring = enable_monitoring

        self.executor = HookExecutor(default_timeout=default_timeout)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)

        # Processing state
        self.active_tasks: dict[str, ProcessingTask] = {}
        self.completed_tasks: dict[str, ProcessingResult] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results_queue: asyncio.Queue = asyncio.Queue()

        # Statistics and monitoring
        self.stats = ProcessingStats()
        self.current_workers = 0
        self._shutdown_event = asyncio.Event()

    async def submit_task(self, task: ProcessingTask) -> None:
        """Submit a task for processing."""
        self.active_tasks[task.task_id] = task
        await self.task_queue.put(task)
        self.stats.total_tasks += 1

    async def submit_tasks(self, tasks: list[ProcessingTask]) -> None:
        """Submit multiple tasks for processing."""
        for task in tasks:
            await self.submit_task(task)

    async def process_task(self, task: ProcessingTask) -> ProcessingResult:
        """Process a single task with retry logic."""
        start_time = time.perf_counter()
        attempts = 0
        last_error = None

        while attempts <= task.max_retries:
            attempts += 1

            try:
                # Execute the hook
                execution_result = await self.executor.execute_with_context(
                    hook_script=task.hook_path,
                    input_data=task.input_data,
                    context=task.context,
                    timeout=task.timeout or self.default_timeout,
                )

                end_time = time.perf_counter()

                result = ProcessingResult(
                    task_id=task.task_id,
                    execution_result=execution_result,
                    success=execution_result.exit_code == 0,
                    start_time=start_time,
                    end_time=end_time,
                    attempts=attempts,
                )

                if result.success:
                    self.stats.completed_tasks += 1
                else:
                    self.stats.failed_tasks += 1

                return result

            except Exception as e:
                last_error = e
                if attempts <= task.max_retries:
                    # Exponential backoff for retries
                    delay = 2 ** (attempts - 1)
                    await asyncio.sleep(delay)
                    self.stats.retry_count += 1
                    continue
                else:
                    break

        # All retries exhausted
        end_time = time.perf_counter()
        self.stats.failed_tasks += 1

        # Create a failed execution result

        failed_execution = ExecutionResult(
            exit_code=-1,
            output={"error": str(last_error)},
            stdout="",
            stderr=str(last_error),
            duration=end_time - start_time,
        )

        return ProcessingResult(
            task_id=task.task_id,
            execution_result=failed_execution,
            success=False,
            start_time=start_time,
            end_time=end_time,
            attempts=attempts,
        )

    async def worker(self) -> None:
        """Worker coroutine for processing tasks."""
        while not self._shutdown_event.is_set():
            try:
                # Get task with timeout to allow shutdown
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                self.current_workers += 1
                self.stats.concurrent_peak = max(
                    self.stats.concurrent_peak, self.current_workers
                )

                # Check dependencies
                if not self._check_dependencies(task):
                    # Requeue task if dependencies not met
                    await asyncio.sleep(0.1)
                    await self.task_queue.put(task)
                    continue

                # Process the task
                result = await self.process_task(task)

                # Store result and cleanup
                self.completed_tasks[task.task_id] = result
                del self.active_tasks[task.task_id]
                await self.results_queue.put(result)

                self.current_workers -= 1
                self.task_queue.task_done()

            except TimeoutError:
                # Timeout waiting for tasks - continue to check shutdown
                continue
            except Exception as e:
                self.current_workers = max(0, self.current_workers - 1)
                # Log error but continue processing
                print(f"Worker error: {e}")

    def _check_dependencies(self, task: ProcessingTask) -> bool:
        """Check if task dependencies are satisfied."""
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
            if not self.completed_tasks[dep_id].success:
                return False

        return True

    async def run_sequential(
        self, tasks: list[ProcessingTask]
    ) -> list[ProcessingResult]:
        """Run tasks sequentially."""
        results = []

        for task in sorted(tasks, key=lambda t: t.priority.value):
            result = await self.process_task(task)
            results.append(result)
            self.completed_tasks[task.task_id] = result

        return results

    async def run_parallel(self, tasks: list[ProcessingTask]) -> list[ProcessingResult]:
        """Run tasks in parallel with worker pool."""
        # Submit all tasks
        await self.submit_tasks(tasks)

        # Start workers
        workers = [
            asyncio.create_task(self.worker())
            for _ in range(min(self.max_workers, len(tasks)))
        ]

        # Wait for all tasks to complete
        await self.task_queue.join()

        # Shutdown workers
        self._shutdown_event.set()
        await asyncio.gather(*workers, return_exceptions=True)
        self._shutdown_event.clear()

        # Collect results
        results = []
        for task in tasks:
            if task.task_id in self.completed_tasks:
                results.append(self.completed_tasks[task.task_id])

        return results

    async def run_pipeline(self, tasks: list[ProcessingTask]) -> list[ProcessingResult]:
        """Run tasks in pipeline mode with intermediate results."""
        results = []
        pipeline_context = {}

        # Sort tasks by dependencies to determine pipeline order
        ordered_tasks = self._topological_sort(tasks)

        for task in ordered_tasks:
            # Merge pipeline context with task context
            if task.context:
                merged_context = {**pipeline_context, **task.context}
            else:
                merged_context = pipeline_context.copy()

            task.context = merged_context

            # Process task
            result = await self.process_task(task)
            results.append(result)

            # Update pipeline context with results
            if result.success:
                pipeline_context[f"result_{task.task_id}"] = (
                    result.execution_result.output
                )

        return results

    def _topological_sort(self, tasks: list[ProcessingTask]) -> list[ProcessingTask]:
        """Sort tasks based on dependencies using topological sort."""
        # Simple implementation - in production, use more robust algorithm
        task_map = {task.task_id: task for task in tasks}
        visited = set()
        result = []

        def dfs(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)

            if task_id in task_map:
                task = task_map[task_id]
                for dep_id in task.dependencies:
                    dfs(dep_id)
                result.append(task)

        for task in tasks:
            dfs(task.task_id)

        return result

    async def run_batch(
        self, tasks: list[ProcessingTask], batch_size: int = 10
    ) -> list[ProcessingResult]:
        """Run tasks in batches to manage resource usage."""
        all_results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_results = await self.run_parallel(batch)
            all_results.extend(batch_results)

            # Small delay between batches
            await asyncio.sleep(0.1)

        return all_results

    async def run(
        self,
        tasks: list[ProcessingTask],
        mode: ProcessingMode = ProcessingMode.PARALLEL,
    ) -> list[ProcessingResult]:
        """Run tasks using specified processing mode."""
        start_time = time.perf_counter()

        try:
            if mode == ProcessingMode.SEQUENTIAL:
                results = await self.run_sequential(tasks)
            elif mode == ProcessingMode.PARALLEL:
                results = await self.run_parallel(tasks)
            elif mode == ProcessingMode.PIPELINE:
                results = await self.run_pipeline(tasks)
            elif mode == ProcessingMode.BATCH:
                results = await self.run_batch(tasks)
            else:
                raise ValueError(f"Unknown processing mode: {mode}")

            return results

        finally:
            end_time = time.perf_counter()
            self.stats.total_duration = end_time - start_time

    def get_stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self.stats

    def get_active_tasks(self) -> list[str]:
        """Get list of currently active task IDs."""
        return list(self.active_tasks.keys())

    def get_results(self) -> dict[str, ProcessingResult]:
        """Get all completed results."""
        return self.completed_tasks.copy()

    async def shutdown(self) -> None:
        """Gracefully shutdown the processor."""
        self._shutdown_event.set()
        self.thread_pool.shutdown(wait=True)

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, "thread_pool"):
            self.thread_pool.shutdown(wait=False)
