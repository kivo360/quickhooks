import importlib.util
from pathlib import Path

from quickhooks.models import ExecutionContext, HookInput, HookOutput

# Import TestHook from file with hyphen in name using importlib
hook_path = Path(__file__).parent.parent.parent / "hooks" / "test-hook.py"
spec = importlib.util.spec_from_file_location("test_hook", hook_path)
test_hook_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_hook_module)
TestHook = test_hook_module.TestHook


class TestTestHook:
    """Test suite for TestHook."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_hook = TestHook()
        self.context = ExecutionContext()

    def test_test_hook_success(self):
        """Test successful test_hook."""
        # Arrange
        hook_input = HookInput(
            tool_name="TestTool", tool_input={"test": "data"}, context=self.context
        )

        # Act
        result = self.test_hook.process(hook_input)

        # Assert
        assert isinstance(result, HookOutput)
        assert result.allowed is True
        assert result.tool_name == "TestTool"

    def test_test_hook_edge_case(self):
        """Test test_hook edge case."""
        # TODO: Implement edge case test
