"""Tests for core models in quickhooks.

This module tests the core Pydantic models used throughout the framework.
Following TDD principles - tests are written first.
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from quickhooks.models import (
    ExecutionContext,
    HookError,
    HookInput,
    HookMetadata,
    HookOutput,
    HookResult,
    HookStatus,
)


class TestHookInput:
    """Tests for HookInput model."""

    def test_hook_input_minimal(self):
        """Test HookInput with minimal required fields."""
        hook_input = HookInput(
            event_type="file_changed", data={"file_path": "/test/file.py"}
        )

        assert hook_input.event_type == "file_changed"
        assert hook_input.data == {"file_path": "/test/file.py"}
        assert hook_input.timestamp is not None
        assert isinstance(hook_input.timestamp, datetime)
        assert hook_input.context == {}
        assert hook_input.metadata is None

    def test_hook_input_with_context(self):
        """Test HookInput with execution context."""
        context = {"user_id": "123", "session": "abc"}
        hook_input = HookInput(
            event_type="user_action", data={"action": "click"}, context=context
        )

        assert hook_input.context == context

    def test_hook_input_with_metadata(self):
        """Test HookInput with metadata."""
        metadata = HookMetadata(
            source="test_suite", version="1.0.0", tags=["test", "automation"]
        )
        hook_input = HookInput(
            event_type="test_event", data={"test": True}, metadata=metadata
        )

        assert hook_input.metadata == metadata

    def test_hook_input_validation_error(self):
        """Test HookInput validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            HookInput(event_type="", data={})

        errors = exc_info.value.errors()
        assert any(error["type"] == "string_too_short" for error in errors)

    def test_hook_input_json_serialization(self):
        """Test HookInput JSON serialization/deserialization."""
        hook_input = HookInput(
            event_type="api_call", data={"endpoint": "/users", "method": "GET"}
        )

        json_str = hook_input.model_dump_json()
        assert isinstance(json_str, str)

        parsed_data = json.loads(json_str)
        recreated = HookInput.model_validate(parsed_data)
        assert recreated.event_type == hook_input.event_type
        assert recreated.data == hook_input.data


class TestHookOutput:
    """Tests for HookOutput model."""

    def test_hook_output_success(self):
        """Test successful HookOutput."""
        hook_output = HookOutput(
            status=HookStatus.SUCCESS,
            data={"result": "completed"},
            message="Hook executed successfully",
        )

        assert hook_output.status == HookStatus.SUCCESS
        assert hook_output.data == {"result": "completed"}
        assert hook_output.message == "Hook executed successfully"
        assert hook_output.error is None
        assert hook_output.execution_time is None

    def test_hook_output_with_error(self):
        """Test HookOutput with error information."""
        error = HookError(
            code="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "email", "reason": "invalid format"},
        )

        hook_output = HookOutput(status=HookStatus.FAILED, data={}, error=error)

        assert hook_output.status == HookStatus.FAILED
        assert hook_output.error == error

    def test_hook_output_with_execution_time(self):
        """Test HookOutput with execution time."""
        hook_output = HookOutput(
            status=HookStatus.SUCCESS, data={"processed": 100}, execution_time=1.25
        )

        assert hook_output.execution_time == 1.25

    def test_hook_output_validation_negative_execution_time(self):
        """Test HookOutput validation for negative execution time."""
        with pytest.raises(ValidationError) as exc_info:
            HookOutput(status=HookStatus.SUCCESS, data={}, execution_time=-1.0)

        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)


class TestHookMetadata:
    """Tests for HookMetadata model."""

    def test_hook_metadata_minimal(self):
        """Test HookMetadata with minimal fields."""
        metadata = HookMetadata(source="test")

        assert metadata.source == "test"
        assert metadata.version is None
        assert metadata.tags == []
        assert metadata.extra == {}

    def test_hook_metadata_complete(self):
        """Test HookMetadata with all fields."""
        metadata = HookMetadata(
            source="production",
            version="2.1.0",
            tags=["prod", "critical"],
            extra={"region": "us-east-1", "env": "production"},
        )

        assert metadata.source == "production"
        assert metadata.version == "2.1.0"
        assert metadata.tags == ["prod", "critical"]
        assert metadata.extra == {"region": "us-east-1", "env": "production"}

    def test_hook_metadata_empty_source_validation(self):
        """Test HookMetadata validation for empty source."""
        with pytest.raises(ValidationError) as exc_info:
            HookMetadata(source="")

        errors = exc_info.value.errors()
        assert any(error["type"] == "string_too_short" for error in errors)


class TestHookStatus:
    """Tests for HookStatus enum."""

    def test_hook_status_values(self):
        """Test HookStatus enum values."""
        assert HookStatus.PENDING == "pending"
        assert HookStatus.RUNNING == "running"
        assert HookStatus.SUCCESS == "success"
        assert HookStatus.FAILED == "failed"
        assert HookStatus.CANCELLED == "cancelled"

    def test_hook_status_in_model(self):
        """Test HookStatus usage in models."""
        result = HookResult(
            hook_id="test-123",
            status=HookStatus.RUNNING,
            input_data=HookInput(event_type="test", data={}),
            output_data=None,
        )

        assert result.status == HookStatus.RUNNING


class TestExecutionContext:
    """Tests for ExecutionContext model."""

    def test_execution_context_minimal(self):
        """Test ExecutionContext with minimal fields."""
        context = ExecutionContext(hook_id="hook-123", execution_id="exec-456")

        assert context.hook_id == "hook-123"
        assert context.execution_id == "exec-456"
        assert context.user_id is None
        assert context.session_id is None
        assert context.environment == "development"
        assert context.variables == {}

    def test_execution_context_complete(self):
        """Test ExecutionContext with all fields."""
        variables = {"API_KEY": "secret", "DEBUG": "true"}
        context = ExecutionContext(
            hook_id="hook-123",
            execution_id="exec-456",
            user_id="user-789",
            session_id="session-abc",
            environment="production",
            variables=variables,
        )

        assert context.user_id == "user-789"
        assert context.session_id == "session-abc"
        assert context.environment == "production"
        assert context.variables == variables

    def test_execution_context_environment_validation(self):
        """Test ExecutionContext environment validation."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionContext(
                hook_id="hook-123", execution_id="exec-456", environment="invalid_env"
            )

        errors = exc_info.value.errors()
        # Check for value_error which is raised by custom validator
        assert any(error["type"] == "value_error" for error in errors)


class TestHookResult:
    """Tests for HookResult model."""

    def test_hook_result_pending(self):
        """Test HookResult in pending state."""
        input_data = HookInput(event_type="test", data={"key": "value"})
        result = HookResult(
            hook_id="result-123",
            status=HookStatus.PENDING,
            input_data=input_data,
            output_data=None,
        )

        assert result.hook_id == "result-123"
        assert result.status == HookStatus.PENDING
        assert result.input_data == input_data
        assert result.output_data is None
        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.execution_context is None

    def test_hook_result_completed(self):
        """Test HookResult in completed state."""
        input_data = HookInput(event_type="process", data={"items": [1, 2, 3]})
        output_data = HookOutput(
            status=HookStatus.SUCCESS,
            data={"processed": 3},
            message="All items processed",
        )

        result = HookResult(
            hook_id="result-456",
            status=HookStatus.SUCCESS,
            input_data=input_data,
            output_data=output_data,
        )

        assert result.status == HookStatus.SUCCESS
        assert result.output_data == output_data

    def test_hook_result_with_context(self):
        """Test HookResult with execution context."""
        input_data = HookInput(event_type="auth", data={"token": "xyz"})
        context = ExecutionContext(
            hook_id="result-789", execution_id="exec-123", user_id="user-456"
        )

        result = HookResult(
            hook_id="result-789",
            status=HookStatus.RUNNING,
            input_data=input_data,
            output_data=None,
            execution_context=context,
        )

        assert result.execution_context == context


class TestHookError:
    """Tests for HookError model."""

    def test_hook_error_minimal(self):
        """Test HookError with minimal fields."""
        error = HookError(code="GENERIC_ERROR", message="Something went wrong")

        assert error.code == "GENERIC_ERROR"
        assert error.message == "Something went wrong"
        assert error.details is None

    def test_hook_error_with_details(self):
        """Test HookError with detailed information."""
        details = {
            "traceback": ["line 1", "line 2", "line 3"],
            "context": {"function": "process_data", "line": 42},
        }

        error = HookError(
            code="RUNTIME_ERROR", message="Division by zero", details=details
        )

        assert error.details == details

    def test_hook_error_validation(self):
        """Test HookError validation for empty fields."""
        with pytest.raises(ValidationError) as exc_info:
            HookError(code="", message="")

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Both code and message should fail validation


class TestModelIntegration:
    """Integration tests for models working together."""

    def test_complete_hook_flow(self):
        """Test a complete hook execution flow with all models."""
        # Create input
        metadata = HookMetadata(
            source="integration_test", version="1.0.0", tags=["test"]
        )

        hook_input = HookInput(
            event_type="data_processing", data={"records": 100}, metadata=metadata
        )

        # Create execution context
        context = ExecutionContext(
            hook_id="integration-test-123",
            execution_id="exec-abc-123",
            environment="development",
            variables={"BATCH_SIZE": "10"},
        )

        # Create successful output
        output = HookOutput(
            status=HookStatus.SUCCESS,
            data={"processed_records": 100, "errors": 0},
            message="Processing completed successfully",
            execution_time=2.5,
        )

        # Create final result
        result = HookResult(
            hook_id="integration-test-123",
            status=HookStatus.SUCCESS,
            input_data=hook_input,
            output_data=output,
            execution_context=context,
        )

        # Verify all data is preserved
        assert result.input_data.metadata.source == "integration_test"
        assert result.output_data.execution_time == 2.5
        assert result.execution_context.variables["BATCH_SIZE"] == "10"

        # Test JSON round-trip
        json_data = result.model_dump_json()
        recreated = HookResult.model_validate_json(json_data)
        assert recreated.hook_id == result.hook_id
        assert recreated.status == result.status

    def test_error_handling_flow(self):
        """Test error handling in hook execution flow."""
        hook_input = HookInput(
            event_type="file_upload", data={"file_path": "/invalid/path.txt"}
        )

        error = HookError(
            code="FILE_NOT_FOUND",
            message="The specified file could not be found",
            details={"path": "/invalid/path.txt", "errno": 2},
        )

        output = HookOutput(
            status=HookStatus.FAILED, data={}, error=error, message="File upload failed"
        )

        result = HookResult(
            hook_id="error-test-456",
            status=HookStatus.FAILED,
            input_data=hook_input,
            output_data=output,
        )

        assert result.status == HookStatus.FAILED
        assert result.output_data.error.code == "FILE_NOT_FOUND"
