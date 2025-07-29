"""Tests for QuickHooks custom exceptions."""

import json

import pytest

from quickhooks.exceptions import (
    ConcurrencyError,
    ConfigurationError,
    DependencyError,
    HookError,
    HookExecutionError,
    HookNotFoundError,
    HookTimeoutError,
    HookValidationError,
    InstallationError,
    MemoryError,
    ProcessingError,
    QuickHooksError,
    ResourceError,
    SerializationError,
    TaskExecutionError,
    ValidationError,
    VisualizationError,
    format_exception_chain,
    get_error_summary,
    handle_exception,
)


class TestQuickHooksError:
    """Test cases for QuickHooksError base class."""

    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = QuickHooksError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "QuickHooksError"
        assert error.context == {}

    def test_error_with_code_and_context(self):
        """Test error with custom code and context."""
        context = {"file": "test.py", "line": 42}
        error = QuickHooksError(
            "Custom error", error_code="CUSTOM_ERROR", context=context
        )

        assert error.error_code == "CUSTOM_ERROR"
        assert error.context == context
        assert "file=test.py" in str(error)
        assert "line=42" in str(error)

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        context = {"key": "value"}
        error = QuickHooksError(
            "Test message", error_code="TEST_ERROR", context=context
        )

        data = error.to_dict()

        assert data["error_type"] == "QuickHooksError"
        assert data["error_code"] == "TEST_ERROR"
        assert data["message"] == "Test message"
        assert data["context"] == context


class TestConfigurationError:
    """Test cases for ConfigurationError."""

    def test_configuration_error_creation(self):
        """Test configuration error creation."""
        error = ConfigurationError(
            "Invalid config", config_file="config.yaml", config_section="database"
        )

        assert error.error_code == "CONFIG_ERROR"
        assert error.context["config_file"] == "config.yaml"
        assert error.context["config_section"] == "database"

    def test_configuration_error_minimal(self):
        """Test configuration error with minimal parameters."""
        error = ConfigurationError("Invalid config")

        assert error.message == "Invalid config"
        assert error.error_code == "CONFIG_ERROR"


class TestHookError:
    """Test cases for HookError and subclasses."""

    def test_hook_error_creation(self):
        """Test basic hook error creation."""
        error = HookError(
            "Hook failed", hook_name="test_hook", hook_path="/path/to/hook.py"
        )

        assert error.error_code == "HOOK_ERROR"
        assert error.context["hook_name"] == "test_hook"
        assert error.context["hook_path"] == "/path/to/hook.py"

    def test_hook_execution_error(self):
        """Test hook execution error."""
        error = HookExecutionError(
            "Execution failed",
            hook_name="test_hook",
            exit_code=1,
            stderr="Error output",
            duration=5.0,
        )

        assert error.error_code == "HOOK_EXECUTION_ERROR"
        assert error.context["exit_code"] == 1
        assert error.context["stderr"] == "Error output"
        assert error.context["duration"] == 5.0

    def test_hook_timeout_error(self):
        """Test hook timeout error."""
        error = HookTimeoutError("Hook timed out", hook_name="slow_hook", timeout=30.0)

        assert error.error_code == "HOOK_TIMEOUT_ERROR"
        assert error.context["timeout"] == 30.0

    def test_hook_validation_error(self):
        """Test hook validation error."""
        validation_errors = ["Missing required method", "Invalid signature"]
        error = HookValidationError(
            "Validation failed",
            hook_name="invalid_hook",
            validation_errors=validation_errors,
        )

        assert error.error_code == "HOOK_VALIDATION_ERROR"
        assert error.context["validation_errors"] == validation_errors

    def test_hook_not_found_error(self):
        """Test hook not found error."""
        search_paths = ["/path1", "/path2"]
        error = HookNotFoundError(
            "Hook not found", hook_name="missing_hook", search_paths=search_paths
        )

        assert error.error_code == "HOOK_NOT_FOUND_ERROR"
        assert error.context["search_paths"] == search_paths


class TestProcessingError:
    """Test cases for ProcessingError and subclasses."""

    def test_processing_error_creation(self):
        """Test processing error creation."""
        error = ProcessingError(
            "Processing failed", task_id="task_123", processing_mode="parallel"
        )

        assert error.error_code == "PROCESSING_ERROR"
        assert error.context["task_id"] == "task_123"
        assert error.context["processing_mode"] == "parallel"

    def test_task_execution_error(self):
        """Test task execution error."""
        error = TaskExecutionError(
            "Task failed", task_id="task_456", attempts=3, max_retries=2
        )

        assert error.error_code == "TASK_EXECUTION_ERROR"
        assert error.context["attempts"] == 3
        assert error.context["max_retries"] == 2

    def test_dependency_error(self):
        """Test dependency error."""
        missing_deps = ["task_1", "task_2"]
        circular_deps = ["task_a", "task_b"]

        error = DependencyError(
            "Dependency issue",
            task_id="task_c",
            missing_dependencies=missing_deps,
            circular_dependencies=circular_deps,
        )

        assert error.error_code == "DEPENDENCY_ERROR"
        assert error.context["missing_dependencies"] == missing_deps
        assert error.context["circular_dependencies"] == circular_deps


class TestResourceError:
    """Test cases for ResourceError and subclasses."""

    def test_resource_error_creation(self):
        """Test resource error creation."""
        error = ResourceError(
            "Resource exhausted", resource_type="cpu", current_usage=95, limit=100
        )

        assert error.error_code == "RESOURCE_ERROR"
        assert error.context["resource_type"] == "cpu"
        assert error.context["current_usage"] == 95
        assert error.context["limit"] == 100

    def test_memory_error(self):
        """Test memory error."""
        error = MemoryError("Out of memory", current_memory=1024, memory_limit=512)

        assert error.error_code == "MEMORY_ERROR"
        assert error.context["resource_type"] == "memory"
        assert error.context["current_usage"] == 1024
        assert error.context["limit"] == 512

    def test_concurrency_error(self):
        """Test concurrency error."""
        error = ConcurrencyError("Too many workers", current_workers=10, worker_limit=8)

        assert error.error_code == "CONCURRENCY_ERROR"
        assert error.context["resource_type"] == "workers"
        assert error.context["current_usage"] == 10
        assert error.context["limit"] == 8


class TestOtherExceptions:
    """Test cases for other exception types."""

    def test_validation_error(self):
        """Test validation error."""
        error = ValidationError(
            "Invalid input",
            field="username",
            value="",
            validation_rules=["required", "min_length:3"],
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.context["field"] == "username"
        assert error.context["value"] == ""
        assert error.context["validation_rules"] == ["required", "min_length:3"]

    def test_serialization_error(self):
        """Test serialization error."""
        error = SerializationError(
            "JSON decode failed", data_type="HookOutput", format="json"
        )

        assert error.error_code == "SERIALIZATION_ERROR"
        assert error.context["data_type"] == "HookOutput"
        assert error.context["format"] == "json"

    def test_visualization_error(self):
        """Test visualization error."""
        error = VisualizationError(
            "Diagram generation failed", diagram_type="flowchart", output_format="svg"
        )

        assert error.error_code == "VISUALIZATION_ERROR"
        assert error.context["diagram_type"] == "flowchart"
        assert error.context["output_format"] == "svg"

    def test_installation_error(self):
        """Test installation error."""
        error = InstallationError(
            "Installation failed",
            component="hook_manager",
            installation_path="/usr/local/bin",
        )

        assert error.error_code == "INSTALLATION_ERROR"
        assert error.context["component"] == "hook_manager"
        assert error.context["installation_path"] == "/usr/local/bin"


class TestExceptionUtilities:
    """Test cases for exception utility functions."""

    def test_handle_exception_quickhooks_error(self):
        """Test handling QuickHooks exceptions."""
        original_error = HookExecutionError("Test error")
        handled_error = handle_exception(original_error)

        assert handled_error is original_error

    def test_handle_exception_file_not_found(self):
        """Test handling FileNotFoundError."""
        original_error = FileNotFoundError("File not found")
        original_error.filename = "/path/to/file.py"

        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, HookNotFoundError)
        assert handled_error.context["hook_path"] == "/path/to/file.py"

    def test_handle_exception_timeout(self):
        """Test handling TimeoutError."""
        original_error = TimeoutError("Operation timed out")
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, HookTimeoutError)

    def test_handle_exception_memory_error(self):
        """Test handling MemoryError."""
        original_error = MemoryError("Out of memory")
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, MemoryError)

    def test_handle_exception_value_error(self):
        """Test handling ValueError."""
        original_error = ValueError("Invalid value")
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, ValidationError)

    def test_handle_exception_json_decode_error(self):
        """Test handling JSON decode error."""
        original_error = json.JSONDecodeError("Invalid JSON", "doc", 0)
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, SerializationError)

    def test_handle_exception_unicode_decode_error(self):
        """Test handling Unicode decode error."""
        original_error = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, SerializationError)

    def test_handle_exception_generic(self):
        """Test handling generic exceptions."""
        original_error = RuntimeError("Runtime error")
        handled_error = handle_exception(original_error)

        assert isinstance(handled_error, QuickHooksError)
        assert "Unexpected error" in handled_error.message
        assert handled_error.context["original_type"] == "RuntimeError"

    def test_format_exception_chain(self):
        """Test formatting exception chain."""
        # Create a chain of exceptions
        original_error = ValueError("Original error")
        wrapped_error = HookExecutionError("Hook failed")
        wrapped_error.__cause__ = original_error

        formatted = format_exception_chain(wrapped_error)

        assert "HOOK_EXECUTION_ERROR: Hook failed" in formatted
        assert "ValueError: Original error" in formatted

    def test_format_exception_chain_with_context(self):
        """Test formatting exception chain with context."""
        error = HookExecutionError("Hook failed", hook_name="test_hook", exit_code=1)

        formatted = format_exception_chain(error)

        assert "HOOK_EXECUTION_ERROR: Hook failed" in formatted
        assert "hook_name: test_hook" in formatted
        assert "exit_code: 1" in formatted

    def test_get_error_summary_quickhooks_error(self):
        """Test getting error summary for QuickHooks error."""
        error = HookExecutionError("Test error", hook_name="test_hook")
        summary = get_error_summary(error)

        assert summary["error_type"] == "HookExecutionError"
        assert summary["error_code"] == "HOOK_EXECUTION_ERROR"
        assert summary["message"] == "Test error"
        assert summary["context"]["hook_name"] == "test_hook"
        assert "recoverable" in summary

    def test_get_error_summary_external_error(self):
        """Test getting error summary for external error."""
        error = ValueError("Invalid value")
        summary = get_error_summary(error)

        assert summary["error_type"] == "ValueError"
        assert summary["error_code"] == "EXTERNAL_ERROR"
        assert summary["message"] == "Invalid value"
        assert summary["context"] == {}
        assert summary["recoverable"] is False

    def test_recoverable_error_detection(self):
        """Test detection of recoverable errors."""
        from quickhooks.exceptions import _is_recoverable_error

        # Recoverable errors
        assert _is_recoverable_error(HookTimeoutError("Timeout"))
        assert _is_recoverable_error(ResourceError("Resource issue"))
        assert _is_recoverable_error(ConcurrencyError("Too many workers"))
        assert _is_recoverable_error(MemoryError("Out of memory"))

        # Non-recoverable errors
        assert not _is_recoverable_error(HookValidationError("Invalid hook"))
        assert not _is_recoverable_error(ConfigurationError("Bad config"))
        assert not _is_recoverable_error(HookNotFoundError("Missing hook"))


class TestExceptionInheritance:
    """Test cases for exception inheritance hierarchy."""

    def test_inheritance_chain(self):
        """Test that exceptions inherit correctly."""
        # All custom exceptions should inherit from QuickHooksError
        assert issubclass(ConfigurationError, QuickHooksError)
        assert issubclass(HookError, QuickHooksError)
        assert issubclass(HookExecutionError, HookError)
        assert issubclass(HookTimeoutError, HookExecutionError)
        assert issubclass(ProcessingError, QuickHooksError)
        assert issubclass(TaskExecutionError, ProcessingError)
        assert issubclass(ResourceError, QuickHooksError)
        assert issubclass(MemoryError, ResourceError)

    def test_exception_catching(self):
        """Test that exceptions can be caught by base classes."""
        # Should be able to catch specific exceptions
        try:
            raise HookTimeoutError("Timeout")
        except HookTimeoutError:
            pass
        else:
            pytest.fail("Should have caught HookTimeoutError")

        # Should be able to catch by parent class
        try:
            raise HookTimeoutError("Timeout")
        except HookExecutionError:
            pass
        else:
            pytest.fail("Should have caught as HookExecutionError")

        # Should be able to catch by base class
        try:
            raise HookTimeoutError("Timeout")
        except QuickHooksError:
            pass
        else:
            pytest.fail("Should have caught as QuickHooksError")
