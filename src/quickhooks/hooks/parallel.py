"""Parallel processing hooks for QuickHooks framework.

This module provides specialized hooks that leverage the parallel processing
capabilities of the core processor module.
"""

from pathlib import Path
from typing import Any

from quickhooks.core.processor import (
    ParallelProcessor,
    ProcessingMode,
    ProcessingPriority,
    ProcessingTask,
)
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput


class ParallelHook(BaseHook):
    """Base class for hooks that support parallel processing."""

    def __init__(
        self,
        name: str,
        description: str = "",
        max_workers: int = 4,
        default_timeout: float = 30.0,
    ):
        super().__init__(name, description)
        self.processor = ParallelProcessor(
            max_workers=max_workers, default_timeout=default_timeout
        )

    async def create_processing_tasks(
        self, input_data: HookInput
    ) -> list[ProcessingTask]:
        """Create processing tasks from hook input.

        Subclasses should implement this method to define how to break
        down the hook input into parallel processing tasks.
        """
        raise NotImplementedError("Subclasses must implement create_processing_tasks")

    async def aggregate_results(self, results: list[Any]) -> HookOutput:
        """Aggregate results from parallel tasks into final output.

        Subclasses should implement this method to define how to combine
        results from multiple parallel tasks.
        """
        raise NotImplementedError("Subclasses must implement aggregate_results")

    async def execute_parallel(
        self, input_data: HookInput, mode: ProcessingMode = ProcessingMode.PARALLEL
    ) -> HookOutput:
        """Execute the hook using parallel processing."""
        try:
            # Create processing tasks
            tasks = await self.create_processing_tasks(input_data)

            if not tasks:
                return HookOutput(
                    allowed=True,
                    modified_input=input_data.tool_input,
                    message="No tasks to process",
                )

            # Run tasks using specified mode
            results = await self.processor.run(tasks, mode)

            # Extract successful results
            successful_results = [
                r.execution_result.output for r in results if r.success
            ]

            # Aggregate results
            if successful_results:
                return await self.aggregate_results(successful_results)
            else:
                # All tasks failed
                error_messages = [
                    r.execution_result.stderr for r in results if not r.success
                ]
                return HookOutput(
                    allowed=False,
                    modified_input=input_data.tool_input,
                    message=f"All parallel tasks failed: {'; '.join(error_messages)}",
                )

        except Exception as e:
            return HookOutput(
                allowed=False,
                modified_input=input_data.tool_input,
                message=f"Parallel execution failed: {str(e)}",
            )

    async def execute(self, input_data: HookInput) -> HookOutput:
        """Default execution uses parallel mode."""
        return await self.execute_parallel(input_data)

    def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        return self.processor.get_stats().to_dict()


class MultiHookProcessor(ParallelHook):
    """Hook that processes multiple sub-hooks in parallel.

    This hook allows you to run multiple different hooks concurrently
    and aggregate their results.
    """

    def __init__(
        self,
        name: str = "multi_hook_processor",
        description: str = "Processes multiple hooks in parallel",
        hook_paths: list[str | Path] | None = None,
        max_workers: int = 4,
    ):
        super().__init__(name, description, max_workers)
        self.hook_paths = hook_paths or []

    def add_hook_path(self, path: str | Path) -> None:
        """Add a hook path to the processor."""
        self.hook_paths.append(Path(path))

    async def create_processing_tasks(
        self, input_data: HookInput
    ) -> list[ProcessingTask]:
        """Create tasks for each hook path."""
        tasks = []

        for i, hook_path in enumerate(self.hook_paths):
            task = ProcessingTask(
                task_id=f"hook_{i}_{hook_path.stem}",
                hook_path=hook_path,
                input_data=input_data.model_dump(),
                priority=ProcessingPriority.NORMAL,
            )
            tasks.append(task)

        return tasks

    async def aggregate_results(self, results: list[Any]) -> HookOutput:
        """Aggregate results from multiple hooks."""
        # Check if all hooks allow the operation
        all_allowed = all(result.get("allowed", True) for result in results)

        # Collect messages
        messages = [
            result.get("message", "") for result in results if result.get("message")
        ]

        # Use the last modification or original input
        modified_input = None
        for result in reversed(results):
            if result.get("modified_input"):
                modified_input = result["modified_input"]
                break

        return HookOutput(
            allowed=all_allowed,
            modified_input=modified_input,
            message="; ".join(messages) if messages else None,
            metadata={"hook_count": len(results), "successful_hooks": len(results)},
        )


class DataParallelHook(ParallelHook):
    """Hook that processes data in parallel chunks.

    This hook is useful for processing large datasets by splitting
    them into chunks and processing each chunk in parallel.
    """

    def __init__(
        self,
        name: str = "data_parallel_hook",
        description: str = "Processes data in parallel chunks",
        chunk_size: int = 10,
        max_workers: int = 4,
        processor_hook_path: str | Path | None = None,
    ):
        super().__init__(name, description, max_workers)
        self.chunk_size = chunk_size
        self.processor_hook_path = processor_hook_path

    def set_processor_hook(self, path: str | Path) -> None:
        """Set the hook used to process each data chunk."""
        self.processor_hook_path = Path(path)

    def chunk_data(self, data: list[Any]) -> list[list[Any]]:
        """Split data into chunks for parallel processing."""
        chunks = []
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i : i + self.chunk_size]
            chunks.append(chunk)
        return chunks

    async def create_processing_tasks(
        self, input_data: HookInput
    ) -> list[ProcessingTask]:
        """Create tasks for each data chunk."""
        if not self.processor_hook_path:
            raise ValueError("Processor hook path not set")

        # Extract data to process from input
        data_to_process = input_data.tool_input.get("data", [])
        if not isinstance(data_to_process, list):
            raise ValueError("Data must be a list for parallel processing")

        # Split data into chunks
        chunks = self.chunk_data(data_to_process)

        tasks = []
        for i, chunk in enumerate(chunks):
            # Create modified input for this chunk
            chunk_input = input_data.model_copy()
            chunk_input.tool_input["data"] = chunk
            chunk_input.tool_input["chunk_id"] = i
            chunk_input.tool_input["total_chunks"] = len(chunks)

            task = ProcessingTask(
                task_id=f"chunk_{i}",
                hook_path=self.processor_hook_path,
                input_data=chunk_input.model_dump(),
                priority=ProcessingPriority.NORMAL,
            )
            tasks.append(task)

        return tasks

    async def aggregate_results(self, results: list[Any]) -> HookOutput:
        """Aggregate results from data chunks."""
        # Collect processed data from all chunks
        processed_data = []
        messages = []

        # Sort results by chunk_id to maintain order
        sorted_results = sorted(results, key=lambda r: r.get("chunk_id", 0))

        for result in sorted_results:
            if result.get("allowed", True):
                chunk_data = result.get("modified_input", {}).get("data", [])
                processed_data.extend(chunk_data)

            if result.get("message"):
                messages.append(result["message"])

        # All chunks must be allowed for overall success
        all_allowed = all(result.get("allowed", True) for result in results)

        return HookOutput(
            allowed=all_allowed,
            modified_input={"data": processed_data},
            message="; ".join(messages) if messages else None,
            metadata={"chunk_count": len(results), "total_items": len(processed_data)},
        )


class PipelineHook(ParallelHook):
    """Hook that processes data through a pipeline of sub-hooks.

    This hook runs multiple hooks in sequence, where the output of
    each hook becomes the input to the next hook.
    """

    def __init__(
        self,
        name: str = "pipeline_hook",
        description: str = "Processes data through a pipeline of hooks",
        hook_paths: list[str | Path] | None = None,
        max_workers: int = 1,  # Pipeline is inherently sequential
    ):
        super().__init__(name, description, max_workers)
        self.hook_paths = hook_paths or []

    def add_pipeline_stage(self, path: str | Path) -> None:
        """Add a hook to the pipeline."""
        self.hook_paths.append(Path(path))

    async def create_processing_tasks(
        self, input_data: HookInput
    ) -> list[ProcessingTask]:
        """Create pipeline tasks with dependencies."""
        tasks = []

        for i, hook_path in enumerate(self.hook_paths):
            task_id = f"stage_{i}_{hook_path.stem}"

            # Set dependencies - each stage depends on the previous one
            dependencies = set()
            if i > 0:
                prev_task_id = f"stage_{i - 1}_{self.hook_paths[i - 1].stem}"
                dependencies.add(prev_task_id)

            task = ProcessingTask(
                task_id=task_id,
                hook_path=hook_path,
                input_data=input_data.model_dump(),
                dependencies=dependencies,
                priority=ProcessingPriority.NORMAL,
            )
            tasks.append(task)

        return tasks

    async def aggregate_results(self, results: list[Any]) -> HookOutput:
        """Return the result of the final pipeline stage."""
        if not results:
            return HookOutput(
                allowed=False, modified_input=None, message="No pipeline results"
            )

        # The final result is the output of the last stage
        final_result = results[-1]

        # Collect messages from all stages
        messages = [
            f"Stage {i}: {result.get('message', 'OK')}"
            for i, result in enumerate(results)
            if result.get("message")
        ]

        return HookOutput(
            allowed=final_result.get("allowed", True),
            modified_input=final_result.get("modified_input"),
            message="; ".join(messages) if messages else None,
            metadata={"pipeline_stages": len(results), "final_stage": len(results) - 1},
        )

    async def execute(self, input_data: HookInput) -> HookOutput:
        """Execute pipeline using pipeline mode."""
        return await self.execute_parallel(input_data, ProcessingMode.PIPELINE)
