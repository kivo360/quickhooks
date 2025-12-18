"""Custom exceptions for the QuickHooks framework.

This module defines all custom exceptions used throughout the QuickHooks
framework for better error handling and debugging.
"""

import json
from typing import Any


class QuickHooksError(Exception):
    """Base exception for all QuickHooks framework errors.

    This is the base class for all custom exceptions in the framework.
    It provides common functionality for error handling and debugging.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
        }


class ConfigurationError(QuickHooksError):
    """Raised when there's an error in configuration.

    This includes invalid configuration files, missing required settings,
    or incompatible configuration options.
    """

    def __init__(
        self,
        message: str,
        config_file: str | None = None,
        config_section: str | None = None,
    ):
        context = {}
        if config_file:
            context["config_file"] = config_file
        if config_section:
            context["config_section"] = config_section

        super().__init__(message, "CONFIG_ERROR", context)


class HookError(QuickHooksError):
    """Base class for hook-related errors."""

    def __init__(
        self,
        message: str,
        hook_name: str | None = None,
        hook_path: str | None = None,
        error_code: str | None = None,
    ):
        context = {}
        if hook_name:
            context["hook_name"] = hook_name
        if hook_path:
            context["hook_path"] = str(hook_path)

        super().__init__(message, error_code or "HOOK_ERROR", context)


class HookExecutionError(HookError):
    """Raised when a hook fails to execute properly.

    This includes process failures, timeouts, and unexpected errors
    during hook execution.
    """

    def __init__(
        self,
        message: str,
        hook_name: str | None = None,
        hook_path: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
        duration: float | None = None,
    ):
        context = {}
        if exit_code is not None:
            context["exit_code"] = exit_code
        if stderr:
            context["stderr"] = stderr
        if duration is not None:
            context["duration"] = duration

        super().__init__(message, hook_name, hook_path, "HOOK_EXECUTION_ERROR")
        self.context.update(context)


class HookTimeoutError(HookExecutionError):
    """Raised when a hook execution times out."""

    def __init__(
        self,
        message: str,
        hook_name: str | None = None,
        hook_path: str | None = None,
        timeout: float | None = None,
    ):
        context = {}
        if timeout is not None:
            context["timeout"] = timeout

        super().__init__(message, hook_name, hook_path, -1, None, timeout)
        self.error_code = "HOOK_TIMEOUT_ERROR"
        self.context.update(context)


class HookValidationError(HookError):
    """Raised when hook validation fails.

    This includes invalid hook scripts, missing required methods,
    or incompatible hook interfaces.
    """

    def __init__(
        self,
        message: str,
        hook_name: str | None = None,
        hook_path: str | None = None,
        validation_errors: list[str] | None = None,
    ):
        context = {}
        if validation_errors:
            context["validation_errors"] = validation_errors

        super().__init__(message, hook_name, hook_path, "HOOK_VALIDATION_ERROR")
        self.context.update(context)


class HookNotFoundError(HookError):
    """Raised when a required hook cannot be found."""

    def __init__(
        self,
        message: str,
        hook_name: str | None = None,
        hook_path: str | None = None,
        search_paths: list[str] | None = None,
    ):
        context = {}
        if search_paths:
            context["search_paths"] = search_paths

        super().__init__(message, hook_name, hook_path, "HOOK_NOT_FOUND_ERROR")
        self.context.update(context)


class ProcessingError(QuickHooksError):
    """Base class for parallel processing errors."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        processing_mode: str | None = None,
        error_code: str | None = None,
    ):
        context = {}
        if task_id:
            context["task_id"] = task_id
        if processing_mode:
            context["processing_mode"] = processing_mode

        super().__init__(message, error_code or "PROCESSING_ERROR", context)


class TaskExecutionError(ProcessingError):
    """Raised when a processing task fails to execute."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        attempts: int | None = None,
        max_retries: int | None = None,
    ):
        context = {}
        if attempts is not None:
            context["attempts"] = attempts
        if max_retries is not None:
            context["max_retries"] = max_retries

        super().__init__(message, task_id, None, "TASK_EXECUTION_ERROR")
        self.context.update(context)


class DependencyError(ProcessingError):
    """Raised when task dependencies cannot be resolved."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        missing_dependencies: list[str] | None = None,
        circular_dependencies: list[str] | None = None,
    ):
        context = {}
        if missing_dependencies:
            context["missing_dependencies"] = missing_dependencies
        if circular_dependencies:
            context["circular_dependencies"] = circular_dependencies

        super().__init__(message, task_id, None, "DEPENDENCY_ERROR")
        self.context.update(context)


class ResourceError(QuickHooksError):
    """Raised when system resources are insufficient or unavailable."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        current_usage: Any | None = None,
        limit: Any | None = None,
    ):
        context = {}
        if resource_type:
            context["resource_type"] = resource_type
        if current_usage is not None:
            context["current_usage"] = current_usage
        if limit is not None:
            context["limit"] = limit

        super().__init__(message, "RESOURCE_ERROR", context)


class MemoryError(ResourceError):
    """Raised when memory usage exceeds limits."""

    def __init__(
        self,
        message: str,
        current_memory: int | None = None,
        memory_limit: int | None = None,
    ):
        super().__init__(message, "memory", current_memory, memory_limit)
        self.error_code = "MEMORY_ERROR"


class ConcurrencyError(ResourceError):
    """Raised when concurrency limits are exceeded."""

    def __init__(
        self,
        message: str,
        current_workers: int | None = None,
        worker_limit: int | None = None,
    ):
        super().__init__(message, "workers", current_workers, worker_limit)
        self.error_code = "CONCURRENCY_ERROR"


class ValidationError(QuickHooksError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        validation_rules: list[str] | None = None,
    ):
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = value
        if validation_rules:
            context["validation_rules"] = validation_rules

        super().__init__(message, "VALIDATION_ERROR", context)


class SerializationError(QuickHooksError):
    """Raised when data serialization/deserialization fails."""

    def __init__(
        self,
        message: str,
        data_type: str | None = None,
        format: str | None = None,
    ):
        context = {}
        if data_type:
            context["data_type"] = data_type
        if format:
            context["format"] = format

        super().__init__(message, "SERIALIZATION_ERROR", context)


class VisualizationError(QuickHooksError):
    """Raised when diagram generation fails."""

    def __init__(
        self,
        message: str,
        diagram_type: str | None = None,
        output_format: str | None = None,
    ):
        context = {}
        if diagram_type:
            context["diagram_type"] = diagram_type
        if output_format:
            context["output_format"] = output_format

        super().__init__(message, "VISUALIZATION_ERROR", context)


class InstallationError(QuickHooksError):
    """Raised when installation or setup fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        installation_path: str | None = None,
    ):
        context = {}
        if component:
            context["component"] = component
        if installation_path:
            context["installation_path"] = installation_path

        super().__init__(message, "INSTALLATION_ERROR", context)


# Exception utilities


def handle_exception(exception: Exception) -> QuickHooksError:
    """Convert standard exceptions to QuickHooks exceptions where appropriate."""

    if isinstance(exception, QuickHooksError):
        return exception

    if isinstance(exception, FileNotFoundError):
        return HookNotFoundError(
            str(exception),
            hook_path=str(exception.filename) if exception.filename else None,
        )

    if isinstance(exception, TimeoutError):
        return HookTimeoutError(str(exception))

    if isinstance(exception, MemoryError):
        return MemoryError(str(exception))

    if isinstance(exception, ValueError):
        return ValidationError(str(exception))

    if isinstance(exception, json.JSONDecodeError | UnicodeDecodeError):
        return SerializationError(str(exception))

    # For other exceptions, wrap in generic QuickHooksError
    return QuickHooksError(
        f"Unexpected error: {exception!s}",
        error_code="UNEXPECTED_ERROR",
        context={"original_type": type(exception).__name__},
    )


def format_exception_chain(exception: Exception) -> str:
    """Format exception chain for logging and debugging."""

    lines = []
    current = exception
    level = 0

    while current is not None:
        indent = "  " * level

        if isinstance(current, QuickHooksError):
            lines.append(f"{indent}{current.error_code}: {current.message}")
            if current.context:
                for key, value in current.context.items():
                    lines.append(f"{indent}  {key}: {value}")
        else:
            lines.append(f"{indent}{type(current).__name__}: {current!s}")

        current = current.__cause__ if hasattr(current, "__cause__") else None
        level += 1

    return "\n".join(lines)


def get_error_summary(exception: Exception) -> dict[str, Any]:
    """Get a summary of the error for reporting purposes."""

    if isinstance(exception, QuickHooksError):
        return {
            "error_type": exception.__class__.__name__,
            "error_code": exception.error_code,
            "message": exception.message,
            "context": exception.context,
            "recoverable": _is_recoverable_error(exception),
        }
    return {
        "error_type": type(exception).__name__,
        "error_code": "EXTERNAL_ERROR",
        "message": str(exception),
        "context": {},
        "recoverable": False,
    }


def _is_recoverable_error(exception: QuickHooksError) -> bool:
    """Determine if an error is potentially recoverable."""

    recoverable_types = {HookTimeoutError, ResourceError, ConcurrencyError, MemoryError}

    return type(exception) in recoverable_types
