"""Tests for parallel processing hooks."""

import tempfile
from pathlib import Path

import pytest

from quickhooks.core.processor import ProcessingPriority
from quickhooks.hooks.parallel import (
    DataParallelHook,
    MultiHookProcessor,
    ParallelHook,
    PipelineHook,
)
from quickhooks.models import HookInput, HookOutput


class TestParallelHook:
    """Test cases for ParallelHook base class."""

    @pytest.fixture
    def parallel_hook(self):
        """Create a test parallel hook."""

        class TestParallelHook(ParallelHook):
            async def create_processing_tasks(self, input_data):
                return []

            async def aggregate_results(self, results):
                return HookOutput(allowed=True, modified_input=None)

        return TestParallelHook("test_hook", max_workers=2)

    def test_parallel_hook_initialization(self, parallel_hook):
        """Test parallel hook initialization."""
        assert parallel_hook.name == "test_hook"
        assert parallel_hook.processor.max_workers == 2

    @pytest.mark.asyncio
    async def test_execute_parallel_no_tasks(self, parallel_hook):
        """Test execute_parallel with no tasks."""
        input_data = HookInput(tool_name="test_tool", tool_input={"param": "value"})

        result = await parallel_hook.execute_parallel(input_data)

        assert result.allowed is True
        assert "No tasks to process" in result.message

    def test_get_processing_stats(self, parallel_hook):
        """Test getting processing statistics."""
        stats = parallel_hook.get_processing_stats()
        assert isinstance(stats, dict)
        assert "total_tasks" in stats


class TestMultiHookProcessor:
    """Test cases for MultiHookProcessor."""

    @pytest.fixture
    def mock_hook_scripts(self):
        """Create temporary mock hook scripts."""
        scripts = []

        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(f"""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Simple response
output = {{
    "allowed": True,
    "modified_input": input_data.get("tool_input"),
    "message": "Processed by hook {i}"
}}

print(json.dumps(output))
""")
                f.flush()
                scripts.append(Path(f.name))

        yield scripts

        # Cleanup
        for script in scripts:
            script.unlink(missing_ok=True)

    @pytest.fixture
    def multi_hook_processor(self, mock_hook_scripts):
        """Create a multi-hook processor with test scripts."""
        processor = MultiHookProcessor(hook_paths=mock_hook_scripts, max_workers=2)
        return processor

    def test_multi_hook_initialization(self):
        """Test multi-hook processor initialization."""
        processor = MultiHookProcessor()
        assert processor.name == "multi_hook_processor"
        assert len(processor.hook_paths) == 0

    def test_add_hook_path(self):
        """Test adding hook paths."""
        processor = MultiHookProcessor()
        processor.add_hook_path("/path/to/hook.py")

        assert len(processor.hook_paths) == 1
        assert processor.hook_paths[0] == Path("/path/to/hook.py")

    @pytest.mark.asyncio
    async def test_create_processing_tasks(self, multi_hook_processor):
        """Test creating processing tasks."""
        input_data = HookInput(tool_name="test_tool", tool_input={"param": "value"})

        tasks = await multi_hook_processor.create_processing_tasks(input_data)

        assert len(tasks) == 3
        for i, task in enumerate(tasks):
            assert task.task_id.startswith(f"hook_{i}")
            assert task.priority == ProcessingPriority.NORMAL

    @pytest.mark.asyncio
    async def test_aggregate_results(self, multi_hook_processor):
        """Test aggregating results from multiple hooks."""
        results = [
            {"allowed": True, "message": "Hook 1 OK"},
            {
                "allowed": True,
                "message": "Hook 2 OK",
                "modified_input": {"updated": True},
            },
            {"allowed": True, "message": "Hook 3 OK"},
        ]

        output = await multi_hook_processor.aggregate_results(results)

        assert output.allowed is True
        assert "Hook 1 OK; Hook 2 OK; Hook 3 OK" in output.message
        assert output.modified_input == {"updated": True}
        assert output.metadata["hook_count"] == 3

    @pytest.mark.asyncio
    async def test_aggregate_results_with_failure(self, multi_hook_processor):
        """Test aggregating results when some hooks fail."""
        results = [
            {"allowed": True, "message": "Hook 1 OK"},
            {"allowed": False, "message": "Hook 2 failed"},
            {"allowed": True, "message": "Hook 3 OK"},
        ]

        output = await multi_hook_processor.aggregate_results(results)

        assert output.allowed is False
        assert "Hook 1 OK; Hook 2 failed; Hook 3 OK" in output.message

    @pytest.mark.asyncio
    async def test_execute_multi_hook(self, multi_hook_processor):
        """Test executing multiple hooks."""
        input_data = HookInput(tool_name="test_tool", tool_input={"param": "value"})

        # This will actually execute the hooks
        result = await multi_hook_processor.execute(input_data)

        # Should succeed with all hooks
        assert result.allowed is True
        assert result.metadata["hook_count"] == 3


class TestDataParallelHook:
    """Test cases for DataParallelHook."""

    @pytest.fixture
    def mock_processor_hook(self):
        """Create a mock data processor hook."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Process the data chunk - just double each number
data = input_data.get("tool_input", {}).get("data", [])
processed_data = [x * 2 if isinstance(x, (int, float)) else x for x in data]

output = {
    "allowed": True,
    "modified_input": {"data": processed_data},
    "chunk_id": input_data.get("tool_input", {}).get("chunk_id", 0)
}

print(json.dumps(output))
""")
            f.flush()
            yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def data_parallel_hook(self, mock_processor_hook):
        """Create a data parallel hook with test processor."""
        hook = DataParallelHook(
            chunk_size=3, max_workers=2, processor_hook_path=mock_processor_hook
        )
        return hook

    def test_data_parallel_initialization(self):
        """Test data parallel hook initialization."""
        hook = DataParallelHook(chunk_size=5)
        assert hook.name == "data_parallel_hook"
        assert hook.chunk_size == 5

    def test_set_processor_hook(self, data_parallel_hook):
        """Test setting processor hook path."""
        data_parallel_hook.set_processor_hook("/new/path.py")
        assert data_parallel_hook.processor_hook_path == Path("/new/path.py")

    def test_chunk_data(self, data_parallel_hook):
        """Test data chunking."""
        data = list(range(10))  # [0, 1, 2, ..., 9]
        chunks = data_parallel_hook.chunk_data(data)

        assert len(chunks) == 4  # 10 items / 3 chunk_size = 4 chunks
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]

    @pytest.mark.asyncio
    async def test_create_processing_tasks(self, data_parallel_hook):
        """Test creating processing tasks for data chunks."""
        input_data = HookInput(
            tool_name="data_processor", tool_input={"data": list(range(7))}
        )

        tasks = await data_parallel_hook.create_processing_tasks(input_data)

        assert len(tasks) == 3  # 7 items / 3 chunk_size = 3 chunks

        # Check first task
        assert tasks[0].task_id == "chunk_0"
        task_input = tasks[0].input_data
        assert task_input["tool_input"]["data"] == [0, 1, 2]
        assert task_input["tool_input"]["chunk_id"] == 0
        assert task_input["tool_input"]["total_chunks"] == 3

    @pytest.mark.asyncio
    async def test_create_processing_tasks_no_processor(self):
        """Test creating tasks without processor hook set."""
        hook = DataParallelHook()
        input_data = HookInput(tool_name="test", tool_input={"data": [1, 2, 3]})

        with pytest.raises(ValueError, match="Processor hook path not set"):
            await hook.create_processing_tasks(input_data)

    @pytest.mark.asyncio
    async def test_create_processing_tasks_invalid_data(self, data_parallel_hook):
        """Test creating tasks with invalid data type."""
        input_data = HookInput(tool_name="test", tool_input={"data": "not a list"})

        with pytest.raises(ValueError, match="Data must be a list"):
            await data_parallel_hook.create_processing_tasks(input_data)

    @pytest.mark.asyncio
    async def test_aggregate_results(self, data_parallel_hook):
        """Test aggregating results from data chunks."""
        results = [
            {"allowed": True, "modified_input": {"data": [0, 2, 4]}, "chunk_id": 0},
            {"allowed": True, "modified_input": {"data": [6, 8, 10]}, "chunk_id": 1},
            {"allowed": True, "modified_input": {"data": [12]}, "chunk_id": 2},
        ]

        output = await data_parallel_hook.aggregate_results(results)

        assert output.allowed is True
        assert output.modified_input["data"] == [0, 2, 4, 6, 8, 10, 12]
        assert output.metadata["chunk_count"] == 3
        assert output.metadata["total_items"] == 7

    @pytest.mark.asyncio
    async def test_execute_data_parallel(self, data_parallel_hook):
        """Test executing data parallel processing."""
        input_data = HookInput(
            tool_name="data_processor", tool_input={"data": [1, 2, 3, 4, 5]}
        )

        result = await data_parallel_hook.execute(input_data)

        # Should succeed and double all numbers
        assert result.allowed is True
        assert result.modified_input["data"] == [2, 4, 6, 8, 10]


class TestPipelineHook:
    """Test cases for PipelineHook."""

    @pytest.fixture
    def mock_pipeline_hooks(self):
        """Create mock pipeline stage hooks."""
        scripts = []

        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                stage_num = i + 1
                script_content = f"""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Get data from previous stage or original input
data = input_data.get("tool_input", {{}}).get("value", 0)
processed_value = data + {stage_num}  # Add stage number

output = {{
    "allowed": True,
    "modified_input": {{"value": processed_value}},
    "message": "Stage {stage_num} complete"
}}

print(json.dumps(output))
"""
                f.write(script_content)
                f.flush()
                scripts.append(Path(f.name))

        yield scripts

        # Cleanup
        for script in scripts:
            script.unlink(missing_ok=True)

    @pytest.fixture
    def pipeline_hook(self, mock_pipeline_hooks):
        """Create a pipeline hook with test stages."""
        hook = PipelineHook(hook_paths=mock_pipeline_hooks)
        return hook

    def test_pipeline_initialization(self):
        """Test pipeline hook initialization."""
        hook = PipelineHook()
        assert hook.name == "pipeline_hook"
        assert len(hook.hook_paths) == 0
        assert hook.max_workers == 1  # Pipeline is sequential

    def test_add_pipeline_stage(self, pipeline_hook):
        """Test adding pipeline stages."""
        original_count = len(pipeline_hook.hook_paths)
        pipeline_hook.add_pipeline_stage("/new/stage.py")

        assert len(pipeline_hook.hook_paths) == original_count + 1
        assert pipeline_hook.hook_paths[-1] == Path("/new/stage.py")

    @pytest.mark.asyncio
    async def test_create_processing_tasks(self, pipeline_hook):
        """Test creating pipeline tasks with dependencies."""
        input_data = HookInput(tool_name="pipeline", tool_input={"value": 0})

        tasks = await pipeline_hook.create_processing_tasks(input_data)

        assert len(tasks) == 3

        # First stage should have no dependencies
        assert len(tasks[0].dependencies) == 0
        assert tasks[0].task_id.startswith("stage_0_")

        # Second stage should depend on first
        assert len(tasks[1].dependencies) == 1
        assert tasks[0].task_id in tasks[1].dependencies

        # Third stage should depend on second
        assert len(tasks[2].dependencies) == 1
        assert tasks[1].task_id in tasks[2].dependencies

    @pytest.mark.asyncio
    async def test_aggregate_results(self, pipeline_hook):
        """Test aggregating pipeline results."""
        results = [
            {
                "allowed": True,
                "modified_input": {"value": 1},
                "message": "Stage 1 complete",
            },
            {
                "allowed": True,
                "modified_input": {"value": 3},
                "message": "Stage 2 complete",
            },
            {
                "allowed": True,
                "modified_input": {"value": 6},
                "message": "Stage 3 complete",
            },
        ]

        output = await pipeline_hook.aggregate_results(results)

        assert output.allowed is True
        assert output.modified_input == {"value": 6}  # Final stage result
        assert (
            "Stage 1: Stage 1 complete; Stage 2: Stage 2 complete; Stage 3: Stage 3 complete"
            in output.message
        )
        assert output.metadata["pipeline_stages"] == 3
        assert output.metadata["final_stage"] == 2

    @pytest.mark.asyncio
    async def test_aggregate_results_empty(self, pipeline_hook):
        """Test aggregating empty results."""
        output = await pipeline_hook.aggregate_results([])

        assert output.allowed is False
        assert "No pipeline results" in output.message

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, pipeline_hook):
        """Test executing pipeline processing."""
        input_data = HookInput(tool_name="pipeline", tool_input={"value": 0})

        # This should use pipeline mode
        result = await pipeline_hook.execute(input_data)

        # Should succeed and process through all stages
        assert result.allowed is True
        # Final value should be 0 + 1 + 2 + 3 = 6
        assert result.modified_input["value"] == 6
