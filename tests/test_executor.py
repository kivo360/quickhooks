"""Tests for the HookExecutor class."""

import tempfile
from pathlib import Path

import pytest

from quickhooks.executor import (
    ExecutionError,
    ExecutionResult,
    HookExecutor,
    PreToolUseInput,
)


class TestHookExecutor:
    """Test suite for the HookExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create a HookExecutor instance for testing."""
        return HookExecutor()

    @pytest.fixture
    def test_hook_script(self):
        """Create a temporary test hook script that allows all tool usage."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Simple hook that allows all tool usage
output = {
    "allowed": True,
    "message": "Tool usage approved",
    "tool_name": input_data.get("tool_name", "unknown"),
    "processed": True
}

# Write output to stdout as JSON
print(json.dumps(output))
""")
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def slow_hook_script(self):
        """Create a slow hook script for timeout testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys
import time

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Sleep for 2 seconds to trigger timeout
time.sleep(2)

# This should never be reached in timeout tests
output = {"allowed": True}
print(json.dumps(output))
""")
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def error_hook_script(self):
        """Create a hook script that raises an error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Raise an error to test error handling
raise RuntimeError("Simulated hook error")
""")
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def invalid_json_hook_script(self):
        """Create a hook script that outputs invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input from stdin
input_data = json.loads(sys.stdin.read())

# Output invalid JSON
print("This is not valid JSON")
print("Second line of invalid output")
""")
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, test_hook_script):
        """Test successful hook execution with valid input and output."""
        input_data = PreToolUseInput(
            tool_name="Bash", tool_input={"command": "echo hello"}
        )

        result = await executor.execute(test_hook_script, input_data.model_dump())

        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert result.output["allowed"] is True
        assert result.output["tool_name"] == "Bash"
        assert result.output["processed"] is True
        assert result.stderr == ""
        assert result.duration > 0
        assert "Tool usage approved" in result.output["message"]

    @pytest.mark.asyncio
    async def test_execution_timeout(self, executor, slow_hook_script):
        """Test hook execution timeout handling."""
        input_data = PreToolUseInput(tool_name="SlowTool", tool_input={"delay": 5})

        with pytest.raises(ExecutionError) as exc_info:
            await executor.execute(
                slow_hook_script, input_data.model_dump(), timeout=0.5
            )

        assert "timed out" in str(exc_info.value).lower()
        assert "0.5 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hook_script_error(self, executor, error_hook_script):
        """Test handling of hook script that raises an error."""
        input_data = PreToolUseInput(
            tool_name="ErrorTool", tool_input={"should_fail": True}
        )

        result = await executor.execute(error_hook_script, input_data.model_dump())

        # Script should exit with non-zero code, but executor should handle it gracefully
        assert result.exit_code != 0
        assert result.stderr != ""  # Should contain error information
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_invalid_json_output(self, executor, invalid_json_hook_script):
        """Test handling of hook that outputs invalid JSON."""
        input_data = PreToolUseInput(
            tool_name="InvalidJsonTool", tool_input={"test": True}
        )

        with pytest.raises(ExecutionError) as exc_info:
            await executor.execute(invalid_json_hook_script, input_data.model_dump())

        assert "Invalid JSON output" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_hook_script(self, executor):
        """Test handling of missing hook script file."""
        nonexistent_script = Path("/tmp/nonexistent_hook.py")
        input_data = PreToolUseInput(tool_name="MissingTool", tool_input={"test": True})

        with pytest.raises(FileNotFoundError):
            await executor.execute(nonexistent_script, input_data.model_dump())

    @pytest.mark.asyncio
    async def test_execute_with_context(self, executor, test_hook_script):
        """Test hook execution with additional context data."""
        input_data = PreToolUseInput(
            tool_name="ContextTool", tool_input={"command": "test"}
        )
        context = {
            "user_id": "test_user",
            "session_id": "test_session",
            "environment": "testing",
        }

        result = await executor.execute_with_context(
            test_hook_script, input_data.model_dump(), context=context
        )

        assert result.exit_code == 0
        assert result.output["allowed"] is True
        assert result.duration > 0

    def test_validate_hook_script_valid(self, executor, test_hook_script):
        """Test validation of a valid hook script."""
        assert executor.validate_hook_script(test_hook_script) is True

    def test_validate_hook_script_nonexistent(self, executor):
        """Test validation of a nonexistent hook script."""
        nonexistent_script = Path("/tmp/nonexistent_hook.py")
        assert executor.validate_hook_script(nonexistent_script) is False

    def test_validate_hook_script_not_python(self, executor):
        """Test validation of a non-Python file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is not a Python file")
            f.flush()

            try:
                assert executor.validate_hook_script(Path(f.name)) is False
            finally:
                Path(f.name).unlink(missing_ok=True)

    def test_pre_tool_use_input_model(self):
        """Test the PreToolUseInput Pydantic model."""
        input_data = PreToolUseInput(
            tool_name="TestTool", tool_input={"param1": "value1", "param2": 42}
        )

        assert input_data.tool_name == "TestTool"
        assert input_data.tool_input["param1"] == "value1"
        assert input_data.tool_input["param2"] == 42

        # Test model serialization
        json_data = input_data.model_dump()
        assert json_data["tool_name"] == "TestTool"
        assert json_data["tool_input"]["param1"] == "value1"

    def test_execution_result_dataclass(self):
        """Test the ExecutionResult dataclass."""
        result = ExecutionResult(
            exit_code=0,
            output={"allowed": True},
            stdout="Success output",
            stderr="",
            duration=1.5,
        )

        assert result.exit_code == 0
        assert result.output["allowed"] is True
        assert result.stdout == "Success output"
        assert result.stderr == ""
        assert result.duration == 1.5

    def test_execution_error_exception(self):
        """Test the ExecutionError exception."""
        error_msg = "Test execution error"

        with pytest.raises(ExecutionError) as exc_info:
            raise ExecutionError(error_msg)

        assert str(exc_info.value) == error_msg
        assert isinstance(exc_info.value, Exception)

    @pytest.mark.asyncio
    async def test_custom_timeout(self, executor, slow_hook_script):
        """Test custom timeout configuration."""
        # Test with a longer timeout that should not trigger
        input_data = PreToolUseInput(tool_name="SlowTool", tool_input={"delay": 1})

        # This should timeout since the hook sleeps for 2 seconds
        with pytest.raises(ExecutionError) as exc_info:
            await executor.execute(
                slow_hook_script, input_data.model_dump(), timeout=1.5
            )

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_output_handling(self, executor):
        """Test handling of hook script that produces empty output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

# Read input but produce no output
input_data = json.loads(sys.stdin.read())
# No print statement - empty stdout
""")
            f.flush()

            try:
                input_data = PreToolUseInput(
                    tool_name="EmptyTool", tool_input={"test": True}
                )

                result = await executor.execute(Path(f.name), input_data.model_dump())

                # Should default to allowing tool usage
                assert result.output["allowed"] is True

            finally:
                Path(f.name).unlink(missing_ok=True)


class TestExecutorIntegration:
    """Integration tests for the HookExecutor with realistic scenarios."""

    @pytest.fixture
    def realistic_hook_script(self):
        """Create a realistic hook script that checks tool permissions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""#!/usr/bin/env python3
import json
import sys

def main():
    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        output = {
            "allowed": False,
            "error": "Invalid input JSON",
            "message": "Failed to parse input data"
        }
        print(json.dumps(output))
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Simple permission logic
    dangerous_tools = ["rm", "delete", "format"]

    if any(dangerous in tool_name.lower() for dangerous in dangerous_tools):
        output = {
            "allowed": False,
            "message": f"Tool '{tool_name}' is not permitted",
            "reason": "Potentially dangerous operation"
        }
    else:
        output = {
            "allowed": True,
            "message": f"Tool '{tool_name}' is permitted",
            "metadata": {
                "checked_at": "2023-01-01T00:00:00Z",
                "input_params": list(tool_input.keys())
            }
        }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
""")
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_realistic_hook_allowed_tool(self, realistic_hook_script):
        """Test realistic hook with an allowed tool."""
        executor = HookExecutor()
        input_data = PreToolUseInput(
            tool_name="Bash", tool_input={"command": "ls -la", "cwd": "/tmp"}
        )

        result = await executor.execute(realistic_hook_script, input_data.model_dump())

        assert result.exit_code == 0
        assert result.output["allowed"] is True
        assert "Bash" in result.output["message"]
        assert "metadata" in result.output
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_realistic_hook_denied_tool(self, realistic_hook_script):
        """Test realistic hook with a denied tool."""
        executor = HookExecutor()
        input_data = PreToolUseInput(
            tool_name="rm", tool_input={"path": "/important/file.txt"}
        )

        result = await executor.execute(realistic_hook_script, input_data.model_dump())

        assert result.exit_code == 0  # Script runs successfully
        assert result.output["allowed"] is False
        assert "not permitted" in result.output["message"]
        assert "reason" in result.output
        assert result.duration > 0
