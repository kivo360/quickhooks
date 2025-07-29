"""Tests for core parallel processor module."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from quickhooks.core.processor import (
    ParallelProcessor,
    ProcessingMode,
    ProcessingPriority,
    ProcessingResult,
    ProcessingStats,
    ProcessingTask,
)
from quickhooks.executor import ExecutionResult


class TestProcessingTask:
    """Test cases for ProcessingTask."""

    def test_task_creation(self):
        """Test basic task creation."""
        task = ProcessingTask(
            task_id="test_task",
            hook_path="/path/to/hook.py",
            input_data={"tool_name": "test", "tool_input": {}},
            priority=ProcessingPriority.HIGH,
        )

        assert task.task_id == "test_task"
        assert task.hook_path == "/path/to/hook.py"
        assert task.priority == ProcessingPriority.HIGH
        assert task.retries == 0
        assert task.max_retries == 3

    def test_task_hash(self):
        """Test task hashing for use in sets/dicts."""
        task1 = ProcessingTask("task1", "/path", {})
        task2 = ProcessingTask("task1", "/different/path", {})
        task3 = ProcessingTask("task3", "/path", {})

        # Same task_id should have same hash
        assert hash(task1) == hash(task2)
        assert hash(task1) != hash(task3)

    def test_task_dependencies(self):
        """Test task dependency handling."""
        task = ProcessingTask(
            task_id="dependent_task",
            hook_path="/path",
            input_data={},
            dependencies={"task1", "task2"},
        )

        assert len(task.dependencies) == 2
        assert "task1" in task.dependencies
        assert "task2" in task.dependencies


class TestProcessingResult:
    """Test cases for ProcessingResult."""

    def test_result_creation(self):
        """Test basic result creation."""
        execution_result = ExecutionResult(
            exit_code=0,
            output={"allowed": True},
            stdout="success",
            stderr="",
            duration=1.5,
        )

        result = ProcessingResult(
            task_id="test_task",
            execution_result=execution_result,
            success=True,
            start_time=100.0,
            end_time=101.5,
            attempts=1,
        )

        assert result.task_id == "test_task"
        assert result.success is True
        assert result.duration == 1.5
        assert result.attempts == 1

    def test_result_duration_property(self):
        """Test duration property calculation."""
        execution_result = ExecutionResult(0, {}, "", "", 0.5)
        result = ProcessingResult(
            "task", execution_result, True, start_time=10.0, end_time=12.5
        )

        assert result.duration == 2.5


class TestProcessingStats:
    """Test cases for ProcessingStats."""

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = ProcessingStats()

        assert stats.total_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.failed_tasks == 0
        assert stats.total_duration == 0.0
        assert stats.concurrent_peak == 0
        assert stats.retry_count == 0

    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = ProcessingStats()
        stats.total_tasks = 10
        stats.completed_tasks = 8
        stats.failed_tasks = 2
        stats.total_duration = 50.0

        data = stats.to_dict()

        assert data["total_tasks"] == 10
        assert data["completed_tasks"] == 8
        assert data["failed_tasks"] == 2
        assert data["success_rate"] == 0.8
        assert data["average_duration"] == 6.25


class TestParallelProcessor:
    """Test cases for ParallelProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a test processor instance."""
        return ParallelProcessor(max_workers=2, default_timeout=5.0)

    @pytest.fixture
    def mock_hook_script(self):
        """Create a temporary mock hook script."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Simple echo response
output = {
    "allowed": True,
    "modified_input": input_data.get("tool_input"),
    "message": f"Processed by {input_data.get('tool_name', 'unknown')}"
}

print(json.dumps(output))
""")
            f.flush()
            yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_submit_task(self, processor):
        """Test task submission."""
        task = ProcessingTask("test", "/path", {})

        await processor.submit_task(task)

        assert "test" in processor.active_tasks
        assert processor.stats.total_tasks == 1

    @pytest.mark.asyncio
    async def test_submit_multiple_tasks(self, processor):
        """Test submitting multiple tasks."""
        tasks = [ProcessingTask(f"task_{i}", "/path", {}) for i in range(3)]

        await processor.submit_tasks(tasks)

        assert len(processor.active_tasks) == 3
        assert processor.stats.total_tasks == 3

    @pytest.mark.asyncio
    async def test_process_successful_task(self, processor, mock_hook_script):
        """Test processing a successful task."""
        task = ProcessingTask(
            task_id="success_task",
            hook_path=mock_hook_script,
            input_data={"tool_name": "test_tool", "tool_input": {"param": "value"}},
        )

        result = await processor.process_task(task)

        assert result.success is True
        assert result.task_id == "success_task"
        assert result.attempts == 1
        assert result.execution_result.exit_code == 0

    @pytest.mark.asyncio
    async def test_process_task_with_retry(self, processor):
        """Test task processing with retries."""
        # Create a non-existent hook path to trigger retries
        task = ProcessingTask(
            task_id="retry_task",
            hook_path="/nonexistent/hook.py",
            input_data={},
            max_retries=2,
        )

        result = await processor.process_task(task)

        assert result.success is False
        assert result.attempts == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_dependency_checking(self, processor):
        """Test dependency resolution."""
        # Create tasks with dependencies
        task1 = ProcessingTask("task1", "/path", {})
        task2 = ProcessingTask("task2", "/path", {}, dependencies={"task1"})

        # Task without dependencies should be ready
        assert processor._check_dependencies(task1)

        # Task with unmet dependencies should not be ready
        assert not processor._check_dependencies(task2)

        # Add completed dependency
        from quickhooks.executor import ExecutionResult

        processor.completed_tasks["task1"] = ProcessingResult(
            "task1", ExecutionResult(0, {}, "", "", 1.0), True, 0.0, 1.0
        )

        # Now task2 should be ready
        assert processor._check_dependencies(task2)

    @pytest.mark.asyncio
    async def test_run_sequential(self, processor, mock_hook_script):
        """Test sequential processing mode."""
        tasks = [
            ProcessingTask(f"task_{i}", mock_hook_script, {"tool_name": f"tool_{i}"})
            for i in range(3)
        ]

        results = await processor.run_sequential(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_parallel(self, processor, mock_hook_script):
        """Test parallel processing mode."""
        tasks = [
            ProcessingTask(f"task_{i}", mock_hook_script, {"tool_name": f"tool_{i}"})
            for i in range(3)
        ]

        results = await processor.run_parallel(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_pipeline(self, processor, mock_hook_script):
        """Test pipeline processing mode."""
        # Create tasks with dependencies to form a pipeline
        tasks = [
            ProcessingTask("stage1", mock_hook_script, {"tool_name": "stage1"}),
            ProcessingTask(
                "stage2",
                mock_hook_script,
                {"tool_name": "stage2"},
                dependencies={"stage1"},
            ),
            ProcessingTask(
                "stage3",
                mock_hook_script,
                {"tool_name": "stage3"},
                dependencies={"stage2"},
            ),
        ]

        results = await processor.run_pipeline(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_batch(self, processor, mock_hook_script):
        """Test batch processing mode."""
        tasks = [
            ProcessingTask(f"task_{i}", mock_hook_script, {"tool_name": f"tool_{i}"})
            for i in range(5)
        ]

        results = await processor.run_batch(tasks, batch_size=2)

        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_with_different_modes(self, processor, mock_hook_script):
        """Test run method with different processing modes."""
        tasks = [
            ProcessingTask(f"task_{i}", mock_hook_script, {"tool_name": f"tool_{i}"})
            for i in range(2)
        ]

        # Test each mode
        for mode in ProcessingMode:
            results = await processor.run(tasks, mode)
            assert len(results) == 2
            assert all(r.success for r in results)

    def test_get_stats(self, processor):
        """Test statistics retrieval."""
        stats = processor.get_stats()
        assert isinstance(stats, ProcessingStats)

    def test_get_active_tasks(self, processor):
        """Test active tasks retrieval."""
        active = processor.get_active_tasks()
        assert isinstance(active, list)
        assert len(active) == 0

    def test_get_results(self, processor):
        """Test results retrieval."""
        results = processor.get_results()
        assert isinstance(results, dict)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_shutdown(self, processor):
        """Test graceful shutdown."""
        await processor.shutdown()
        assert processor._shutdown_event.is_set()

    def test_topological_sort(self, processor):
        """Test topological sorting of tasks."""
        tasks = [
            ProcessingTask("C", "/path", {}, dependencies={"A", "B"}),
            ProcessingTask("A", "/path", {}),
            ProcessingTask("B", "/path", {}, dependencies={"A"}),
        ]

        sorted_tasks = processor._topological_sort(tasks)

        # A should come first, then B, then C
        task_ids = [t.task_id for t in sorted_tasks]
        assert task_ids.index("A") < task_ids.index("B")
        assert task_ids.index("B") < task_ids.index("C")

    @pytest.mark.asyncio
    async def test_worker_shutdown(self, processor):
        """Test worker graceful shutdown."""
        # Start a worker
        worker_task = asyncio.create_task(processor.worker())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Signal shutdown
        processor._shutdown_event.set()

        # Worker should exit gracefully
        await asyncio.wait_for(worker_task, timeout=2.0)

    @pytest.mark.asyncio
    async def test_concurrent_peak_tracking(self, processor):
        """Test that concurrent peak is tracked correctly."""
        # This is hard to test reliably, but we can at least check initialization
        assert processor.stats.concurrent_peak == 0
        assert processor.current_workers == 0
