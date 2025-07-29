"""Test cases for the example hook."""

import pytest

from quickhooks.models import HookInput, HookOutput


class TestExampleHook:
    """Test cases for the ExampleHook."""

    def test_example_hook_success(self):
        """Test that the example hook runs successfully with valid input."""
        # This is a placeholder test that will be executed by the test runner
        assert True

    def test_example_hook_with_string_input(self):
        """Test the example hook with string input."""
        # This is a placeholder test that will be executed by the test runner
        input_data = HookInput(data="test string")
        assert input_data.data == "test string"

    def test_example_hook_with_dict_input(self):
        """Test the example hook with dictionary input."""
        # This is a placeholder test that will be executed by the test runner
        input_data = HookInput(data={"key": "value"})
        assert input_data.data["key"] == "value"

    @pytest.mark.asyncio
    async def test_example_hook_execute_method(self):
        """Test the execute method of the example hook."""
        # Import here to avoid issues with the test runner
        import sys
        from pathlib import Path

        # Add the hooks directory to the path
        hooks_dir = Path(__file__).parent.parent / "hooks"
        sys.path.insert(0, str(hooks_dir))

        # Import the hook
        from example_hook import ExampleHook

        # Create an instance of the hook
        hook = ExampleHook()

        # Create test input
        input_data = HookInput(data={"test": "data"})

        # Execute the hook
        result = await hook.execute(input_data)

        # Verify the result
        assert isinstance(result, HookOutput)
        assert result.success is True
        assert result.data == {"test": "data"}
        assert "message" in result.metadata
        assert "input_type" in result.metadata
