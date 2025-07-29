"""Tests for Mermaid workflow visualization."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from quickhooks.core.processor import (
    ProcessingMode,
    ProcessingPriority,
    ProcessingResult,
    ProcessingTask,
)
from quickhooks.executor import ExecutionResult
from quickhooks.visualization.mermaid_generator import MermaidWorkflowGenerator


class TestMermaidWorkflowGenerator:
    """Test cases for MermaidWorkflowGenerator."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def generator(self, temp_output_dir):
        """Create a test generator instance."""
        return MermaidWorkflowGenerator(output_dir=temp_output_dir)

    @pytest.fixture
    def sample_tasks(self):
        """Create sample processing tasks."""
        return [
            ProcessingTask("task1", "/path/hook1.py", {}, ProcessingPriority.HIGH),
            ProcessingTask(
                "task2",
                "/path/hook2.py",
                {},
                ProcessingPriority.NORMAL,
                dependencies={"task1"},
            ),
            ProcessingTask(
                "task3",
                "/path/hook3.py",
                {},
                ProcessingPriority.LOW,
                dependencies={"task1", "task2"},
            ),
            ProcessingTask("task4", "/path/hook4.py", {}, ProcessingPriority.CRITICAL),
        ]

    @pytest.fixture
    def sample_results(self):
        """Create sample processing results."""
        return [
            ProcessingResult(
                "task1",
                ExecutionResult(0, {"allowed": True}, "", "", 1.0),
                True,
                100.0,
                101.0,
            ),
            ProcessingResult(
                "task2",
                ExecutionResult(0, {"allowed": True}, "", "", 1.5),
                True,
                101.5,
                103.0,
            ),
            ProcessingResult(
                "task3",
                ExecutionResult(1, {"allowed": False}, "", "error", 0.5),
                False,
                103.5,
                104.0,
            ),
        ]

    def test_generator_initialization(self, generator, temp_output_dir):
        """Test generator initialization."""
        assert generator.output_dir == temp_output_dir
        assert temp_output_dir.exists()

    def test_generate_task_dependency_graph(self, generator, sample_tasks):
        """Test dependency graph generation."""
        mermaid_code = generator.generate_task_dependency_graph(sample_tasks)

        assert "flowchart TD" in mermaid_code
        assert "task1" in mermaid_code
        assert "task2" in mermaid_code
        assert "task3" in mermaid_code
        assert "task4" in mermaid_code

        # Check for dependency relationships
        assert "task1" in mermaid_code and "task2" in mermaid_code

    def test_generate_execution_timeline(self, generator, sample_results):
        """Test timeline generation."""
        mermaid_code = generator.generate_execution_timeline(sample_results)

        assert "gantt" in mermaid_code
        assert "Execution Timeline" in mermaid_code
        assert "task1" in mermaid_code
        assert "task2" in mermaid_code
        assert "task3" in mermaid_code

        # Check for status markers
        assert "done" in mermaid_code  # For successful tasks
        assert "crit" in mermaid_code  # For failed tasks

    def test_generate_execution_timeline_empty(self, generator):
        """Test timeline generation with empty results."""
        mermaid_code = generator.generate_execution_timeline([])

        assert "gantt" in mermaid_code
        assert "Empty Timeline" in mermaid_code

    def test_generate_sequential_flow(self, generator, sample_tasks):
        """Test sequential flow generation."""
        mermaid_code = generator.generate_processing_flow(
            ProcessingMode.SEQUENTIAL, sample_tasks
        )

        assert "flowchart TD" in mermaid_code
        assert "Sequential Processing Flow" in mermaid_code
        assert "Start" in mermaid_code
        assert "End" in mermaid_code

    def test_generate_parallel_flow(self, generator, sample_tasks):
        """Test parallel flow generation."""
        mermaid_code = generator.generate_processing_flow(
            ProcessingMode.PARALLEL, sample_tasks
        )

        assert "flowchart TD" in mermaid_code
        assert "Parallel Processing Flow" in mermaid_code
        assert "Fork" in mermaid_code
        assert "Join" in mermaid_code

    def test_generate_pipeline_flow(self, generator, sample_tasks):
        """Test pipeline flow generation."""
        mermaid_code = generator.generate_processing_flow(
            ProcessingMode.PIPELINE, sample_tasks
        )

        assert "flowchart LR" in mermaid_code
        assert "Pipeline Processing Flow" in mermaid_code
        assert "Stage" in mermaid_code

    def test_generate_batch_flow(self, generator, sample_tasks):
        """Test batch flow generation."""
        mermaid_code = generator.generate_processing_flow(
            ProcessingMode.BATCH, sample_tasks
        )

        assert "flowchart TD" in mermaid_code
        assert "Batch Processing Flow" in mermaid_code
        assert "Batch" in mermaid_code

    def test_generate_performance_summary(self, generator, sample_results):
        """Test performance summary generation."""
        mermaid_code = generator.generate_performance_summary(sample_results)

        assert "pie title Performance Summary" in mermaid_code
        assert "Successful" in mermaid_code
        assert "Failed" in mermaid_code

    def test_generate_performance_summary_empty(self, generator):
        """Test performance summary with empty results."""
        mermaid_code = generator.generate_performance_summary([])

        assert "graph LR" in mermaid_code
        assert "No Results" in mermaid_code

    def test_save_diagram(self, generator):
        """Test saving diagram to file."""
        mermaid_code = "graph LR\n    A --> B"

        output_path = generator.save_diagram(mermaid_code, "test_diagram")

        assert output_path.exists()
        assert output_path.suffix == ".mmd"

        # Check content
        with open(output_path) as f:
            content = f.read()
        assert content == mermaid_code

    def test_generate_complete_workflow_report(
        self, generator, sample_tasks, sample_results
    ):
        """Test complete workflow report generation."""
        generated_files = generator.generate_complete_workflow_report(
            sample_tasks, sample_results, ProcessingMode.PARALLEL, "test_report"
        )

        assert isinstance(generated_files, dict)
        assert len(generated_files) > 0

        # Check that files were created
        for file_path in generated_files.values():
            assert file_path.exists()

    def test_sanitize_id(self, generator):
        """Test ID sanitization for Mermaid."""
        test_cases = [
            ("normal_id", "normal_id"),
            ("with-dashes", "with_dashes"),
            ("with spaces", "with_spaces"),
            ("with.dots", "with_dots"),
            ("with@symbols!", "with_symbols_"),
        ]

        for input_id, expected in test_cases:
            result = generator._sanitize_id(input_id)
            assert result == expected

    def test_sanitize_task_name(self, generator):
        """Test task name sanitization for Gantt charts."""
        test_cases = [
            ("normal_task", "normaltask"),
            ("with spaces", "withspaces"),
            ("with-dashes", "withdashes"),
            ("with@symbols!", "withsymbols"),
        ]

        for input_name, expected in test_cases:
            result = generator._sanitize_task_name(input_name)
            assert result == expected

    def test_topological_sort(self, generator):
        """Test topological sorting of tasks."""
        tasks = [
            ProcessingTask("C", "/path", {}, dependencies={"A", "B"}),
            ProcessingTask("A", "/path", {}),
            ProcessingTask("B", "/path", {}, dependencies={"A"}),
        ]

        sorted_tasks = generator._topological_sort(tasks)

        # A should come before B, B should come before C
        task_ids = [t.task_id for t in sorted_tasks]
        assert task_ids.index("A") < task_ids.index("B")
        assert task_ids.index("B") < task_ids.index("C")

    def test_generate_report_index(self, generator, temp_output_dir):
        """Test HTML report index generation."""
        test_files = {
            "dependencies": temp_output_dir / "deps.mmd",
            "timeline": temp_output_dir / "timeline.mmd",
        }

        # Create test files
        for file_path in test_files.values():
            file_path.write_text("graph LR\n    A --> B")

        generator._generate_report_index(temp_output_dir, test_files)

        index_path = temp_output_dir / "index.html"
        assert index_path.exists()

        content = index_path.read_text()
        assert "QuickHooks Workflow Report" in content
        assert "dependencies" in content
        assert "timeline" in content

    def test_unknown_processing_mode(self, generator, sample_tasks):
        """Test handling of unknown processing mode."""
        with pytest.raises(ValueError, match="Unknown processing mode"):
            generator.generate_processing_flow("unknown_mode", sample_tasks)

    def test_custom_title(self, generator, sample_tasks):
        """Test custom title in diagrams."""
        custom_title = "My Custom Workflow"

        mermaid_code = generator.generate_processing_flow(
            ProcessingMode.SEQUENTIAL, sample_tasks, title=custom_title
        )

        assert custom_title in mermaid_code

    @patch("quickhooks.visualization.mermaid_generator.Mermaid")
    def test_save_diagram_with_rendering(self, mock_mermaid_class, generator):
        """Test saving diagram with mermaid rendering."""
        mock_mermaid = Mock()
        mock_mermaid.render.return_value = "<svg>test</svg>"
        mock_mermaid_class.return_value = mock_mermaid

        mermaid_code = "graph LR\n    A --> B"
        generator.save_diagram(mermaid_code, "test", format="svg")

        # Should attempt to render
        mock_mermaid.render.assert_called_once_with(mermaid_code)

    @patch("quickhooks.visualization.mermaid_generator.Mermaid")
    def test_save_diagram_render_failure(self, mock_mermaid_class, generator):
        """Test saving diagram when rendering fails."""
        mock_mermaid = Mock()
        mock_mermaid.render.side_effect = Exception("Render failed")
        mock_mermaid_class.return_value = mock_mermaid

        mermaid_code = "graph LR\n    A --> B"
        output_path = generator.save_diagram(mermaid_code, "test", format="svg")

        # Should fall back to saving source
        assert output_path.suffix == ".mmd"
        assert output_path.exists()

    def test_empty_tasks_handling(self, generator):
        """Test handling of empty task lists."""
        # Should not crash with empty tasks
        mermaid_code = generator.generate_task_dependency_graph([])
        assert isinstance(mermaid_code, str)

        mermaid_code = generator.generate_processing_flow(ProcessingMode.PARALLEL, [])
        assert isinstance(mermaid_code, str)

    def test_complex_dependencies(self, generator):
        """Test handling of complex dependency relationships."""
        tasks = [
            ProcessingTask("A", "/path", {}),
            ProcessingTask("B", "/path", {}, dependencies={"A"}),
            ProcessingTask("C", "/path", {}, dependencies={"A"}),
            ProcessingTask("D", "/path", {}, dependencies={"B", "C"}),
            ProcessingTask("E", "/path", {}, dependencies={"D"}),
        ]

        mermaid_code = generator.generate_task_dependency_graph(tasks)

        # Should contain all tasks
        for task in tasks:
            assert task.task_id in mermaid_code

        # Should handle dependencies properly
        assert "flowchart TD" in mermaid_code
