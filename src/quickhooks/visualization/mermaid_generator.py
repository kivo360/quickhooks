"""Mermaid workflow visualization for QuickHooks framework.

This module generates Mermaid diagrams to visualize hook execution workflows,
dependencies, and processing pipelines.
"""

from datetime import datetime
from pathlib import Path

from mermaid import Mermaid
from mermaid.graph import Graph

from quickhooks.core.processor import ProcessingMode, ProcessingResult, ProcessingTask


class MermaidWorkflowGenerator:
    """Generates Mermaid diagrams for QuickHooks workflows."""

    def __init__(self, output_dir: str | Path = "workflow_diagrams"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_task_dependency_graph(
        self, tasks: list[ProcessingTask], title: str = "Task Dependencies"
    ) -> str:
        """Generate a dependency graph showing task relationships."""

        graph = Graph(title, "flowchart TD")

        # Add nodes for each task
        for task in tasks:
            node_id = self._sanitize_id(task.task_id)
            label = f"{task.task_id}\\n[{task.priority.value}]"

            # Style nodes based on priority
            if task.priority.value == "critical":
                graph.add_node(node_id, label, shape="diamond", style="fill:#ff6b6b")
            elif task.priority.value == "high":
                graph.add_node(node_id, label, shape="rect", style="fill:#ffa726")
            else:
                graph.add_node(node_id, label, shape="rect", style="fill:#66bb6a")

        # Add dependency edges
        for task in tasks:
            task_node = self._sanitize_id(task.task_id)
            for dep_id in task.dependencies:
                dep_node = self._sanitize_id(dep_id)
                graph.add_edge(dep_node, task_node, "depends")

        return graph.render()

    def generate_execution_timeline(
        self, results: list[ProcessingResult], title: str = "Execution Timeline"
    ) -> str:
        """Generate a timeline showing task execution order and duration."""

        graph = Graph(title, "gantt")
        graph.config["dateFormat"] = "X"
        graph.config["axisFormat"] = "%S"

        # Sort results by start time
        sorted_results = sorted(results, key=lambda r: r.start_time)

        if not sorted_results:
            return (
                "gantt\n    title Empty Timeline\n    dateFormat X\n    axisFormat %S"
            )

        base_time = sorted_results[0].start_time

        gantt_content = [
            "gantt",
            f"    title {title}",
            "    dateFormat X",
            "    axisFormat %S",
        ]

        for result in sorted_results:
            start_offset = int((result.start_time - base_time) * 1000)
            end_offset = int((result.end_time - base_time) * 1000)

            status_marker = "done" if result.success else "crit"
            task_name = self._sanitize_task_name(result.task_id)

            gantt_content.append(
                f"    {task_name} :{status_marker}, {start_offset}, {end_offset}"
            )

        return "\n".join(gantt_content)

    def generate_processing_flow(
        self,
        mode: ProcessingMode,
        tasks: list[ProcessingTask],
        title: str | None = None,
    ) -> str:
        """Generate a flow diagram showing processing mode execution."""

        if title is None:
            title = f"{mode.value.title()} Processing Flow"

        if mode == ProcessingMode.SEQUENTIAL:
            return self._generate_sequential_flow(tasks, title)
        if mode == ProcessingMode.PARALLEL:
            return self._generate_parallel_flow(tasks, title)
        if mode == ProcessingMode.PIPELINE:
            return self._generate_pipeline_flow(tasks, title)
        if mode == ProcessingMode.BATCH:
            return self._generate_batch_flow(tasks, title)
        msg = f"Unknown processing mode: {mode}"
        raise ValueError(msg)

    def _generate_sequential_flow(self, tasks: list[ProcessingTask], title: str) -> str:
        """Generate sequential processing flow."""

        graph = Graph(title, "flowchart TD")

        # Add start node
        graph.add_node("start", "Start", shape="circle", style="fill:#4caf50")

        prev_node = "start"
        for i, task in enumerate(tasks):
            node_id = self._sanitize_id(f"task_{i}")
            label = task.task_id

            graph.add_node(node_id, label, shape="rect")
            graph.add_edge(prev_node, node_id, "")
            prev_node = node_id

        # Add end node
        graph.add_node("end", "End", shape="circle", style="fill:#f44336")
        graph.add_edge(prev_node, "end", "")

        return graph.render()

    def _generate_parallel_flow(self, tasks: list[ProcessingTask], title: str) -> str:
        """Generate parallel processing flow."""

        graph = Graph(title, "flowchart TD")

        # Add start node
        graph.add_node("start", "Start", shape="circle", style="fill:#4caf50")

        # Add fork node
        graph.add_node("fork", "Fork", shape="diamond", style="fill:#2196f3")
        graph.add_edge("start", "fork", "")

        # Add parallel tasks
        task_nodes = []
        for i, task in enumerate(tasks):
            node_id = self._sanitize_id(f"task_{i}")
            label = task.task_id

            graph.add_node(node_id, label, shape="rect")
            graph.add_edge("fork", node_id, "")
            task_nodes.append(node_id)

        # Add join node
        graph.add_node("join", "Join", shape="diamond", style="fill:#2196f3")
        for node_id in task_nodes:
            graph.add_edge(node_id, "join", "")

        # Add end node
        graph.add_node("end", "End", shape="circle", style="fill:#f44336")
        graph.add_edge("join", "end", "")

        return graph.render()

    def _generate_pipeline_flow(self, tasks: list[ProcessingTask], title: str) -> str:
        """Generate pipeline processing flow."""

        # Sort tasks by dependencies for pipeline order
        ordered_tasks = self._topological_sort(tasks)

        graph = Graph(title, "flowchart LR")

        # Add start node
        graph.add_node("start", "Start", shape="circle", style="fill:#4caf50")

        prev_node = "start"
        for i, task in enumerate(ordered_tasks):
            node_id = self._sanitize_id(f"stage_{i}")
            label = f"Stage {i}\\n{task.task_id}"

            graph.add_node(node_id, label, shape="rect", style="fill:#ff9800")
            graph.add_edge(prev_node, node_id, f"data_{i}")
            prev_node = node_id

        # Add end node
        graph.add_node("end", "End", shape="circle", style="fill:#f44336")
        graph.add_edge(prev_node, "end", "result")

        return graph.render()

    def _generate_batch_flow(self, tasks: list[ProcessingTask], title: str) -> str:
        """Generate batch processing flow."""

        graph = Graph(title, "flowchart TD")

        # Group tasks into batches (assume batch size of 4 for visualization)
        batch_size = 4
        batches = [tasks[i : i + batch_size] for i in range(0, len(tasks), batch_size)]

        # Add start node
        graph.add_node("start", "Start", shape="circle", style="fill:#4caf50")

        prev_node = "start"
        for batch_idx, batch in enumerate(batches):
            # Add batch node
            batch_node = self._sanitize_id(f"batch_{batch_idx}")
            batch_label = f"Batch {batch_idx + 1}\\n({len(batch)} tasks)"

            graph.add_node(batch_node, batch_label, shape="rect", style="fill:#9c27b0")
            graph.add_edge(prev_node, batch_node, "")

            # Add tasks in batch as subgraph
            for task_idx, task in enumerate(batch):
                task_node = self._sanitize_id(f"b{batch_idx}_t{task_idx}")
                graph.add_node(task_node, task.task_id, shape="rect")
                graph.add_edge(batch_node, task_node, "")

            prev_node = batch_node

        # Add end node
        graph.add_node("end", "End", shape="circle", style="fill:#f44336")
        graph.add_edge(prev_node, "end", "")

        return graph.render()

    def generate_performance_summary(
        self, results: list[ProcessingResult], title: str = "Performance Summary"
    ) -> str:
        """Generate a performance summary chart."""

        if not results:
            return "graph LR\n    A[No Results] --> B[Empty Summary]"

        # Calculate statistics
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = total_tasks - successful_tasks
        sum(r.duration for r in results) / total_tasks

        graph = Graph(title, "pie")
        graph.config["showData"] = True

        pie_content = [
            "pie title Performance Summary",
            f'    "Successful" : {successful_tasks}',
            f'    "Failed" : {failed_tasks}',
        ]

        return "\n".join(pie_content)

    def save_diagram(
        self, mermaid_code: str, filename: str, format: str = "svg"
    ) -> Path:
        """Save Mermaid diagram to file."""

        # Save mermaid source
        mmd_path = self.output_dir / f"{filename}.mmd"
        with open(mmd_path, "w") as f:
            f.write(mermaid_code)

        # Try to render to specified format (requires mermaid CLI)
        output_path = self.output_dir / f"{filename}.{format}"

        try:
            # Use mermaid-py to render if possible
            mermaid = Mermaid()
            if format == "svg":
                rendered = mermaid.render(mermaid_code)
                with open(output_path, "w") as f:
                    f.write(rendered)
            else:
                # For other formats, just save the source
                output_path = mmd_path

        except Exception:
            output_path = mmd_path

        return output_path

    def generate_complete_workflow_report(
        self,
        tasks: list[ProcessingTask],
        results: list[ProcessingResult],
        mode: ProcessingMode,
        report_name: str = "workflow_report",
    ) -> dict[str, Path]:
        """Generate a complete workflow report with multiple diagrams."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"{report_name}_{timestamp}"
        report_dir.mkdir(exist_ok=True)

        # Update output directory temporarily
        original_dir = self.output_dir
        self.output_dir = report_dir

        try:
            generated_files = {}

            # Generate dependency graph
            if tasks:
                dep_graph = self.generate_task_dependency_graph(tasks)
                path = self.save_diagram(dep_graph, "dependencies")
                generated_files["dependencies"] = path

            # Generate processing flow
            if tasks:
                flow_graph = self.generate_processing_flow(mode, tasks)
                path = self.save_diagram(flow_graph, "processing_flow")
                generated_files["processing_flow"] = path

            # Generate execution timeline
            if results:
                timeline = self.generate_execution_timeline(results)
                path = self.save_diagram(timeline, "timeline")
                generated_files["timeline"] = path

            # Generate performance summary
            if results:
                perf_summary = self.generate_performance_summary(results)
                path = self.save_diagram(perf_summary, "performance")
                generated_files["performance"] = path

            # Generate report index
            self._generate_report_index(report_dir, generated_files)

            return generated_files

        finally:
            # Restore original output directory
            self.output_dir = original_dir

    def _generate_report_index(
        self, report_dir: Path, generated_files: dict[str, Path]
    ) -> None:
        """Generate an HTML index for the report."""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>QuickHooks Workflow Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .diagram {{ margin: 20px 0; }}
        .diagram h2 {{ color: #666; }}
        .mermaid-code {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <h1>QuickHooks Workflow Report</h1>
    <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <h2>Available Diagrams</h2>
    <ul>
"""

        for diagram_type, file_path in generated_files.items():
            relative_path = file_path.name
            html_content += f'        <li><a href="{relative_path}">{diagram_type.replace("_", " ").title()}</a></li>\n'

        html_content += """
    </ul>

    <h2>Diagram Sources</h2>
"""

        # Include mermaid source code for each diagram
        for diagram_type, file_path in generated_files.items():
            mmd_file = file_path.with_suffix(".mmd")
            if mmd_file.exists():
                with open(mmd_file) as f:
                    mermaid_code = f.read()

                html_content += f"""
    <div class="diagram">
        <h3>{diagram_type.replace("_", " ").title()}</h3>
        <div class="mermaid-code">{mermaid_code}</div>
    </div>
"""

        html_content += """
</body>
</html>
"""

        index_path = report_dir / "index.html"
        with open(index_path, "w") as f:
            f.write(html_content)

    def _sanitize_id(self, task_id: str) -> str:
        """Sanitize task ID for use in Mermaid diagrams."""
        # Replace special characters with underscores
        return "".join(c if c.isalnum() else "_" for c in task_id)

    def _sanitize_task_name(self, task_name: str) -> str:
        """Sanitize task name for Gantt charts."""
        # Remove special characters and spaces
        return "".join(c for c in task_name if c.isalnum())

    def _topological_sort(self, tasks: list[ProcessingTask]) -> list[ProcessingTask]:
        """Sort tasks topologically based on dependencies."""
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
