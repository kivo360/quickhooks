"""Core Pydantic models for the QuickHooks framework.

This module defines the fundamental data structures used throughout the framework
for hook inputs, outputs, metadata, execution context, and results.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class HookStatus(str, Enum):
    """Enumeration of possible hook execution states."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HookMetadata(BaseModel):
    """Metadata associated with a hook execution.

    Contains information about the source, version, tags, and additional
    context for hook execution tracking and debugging.
    """

    source: str = Field(
        ...,
        min_length=1,
        description="Source system or component that triggered the hook",
    )
    version: str | None = Field(None, description="Version of the hook or system")
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization and filtering"
    )
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata fields"
    )


class HookError(BaseModel):
    """Error information for failed hook executions.

    Captures error codes, messages, and detailed context information
    to aid in debugging and error handling.
    """

    code: str = Field(..., min_length=1, description="Error code identifier")
    message: str = Field(..., min_length=1, description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        None, description="Additional error details and context"
    )


class HookInput(BaseModel):
    """Input data structure for hook execution.

    Contains the event information, data payload, execution context,
    and metadata needed to execute a hook.
    """

    event_type: str = Field(
        ..., min_length=1, description="Type of event that triggered the hook"
    )
    data: dict[str, Any] = Field(..., description="Event data payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the event occurred",
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional execution context"
    )
    metadata: HookMetadata | None = Field(
        None, description="Metadata about the hook execution"
    )


class HookOutput(BaseModel):
    """Output data structure from hook execution.

    Contains the execution status, result data, messages, error information,
    and performance metrics from hook execution.
    """

    status: HookStatus = Field(..., description="Execution status of the hook")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Result data from hook execution"
    )
    message: str | None = Field(None, description="Human-readable status message")
    error: HookError | None = Field(
        None, description="Error information if execution failed"
    )
    execution_time: float | None = Field(
        None, ge=0.0, description="Execution time in seconds"
    )


class ExecutionContext(BaseModel):
    """Context information for hook execution.

    Provides execution environment details, user information, session data,
    and environment variables needed during hook execution.
    """

    hook_id: str = Field(..., description="Unique identifier for the hook")
    execution_id: str = Field(..., description="Unique identifier for this execution")
    user_id: str | None = Field(
        None, description="ID of the user who triggered the execution"
    )
    session_id: str | None = Field(None, description="Session identifier")
    environment: str = Field(default="development", description="Execution environment")
    variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables and settings"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment values."""
        allowed_environments = {"development", "testing", "staging", "production"}
        if v not in allowed_environments:
            raise ValueError(
                f"Environment must be one of: {', '.join(allowed_environments)}"
            )
        return v


class HookResult(BaseModel):
    """Complete result of a hook execution.

    Aggregates input data, output data, execution context, and timing
    information for a complete record of hook execution.
    """

    hook_id: str = Field(..., description="Unique identifier for the hook")
    status: HookStatus = Field(..., description="Current status of the hook execution")
    input_data: HookInput = Field(..., description="Input data that triggered the hook")
    output_data: HookOutput | None = Field(
        None, description="Output data from hook execution"
    )
    execution_context: ExecutionContext | None = Field(
        None, description="Execution context information"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the execution was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the execution was last updated",
    )

    def model_post_init(self, __context: Any) -> None:
        """Update the updated_at timestamp after model creation."""
        self.updated_at = datetime.now(UTC)
