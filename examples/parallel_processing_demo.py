#!/usr/bin/env python3
"""
QuickHooks Parallel Processing Demo

This script demonstrates the advanced parallel processing capabilities
of the QuickHooks framework, including:

1. Multi-hook parallel execution
2. Data parallel processing
3. Pipeline processing
4. Workflow visualization with Mermaid diagrams

Run with: python examples/parallel_processing_demo.py
"""

import asyncio
import tempfile
from pathlib import Path

# QuickHooks imports
from quickhooks import (
    DataParallelHook,
    HookInput,
    MermaidWorkflowGenerator,
    MultiHookProcessor,
    ParallelProcessor,
    PipelineHook,
    ProcessingMode,
    ProcessingPriority,
    ProcessingTask,
)


def create_sample_hooks() -> list[Path]:
    """Create sample hook scripts for demonstration."""

    hooks = []

    # Hook 1: Input validator
    validator_hook = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})

# Validate that required fields are present
required_fields = ["command", "description"]
missing_fields = [field for field in required_fields if field not in tool_input]

if missing_fields:
    output = {
        "allowed": False,
        "message": f"Missing required fields: {missing_fields}"
    }
else:
    output = {
        "allowed": True,
        "modified_input": tool_input,
        "message": "Validation passed"
    }

print(json.dumps(output))
"""

    # Hook 2: Security checker
    security_hook = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
command = tool_input.get("command", "")

# Check for potentially dangerous commands
dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "eval"]
is_dangerous = any(pattern in command.lower() for pattern in dangerous_patterns)

if is_dangerous:
    output = {
        "allowed": False,
        "message": f"Potentially dangerous command detected: {command}"
    }
else:
    output = {
        "allowed": True,
        "modified_input": tool_input,
        "message": "Security check passed"
    }

print(json.dumps(output))
"""

    # Hook 3: Command formatter
    formatter_hook = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
command = tool_input.get("command", "")

# Add timeout and safety flags
formatted_command = f"timeout 30s {command}"
tool_input["command"] = formatted_command
tool_input["formatted"] = True

output = {
    "allowed": True,
    "modified_input": tool_input,
    "message": f"Command formatted with timeout"
}

print(json.dumps(output))
"""

    # Hook 4: Data processor (for data parallel demo)
    data_processor_hook = """#!/usr/bin/env python3
import json
import sys
import time

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
data = tool_input.get("data", [])
chunk_id = tool_input.get("chunk_id", 0)

# Simulate some processing time
time.sleep(0.1)

# Process each item in the chunk (multiply by 2)
processed_data = [item * 2 if isinstance(item, (int, float)) else f"processed_{item}" for item in data]

output = {
    "allowed": True,
    "modified_input": {"data": processed_data},
    "chunk_id": chunk_id,
    "message": f"Processed chunk {chunk_id} with {len(processed_data)} items"
}

print(json.dumps(output))
"""

    # Pipeline hooks
    pipeline_stage1 = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
value = tool_input.get("value", 0)

# Stage 1: Add 10
result = value + 10

output = {
    "allowed": True,
    "modified_input": {"value": result},
    "message": f"Stage 1: Added 10, result = {result}"
}

print(json.dumps(output))
"""

    pipeline_stage2 = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
value = tool_input.get("value", 0)

# Stage 2: Multiply by 2
result = value * 2

output = {
    "allowed": True,
    "modified_input": {"value": result},
    "message": f"Stage 2: Multiplied by 2, result = {result}"
}

print(json.dumps(output))
"""

    pipeline_stage3 = """#!/usr/bin/env python3
import json
import sys

input_data = json.loads(sys.stdin.read())
tool_input = input_data.get("tool_input", {})
value = tool_input.get("value", 0)

# Stage 3: Subtract 5
result = value - 5

output = {
    "allowed": True,
    "modified_input": {"value": result},
    "message": f"Stage 3: Subtracted 5, final result = {result}"
}

print(json.dumps(output))
"""

    # Create temporary files
    hook_scripts = [
        ("validator", validator_hook),
        ("security", security_hook),
        ("formatter", formatter_hook),
        ("data_processor", data_processor_hook),
        ("pipeline_stage1", pipeline_stage1),
        ("pipeline_stage2", pipeline_stage2),
        ("pipeline_stage3", pipeline_stage3),
    ]

    for name, script_content in hook_scripts:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix=f"{name}_"
        ) as f:
            f.write(script_content)
            f.flush()
            hooks.append(Path(f.name))

    return hooks


async def demo_core_parallel_processor():
    """Demonstrate the core parallel processor."""

    print("\n" + "=" * 60)
    print("CORE PARALLEL PROCESSOR DEMO")
    print("=" * 60)

    # Create sample hooks
    hooks = create_sample_hooks()

    try:
        # Create processor
        processor = ParallelProcessor(max_workers=3, default_timeout=10.0)

        # Create processing tasks
        tasks = [
            ProcessingTask(
                task_id="validate_input",
                hook_path=hooks[0],  # validator
                input_data={
                    "tool_name": "Bash",
                    "tool_input": {"command": "ls -la", "description": "List files"},
                },
                priority=ProcessingPriority.HIGH,
            ),
            ProcessingTask(
                task_id="security_check",
                hook_path=hooks[1],  # security
                input_data={
                    "tool_name": "Bash",
                    "tool_input": {"command": "ls -la", "description": "List files"},
                },
                priority=ProcessingPriority.NORMAL,
            ),
            ProcessingTask(
                task_id="format_command",
                hook_path=hooks[2],  # formatter
                input_data={
                    "tool_name": "Bash",
                    "tool_input": {"command": "ls -la", "description": "List files"},
                },
                priority=ProcessingPriority.LOW,
                dependencies={"validate_input", "security_check"},
            ),
        ]

        print(f"Created {len(tasks)} processing tasks")

        # Test different processing modes
        modes = [
            ProcessingMode.SEQUENTIAL,
            ProcessingMode.PARALLEL,
            ProcessingMode.PIPELINE,
        ]

        for mode in modes:
            print(f"\n--- Testing {mode.value.upper()} mode ---")

            results = await processor.run(tasks, mode)

            print(f"Completed {len(results)} tasks")
            for result in results:
                status = "✓" if result.success else "✗"
                print(f"  {status} {result.task_id}: {result.duration:.2f}s")
                if result.success:
                    message = result.execution_result.output.get(
                        "message", "No message"
                    )
                    print(f"    Message: {message}")

        # Get statistics
        stats = processor.get_stats()
        print("\nProcessing Statistics:")
        print(f"  Total tasks: {stats.total_tasks}")
        print(f"  Completed: {stats.completed_tasks}")
        print(f"  Failed: {stats.failed_tasks}")
        print(
            f"  Success rate: {stats.completed_tasks / max(stats.total_tasks, 1) * 100:.1f}%"
        )
        print(f"  Total duration: {stats.total_duration:.2f}s")

    finally:
        # Cleanup temp files
        for hook in hooks:
            hook.unlink(missing_ok=True)


async def demo_multi_hook_processor():
    """Demonstrate multi-hook parallel processing."""

    print("\n" + "=" * 60)
    print("MULTI-HOOK PROCESSOR DEMO")
    print("=" * 60)

    hooks = create_sample_hooks()

    try:
        # Create multi-hook processor with first 3 hooks
        multi_processor = MultiHookProcessor(
            hook_paths=hooks[:3],  # validator, security, formatter
            max_workers=3,
        )

        # Input data
        input_data = HookInput(
            tool_name="Bash",
            tool_input={
                "command": "echo 'Hello World'",
                "description": "Simple echo command",
            },
        )

        print("Executing multiple hooks in parallel...")

        result = await multi_processor.execute(input_data)

        print("Multi-hook execution result:")
        print(f"  Allowed: {result.allowed}")
        print(f"  Message: {result.message}")
        print(f"  Modified input: {result.modified_input}")
        print(f"  Metadata: {result.metadata}")

        # Get processing stats
        stats = multi_processor.get_processing_stats()
        print(f"\nProcessing stats: {stats}")

    finally:
        # Cleanup
        for hook in hooks:
            hook.unlink(missing_ok=True)


async def demo_data_parallel_processing():
    """Demonstrate data parallel processing."""

    print("\n" + "=" * 60)
    print("DATA PARALLEL PROCESSING DEMO")
    print("=" * 60)

    hooks = create_sample_hooks()

    try:
        # Create data parallel processor
        data_processor = DataParallelHook(
            chunk_size=5,  # Process 5 items at a time
            max_workers=3,
            processor_hook_path=hooks[3],  # data_processor hook
        )

        # Large dataset to process
        large_dataset = list(range(1, 21))  # Numbers 1-20

        input_data = HookInput(
            tool_name="DataProcessor", tool_input={"data": large_dataset}
        )

        print(f"Processing {len(large_dataset)} items in parallel chunks...")

        result = await data_processor.execute(input_data)

        print("Data parallel processing result:")
        print(f"  Allowed: {result.allowed}")
        print(f"  Original data: {large_dataset}")
        print(f"  Processed data: {result.modified_input['data']}")
        print(f"  Message: {result.message}")
        print(f"  Metadata: {result.metadata}")

    finally:
        # Cleanup
        for hook in hooks:
            hook.unlink(missing_ok=True)


async def demo_pipeline_processing():
    """Demonstrate pipeline processing."""

    print("\n" + "=" * 60)
    print("PIPELINE PROCESSING DEMO")
    print("=" * 60)

    hooks = create_sample_hooks()

    try:
        # Create pipeline processor with stage hooks
        pipeline_processor = PipelineHook(
            hook_paths=hooks[4:7]  # pipeline_stage1, stage2, stage3
        )

        # Input data with initial value
        input_data = HookInput(tool_name="PipelineProcessor", tool_input={"value": 5})

        print("Processing through pipeline stages...")
        print("Pipeline: value -> (+10) -> (*2) -> (-5)")
        print(f"Initial value: {input_data.tool_input['value']}")

        result = await pipeline_processor.execute(input_data)

        print("\nPipeline processing result:")
        print(f"  Allowed: {result.allowed}")
        print(f"  Final value: {result.modified_input['value']}")
        print(f"  Expected: {((5 + 10) * 2) - 5} = 25")
        print(f"  Message: {result.message}")
        print(f"  Metadata: {result.metadata}")

    finally:
        # Cleanup
        for hook in hooks:
            hook.unlink(missing_ok=True)


async def demo_workflow_visualization():
    """Demonstrate workflow visualization with Mermaid."""

    print("\n" + "=" * 60)
    print("WORKFLOW VISUALIZATION DEMO")
    print("=" * 60)

    # Create sample tasks for visualization
    tasks = [
        ProcessingTask(
            "input_validation", "/path/validator.py", {}, ProcessingPriority.HIGH
        ),
        ProcessingTask(
            "security_check",
            "/path/security.py",
            {},
            ProcessingPriority.NORMAL,
            dependencies={"input_validation"},
        ),
        ProcessingTask(
            "data_transform",
            "/path/transform.py",
            {},
            ProcessingPriority.NORMAL,
            dependencies={"input_validation"},
        ),
        ProcessingTask(
            "final_processing",
            "/path/final.py",
            {},
            ProcessingPriority.LOW,
            dependencies={"security_check", "data_transform"},
        ),
    ]

    # Create sample results
    import time

    from quickhooks.core.processor import ProcessingResult
    from quickhooks.executor import ExecutionResult

    base_time = time.time()
    results = [
        ProcessingResult(
            "input_validation",
            ExecutionResult(0, {"allowed": True}, "", "", 1.0),
            True,
            base_time,
            base_time + 1.0,
        ),
        ProcessingResult(
            "security_check",
            ExecutionResult(0, {"allowed": True}, "", "", 1.5),
            True,
            base_time + 1.0,
            base_time + 2.5,
        ),
        ProcessingResult(
            "data_transform",
            ExecutionResult(0, {"allowed": True}, "", "", 2.0),
            True,
            base_time + 1.0,
            base_time + 3.0,
        ),
        ProcessingResult(
            "final_processing",
            ExecutionResult(1, {"allowed": False}, "", "Error", 0.5),
            False,
            base_time + 3.0,
            base_time + 3.5,
        ),
    ]

    # Create visualization generator
    visualizer = MermaidWorkflowGenerator("workflow_diagrams")

    print("Generating workflow diagrams...")

    # Generate dependency graph
    dep_graph = visualizer.generate_task_dependency_graph(tasks)
    dep_path = visualizer.save_diagram(dep_graph, "demo_dependencies")
    print(f"  Dependency graph: {dep_path}")

    # Generate processing flow diagrams
    for mode in ProcessingMode:
        flow_graph = visualizer.generate_processing_flow(mode, tasks)
        flow_path = visualizer.save_diagram(flow_graph, f"demo_{mode.value}_flow")
        print(f"  {mode.value.title()} flow: {flow_path}")

    # Generate execution timeline
    timeline = visualizer.generate_execution_timeline(results)
    timeline_path = visualizer.save_diagram(timeline, "demo_timeline")
    print(f"  Execution timeline: {timeline_path}")

    # Generate performance summary
    perf_summary = visualizer.generate_performance_summary(results)
    perf_path = visualizer.save_diagram(perf_summary, "demo_performance")
    print(f"  Performance summary: {perf_path}")

    # Generate complete workflow report
    report_files = visualizer.generate_complete_workflow_report(
        tasks, results, ProcessingMode.PARALLEL, "quickhooks_demo"
    )

    print("\nComplete workflow report generated:")
    for diagram_type, file_path in report_files.items():
        print(f"  {diagram_type}: {file_path}")

    # Show sample diagram content
    print("\nSample dependency graph:")
    print("-" * 40)
    print(dep_graph[:500] + "..." if len(dep_graph) > 500 else dep_graph)


async def main():
    """Run all demos."""

    print("QuickHooks Parallel Processing Framework Demo")
    print("=" * 60)

    try:
        # Run all demos
        await demo_core_parallel_processor()
        await demo_multi_hook_processor()
        await demo_data_parallel_processing()
        await demo_pipeline_processing()
        await demo_workflow_visualization()

        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nKey features demonstrated:")
        print("✓ Core parallel processor with multiple execution modes")
        print("✓ Multi-hook parallel execution")
        print("✓ Data parallel processing with chunking")
        print("✓ Pipeline processing with dependencies")
        print("✓ Workflow visualization with Mermaid diagrams")
        print("✓ Comprehensive error handling and statistics")

        print("\nGenerated files:")
        print("- Workflow diagrams in: workflow_diagrams/")
        print("- Example hook scripts (temporary, cleaned up)")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
