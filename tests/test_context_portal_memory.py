"""Tests for the Context Portal Memory Management hook."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
from pathlib import Path

# Add the hooks directory to the path
hooks_dir = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(hooks_dir))

from context_portal_memory import ContextPortalHook, ContextPortalMemoryManager


class TestContextPortalMemoryManager:
    """Test the Context Portal Memory Manager functionality."""

    def setup_method(self):
        """Set up test database in temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ContextPortalMemoryManager(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_init_database(self):
        """Test database initialization."""
        db_path = Path(self.temp_dir) / ".context-portal" / "project.db"
        assert db_path.exists()

        # Verify tables were created
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ["decisions", "tasks", "patterns", "context_entries"]
        for table in expected_tables:
            assert table in tables

    def test_store_decision(self):
        """Test storing a decision."""
        result = self.manager.store_decision(
            title="Use FastAPI for API",
            description="Need to build REST API",
            decision="Use FastAPI framework",
            rationale="Better performance and modern Python features",
            alternatives="Django REST, Flask",
            tags=["architecture", "api"],
        )

        assert result is True

        # Verify decision was stored
        decisions = self.manager.search_decisions("FastAPI")
        assert len(decisions) == 1
        assert decisions[0]["title"] == "Use FastAPI for API"
        assert "architecture" in decisions[0]["tags"]

    def test_store_task(self):
        """Test storing a task."""
        result = self.manager.store_task(
            title="Implement user authentication",
            description="Add JWT-based auth",
            status="in_progress",
            priority="high",
            context="Security requirement",
        )

        assert result is True

        # Verify task was stored
        import sqlite3

        with sqlite3.connect(self.manager.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE title LIKE ?", ("%authentication%",)
            )
            task = cursor.fetchone()

        assert task is not None
        assert task[3] == "in_progress"  # status column
        assert task[4] == "high"  # priority column

    def test_store_pattern(self):
        """Test storing a code pattern."""
        result = self.manager.store_pattern(
            name="Singleton Pattern",
            description="Ensure single instance",
            code_example="class Singleton: ...",
            use_cases="Configuration, logging",
            category="design_patterns",
        )

        assert result is True

        # Verify pattern was stored
        patterns = self.manager.search_patterns("Singleton")
        assert len(patterns) == 1
        assert patterns[0]["name"] == "Singleton Pattern"
        assert patterns[0]["category"] == "design_patterns"

    def test_store_context_entry(self):
        """Test storing a context entry."""
        result = self.manager.store_context_entry(
            tool_name="Bash",
            command="npm install express",
            context="Setting up Express server",
            result="Installed successfully",
            session_id="test_session",
        )

        assert result is True

        # Verify context entry was stored
        context_entries = self.manager.search_context(tool_name="Bash", query="express")
        assert len(context_entries) == 1
        assert context_entries[0]["command"] == "npm install express"
        assert context_entries[0]["session_id"] == "test_session"

    def test_search_decisions(self):
        """Test searching decisions."""
        # Store multiple decisions
        self.manager.store_decision("Use React", tags=["frontend"])
        self.manager.store_decision("Use Vue", tags=["frontend"])
        self.manager.store_decision("Use PostgreSQL", tags=["database"])

        # Search for frontend decisions
        frontend_decisions = self.manager.search_decisions("React")
        assert len(frontend_decisions) >= 1
        assert any("React" in d["title"] for d in frontend_decisions)

        # Search for database decisions
        db_decisions = self.manager.search_decisions("PostgreSQL")
        assert len(db_decisions) >= 1
        assert any("PostgreSQL" in d["title"] for d in db_decisions)

    def test_search_patterns_by_category(self):
        """Test searching patterns by category."""
        # Store patterns in different categories
        self.manager.store_pattern("Factory", category="design_patterns")
        self.manager.store_pattern("Repository", category="data_patterns")

        # Search by category
        design_patterns = self.manager.search_patterns("", category="design_patterns")
        assert len(design_patterns) >= 1
        assert any("Factory" in p["name"] for p in design_patterns)

        data_patterns = self.manager.search_patterns("", category="data_patterns")
        assert len(data_patterns) >= 1
        assert any("Repository" in p["name"] for p in data_patterns)

    def test_deduplication(self):
        """Test that duplicate entries are handled correctly."""
        # Store same decision twice
        self.manager.store_decision("Test Decision", description="Same content")
        self.manager.store_decision("Test Decision", description="Same content")

        # Should only have one entry
        decisions = self.manager.search_decisions("Test Decision")
        assert len(decisions) == 1


class TestContextPortalHook:
    """Test the Context Portal Hook functionality."""

    def setup_method(self):
        """Set up test hook."""
        self.temp_dir = tempfile.mkdtemp()
        with patch("context_portal_memory.os.getcwd", return_value=self.temp_dir):
            self.hook = ContextPortalHook()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_should_process(self):
        """Test tool filtering logic."""
        assert self.hook.should_process("Bash", {})
        assert self.hook.should_process("Edit", {})
        assert self.hook.should_process("Task", {})
        assert not self.hook.should_process("UnknownTool", {})

    def test_extract_context_info_bash(self):
        """Test context extraction for Bash commands."""
        tool_input = {"command": "git status", "description": "Check repository status"}

        context_info = self.hook.extract_context_info("Bash", tool_input)

        assert context_info["tool"] == "Bash"
        assert context_info["command"] == "git status"
        assert context_info["description"] == "Check repository status"
        assert "timestamp" in context_info
        assert "session" in context_info

    def test_extract_context_info_edit(self):
        """Test context extraction for Edit operations."""
        tool_input = {
            "file_path": "/path/to/file.py",
            "old_string": "old code",
            "new_string": "new code",
        }

        context_info = self.hook.extract_context_info("Edit", tool_input)

        assert context_info["tool"] == "Edit"
        assert context_info["file_path"] == "/path/to/file.py"
        assert context_info["operation"] == "edit"

    def test_detect_decision_context(self):
        """Test decision context detection."""
        # Tool input with decision keywords
        decision_input = {
            "command": "We need to decide on the architecture approach",
            "description": "Choose between microservices and monolith",
        }

        decision_context = self.hook.detect_decision_context(decision_input)

        assert decision_context is not None
        assert decision_context["type"] == "decision"
        assert decision_context["keyword"] in ["decide", "architecture", "approach"]

        # Tool input without decision keywords
        regular_input = {"command": "ls -la", "description": "List files"}

        regular_context = self.hook.detect_decision_context(regular_input)
        assert regular_context is None

    def test_transform_with_context_storage(self):
        """Test that transform stores context correctly."""
        tool_input = {"command": "npm test", "description": "Run tests"}

        # Transform should store context and may enhance with history
        result = self.hook.transform("Bash", tool_input)

        # May return enhanced input or None depending on available context
        if result is not None:
            assert "_context_portal_history" in result or result == tool_input

        # Context should be stored
        context_entries = self.hook.memory_manager.search_context(query="npm test")
        assert len(context_entries) >= 1

    def test_transform_with_decision_detection(self):
        """Test transform with decision detection."""
        tool_input = {
            "command": "We decide to implement the feature using React hooks",
            "description": "Architecture decision for frontend",
        }

        # Transform should detect decision and store it
        self.hook.transform("Task", tool_input)

        # Check that decision was stored
        decisions = self.hook.memory_manager.search_decisions("React hooks")
        assert len(decisions) >= 1
        assert any("decide" in d["tags"] for d in decisions)


class TestHookIntegration:
    """Test the complete hook integration with JSON I/O."""

    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook_script = (
            Path(__file__).parent.parent / "hooks" / "context_portal_memory.py"
        )

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def run_hook(self, input_data: dict) -> dict:
        """Run the actual hook script and return parsed output."""
        # Set working directory to temp dir for database creation
        env = os.environ.copy()
        env["CONTEXT_PORTAL_TEST_DIR"] = self.temp_dir

        process = subprocess.run(
            ["python", str(self.hook_script)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=self.temp_dir,
            env=env,
        )

        if process.returncode != 0:
            pytest.fail(f"Hook script failed: {process.stderr}")

        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {process.stdout}")

    def test_hook_processes_bash_command(self):
        """Test hook processing of Bash command."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status", "description": "Check git status"},
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["tool_name"] == "Bash"
        # Hook may modify input with context enhancement
        assert "modified" in result  # Just check the field exists

    def test_hook_handles_decision_context(self):
        """Test hook handling of decision context."""
        input_data = {
            "tool_name": "Task",
            "tool_input": {
                "description": "Decide on database architecture",
                "prompt": "We need to choose between PostgreSQL and MongoDB",
            },
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["tool_name"] == "Task"
        # Should store decision context but not necessarily modify input

    def test_hook_ignores_unsupported_tools(self):
        """Test hook ignores tools not in its filter list."""
        input_data = {
            "tool_name": "UnsupportedTool",
            "tool_input": {"some_param": "some_value"},
        }

        result = self.run_hook(input_data)

        assert result["allowed"] is True
        assert result["modified"] is False
        assert result["tool_name"] == "UnsupportedTool"

    def test_hook_error_handling(self):
        """Test hook handles errors gracefully."""
        # Invalid JSON input should be handled gracefully by the script
        invalid_input = "invalid json"

        process = subprocess.run(
            ["python", str(self.hook_script)],
            input=invalid_input,
            capture_output=True,
            text=True,
            cwd=self.temp_dir,
        )

        # Should still return valid JSON response
        assert process.returncode == 0
        result = json.loads(process.stdout)
        assert result["allowed"] is True
        assert result["modified"] is False
        assert "error" in result["message"]


@pytest.mark.parametrize(
    "tool_name,tool_input,expected_context",
    [
        (
            "Bash",
            {"command": "pytest tests/"},
            {"tool": "Bash", "command": "pytest tests/"},
        ),
        (
            "Edit",
            {"file_path": "test.py"},
            {"tool": "Edit", "file_path": "test.py", "operation": "edit"},
        ),
        (
            "Write",
            {"file_path": "new.py"},
            {"tool": "Write", "file_path": "new.py", "operation": "write"},
        ),
        (
            "Read",
            {"file_path": "readme.md"},
            {"tool": "Read", "file_path": "readme.md", "operation": "read"},
        ),
        ("Grep", {"pattern": "TODO"}, {"tool": "Grep", "pattern": "TODO"}),
    ],
)
def test_parametrized_context_extraction(tool_name, tool_input, expected_context):
    """Test context extraction for various tool types."""
    temp_dir = tempfile.mkdtemp()
    try:
        with patch("context_portal_memory.os.getcwd", return_value=temp_dir):
            hook = ContextPortalHook()
            context = hook.extract_context_info(tool_name, tool_input)

            for key, value in expected_context.items():
                assert context[key] == value

            # These should always be present
            assert "timestamp" in context
            assert "session" in context
    finally:
        shutil.rmtree(temp_dir)
