"""Tests for the base hook class.

This module tests the abstract base hook class and its lifecycle methods.
Following TDD principles - tests are written first.
"""

import asyncio

import pytest

from quickhooks.hooks.base import BaseHook
from quickhooks.models import (
    ExecutionContext,
    HookInput,
    HookOutput,
    HookResult,
    HookStatus,
)


# Test hook implementations for testing
class TestHook(BaseHook):
    """Simple test hook implementation."""

    async def execute(
        self, input_data: HookInput, context: ExecutionContext
    ) -> HookOutput:
        """Execute the test hook."""
        return HookOutput(
            status=HookStatus.SUCCESS,
            data={
                "message": "Test hook executed",
                "input_event": input_data.event_type,
            },
            message="Test hook completed successfully",
        )


class FailingTestHook(BaseHook):
    """Test hook that always fails."""

    async def execute(
        self, input_data: HookInput, context: ExecutionContext
    ) -> HookOutput:
        """Execute the failing test hook."""
        raise ValueError("Test hook failure")


class SlowTestHook(BaseHook):
    """Test hook that takes time to execute."""

    async def execute(
        self, input_data: HookInput, context: ExecutionContext
    ) -> HookOutput:
        """Execute the slow test hook."""
        await asyncio.sleep(0.1)
        return HookOutput(
            status=HookStatus.SUCCESS,
            data={"delay": 0.1},
            message="Slow hook completed",
        )


class TestBaseHook:
    """Tests for the BaseHook abstract class."""

    def test_base_hook_cannot_be_instantiated(self):
        """Test that BaseHook cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseHook()

    def test_hook_name_property(self):
        """Test hook name property defaults to class name."""
        hook = TestHook()
        assert hook.name == "TestHook"

    def test_hook_custom_name(self):
        """Test hook with custom name."""
        hook = TestHook(name="CustomTestHook")
        assert hook.name == "CustomTestHook"

    def test_hook_description_property(self):
        """Test hook description property."""
        hook = TestHook()
        assert hook.description == "Simple test hook implementation."

    def test_hook_custom_description(self):
        """Test hook with custom description."""
        custom_desc = "A custom test hook for testing purposes"
        hook = TestHook(description=custom_desc)
        assert hook.description == custom_desc

    def test_hook_version_default(self):
        """Test hook version defaults to 1.0.0."""
        hook = TestHook()
        assert hook.version == "1.0.0"

    def test_hook_custom_version(self):
        """Test hook with custom version."""
        hook = TestHook(version="2.1.0")
        assert hook.version == "2.1.0"

    def test_hook_enabled_default(self):
        """Test hook is enabled by default."""
        hook = TestHook()
        assert hook.enabled is True

    def test_hook_disabled(self):
        """Test hook can be disabled."""
        hook = TestHook(enabled=False)
        assert hook.enabled is False

    def test_hook_string_representation(self):
        """Test hook string representation."""
        hook = TestHook()
        assert str(hook) == "TestHook v1.0.0"

    def test_hook_repr(self):
        """Test hook repr."""
        hook = TestHook(name="MyHook", version="1.2.3")
        expected = "TestHook(name='MyHook', version='1.2.3', enabled=True)"
        assert repr(hook) == expected


class TestBaseHookExecution:
    """Tests for BaseHook execution methods."""

    @pytest.mark.asyncio
    async def test_successful_hook_execution(self):
        """Test successful hook execution."""
        hook = TestHook()

        input_data = HookInput(event_type="test_event", data={"test": "data"})

        context = ExecutionContext(hook_id="test-hook-123", execution_id="exec-456")

        result = await hook.run(input_data, context)

        assert isinstance(result, HookResult)
        assert result.hook_id == "test-hook-123"
        assert result.status == HookStatus.SUCCESS
        assert result.input_data == input_data
        assert result.output_data is not None
        assert result.output_data.status == HookStatus.SUCCESS
        assert result.output_data.data["message"] == "Test hook executed"
        assert result.execution_context == context

    @pytest.mark.asyncio
    async def test_hook_execution_with_failure(self):
        """Test hook execution when execute method raises exception."""
        hook = FailingTestHook()

        input_data = HookInput(event_type="failing_event", data={"will": "fail"})

        context = ExecutionContext(hook_id="failing-hook-123", execution_id="exec-789")

        result = await hook.run(input_data, context)

        assert isinstance(result, HookResult)
        assert result.status == HookStatus.FAILED
        assert result.output_data is not None
        assert result.output_data.status == HookStatus.FAILED
        assert result.output_data.error is not None
        assert result.output_data.error.code == "EXECUTION_ERROR"
        assert "Test hook failure" in result.output_data.error.message

    @pytest.mark.asyncio
    async def test_hook_execution_timing(self):
        """Test that hook execution time is measured."""
        hook = SlowTestHook()

        input_data = HookInput(event_type="slow_event", data={"speed": "slow"})

        context = ExecutionContext(hook_id="slow-hook-123", execution_id="exec-slow")

        result = await hook.run(input_data, context)

        assert result.output_data.execution_time is not None
        assert (
            result.output_data.execution_time >= 0.1
        )  # Should take at least 0.1 seconds

    @pytest.mark.asyncio
    async def test_disabled_hook_execution(self):
        """Test that disabled hooks don't execute."""
        hook = TestHook(enabled=False)

        input_data = HookInput(event_type="test_event", data={"test": "data"})

        context = ExecutionContext(
            hook_id="disabled-hook-123", execution_id="exec-disabled"
        )

        result = await hook.run(input_data, context)

        assert result.status == HookStatus.CANCELLED
        assert result.output_data is not None
        assert result.output_data.status == HookStatus.CANCELLED
        assert "Hook is disabled" in result.output_data.message

    @pytest.mark.asyncio
    async def test_hook_validation_methods(self):
        """Test hook validation methods."""
        hook = TestHook()

        # Test valid input
        valid_input = HookInput(event_type="valid_event", data={"valid": True})

        is_valid = await hook.validate_input(valid_input)
        assert is_valid is True

        # Test that validate_input can be overridden by subclasses
        class ValidatingHook(BaseHook):
            async def validate_input(self, input_data: HookInput) -> bool:
                return input_data.event_type.startswith("valid_")

            async def execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> HookOutput:
                return HookOutput(status=HookStatus.SUCCESS, data={})

        validating_hook = ValidatingHook()

        valid_result = await validating_hook.validate_input(valid_input)
        assert valid_result is True

        invalid_input = HookInput(event_type="invalid_event", data={"valid": False})

        invalid_result = await validating_hook.validate_input(invalid_input)
        assert invalid_result is False

    @pytest.mark.asyncio
    async def test_hook_lifecycle_hooks(self):
        """Test hook lifecycle hooks (before_execute, after_execute)."""
        before_execute_called = False
        after_execute_called = False

        class LifecycleHook(BaseHook):
            async def before_execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> None:
                nonlocal before_execute_called
                before_execute_called = True

            async def execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> HookOutput:
                return HookOutput(status=HookStatus.SUCCESS, data={})

            async def after_execute(
                self,
                input_data: HookInput,
                context: ExecutionContext,
                result: HookOutput,
            ) -> None:
                nonlocal after_execute_called
                after_execute_called = True

        hook = LifecycleHook()

        input_data = HookInput(event_type="lifecycle_test", data={})

        context = ExecutionContext(
            hook_id="lifecycle-hook-123", execution_id="exec-lifecycle"
        )

        await hook.run(input_data, context)

        assert before_execute_called is True
        assert after_execute_called is True

    @pytest.mark.asyncio
    async def test_hook_input_validation_in_run(self):
        """Test that input validation is called during run."""

        class StrictValidationHook(BaseHook):
            async def validate_input(self, input_data: HookInput) -> bool:
                return input_data.event_type == "allowed_event"

            async def execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> HookOutput:
                return HookOutput(status=HookStatus.SUCCESS, data={})

        hook = StrictValidationHook()

        # Test with invalid input
        invalid_input = HookInput(event_type="forbidden_event", data={})

        context = ExecutionContext(
            hook_id="strict-hook-123", execution_id="exec-strict"
        )

        result = await hook.run(invalid_input, context)

        assert result.status == HookStatus.FAILED
        assert result.output_data.status == HookStatus.FAILED
        assert result.output_data.error is not None
        assert result.output_data.error.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_hook_exception_handling(self):
        """Test comprehensive exception handling in hooks."""

        class ExceptionHook(BaseHook):
            async def execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> HookOutput:
                if input_data.event_type == "value_error":
                    raise ValueError("Value error occurred")
                elif input_data.event_type == "type_error":
                    raise TypeError("Type error occurred")
                elif input_data.event_type == "runtime_error":
                    raise RuntimeError("Runtime error occurred")
                else:
                    return HookOutput(status=HookStatus.SUCCESS, data={})

        hook = ExceptionHook()
        context = ExecutionContext(
            hook_id="exception-hook", execution_id="exec-exception"
        )

        # Test ValueError
        value_error_input = HookInput(event_type="value_error", data={})
        result = await hook.run(value_error_input, context)
        assert result.status == HookStatus.FAILED
        assert "Value error occurred" in result.output_data.error.message

        # Test TypeError
        type_error_input = HookInput(event_type="type_error", data={})
        result = await hook.run(type_error_input, context)
        assert result.status == HookStatus.FAILED
        assert "Type error occurred" in result.output_data.error.message

        # Test RuntimeError
        runtime_error_input = HookInput(event_type="runtime_error", data={})
        result = await hook.run(runtime_error_input, context)
        assert result.status == HookStatus.FAILED
        assert "Runtime error occurred" in result.output_data.error.message


class TestHookMetadata:
    """Tests for hook metadata and configuration."""

    def test_hook_metadata_collection(self):
        """Test hook metadata collection."""
        hook = TestHook(
            name="MetadataHook", description="Hook with metadata", version="2.0.0"
        )

        metadata = hook.get_metadata()

        assert metadata["name"] == "MetadataHook"
        assert metadata["description"] == "Hook with metadata"
        assert metadata["version"] == "2.0.0"
        assert metadata["enabled"] is True
        assert "class_name" in metadata
        assert metadata["class_name"] == "TestHook"

    def test_hook_config_validation(self):
        """Test hook configuration validation."""
        # Test valid configuration
        config = {
            "name": "ValidHook",
            "version": "1.0.0",
            "enabled": True,
            "description": "A valid hook configuration",
        }

        hook = TestHook(**config)
        assert hook.name == "ValidHook"
        assert hook.version == "1.0.0"
        assert hook.enabled is True
        assert hook.description == "A valid hook configuration"


class TestHookConcurrency:
    """Tests for hook concurrency and async behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_hook_execution(self):
        """Test that multiple hooks can execute concurrently."""
        hook1 = SlowTestHook(name="Hook1")
        hook2 = SlowTestHook(name="Hook2")
        hook3 = SlowTestHook(name="Hook3")

        input_data = HookInput(event_type="concurrent_test", data={})

        contexts = [
            ExecutionContext(hook_id=f"concurrent-{i}", execution_id=f"exec-{i}")
            for i in range(3)
        ]

        # Execute all hooks concurrently
        tasks = [
            hook1.run(input_data, contexts[0]),
            hook2.run(input_data, contexts[1]),
            hook3.run(input_data, contexts[2]),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result.status == HookStatus.SUCCESS for result in results)

        # Each should have taken around 0.1 seconds, but total time should be much less than 0.3 seconds
        # (This is more of a conceptual test - actual timing depends on system)
        assert all(result.output_data.execution_time >= 0.1 for result in results)

    @pytest.mark.asyncio
    async def test_hook_cancellation(self):
        """Test hook execution cancellation."""

        class CancellableHook(BaseHook):
            async def execute(
                self, input_data: HookInput, context: ExecutionContext
            ) -> HookOutput:
                # Simulate long-running operation that can be cancelled
                for _i in range(100):
                    await asyncio.sleep(0.01)
                    # This would be cancelled before completion
                return HookOutput(status=HookStatus.SUCCESS, data={"completed": True})

        hook = CancellableHook()
        input_data = HookInput(event_type="cancellable_test", data={})
        context = ExecutionContext(
            hook_id="cancellable-hook", execution_id="exec-cancel"
        )

        # Start the hook execution
        task = asyncio.create_task(hook.run(input_data, context))

        # Cancel after a short delay
        await asyncio.sleep(0.05)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            # This is expected
            pass

        # The task should be cancelled
        assert task.cancelled()
