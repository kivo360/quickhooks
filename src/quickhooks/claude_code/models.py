"""Pydantic models for Claude Code settings.json based on official schema.

This module provides type-safe models for Claude Code settings, following the
official JSON schema from https://json.schemastore.org/claude-code-settings.json
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HookCommand(BaseModel):
    """Hook command configuration.

    Represents a single hook command that executes at a specific lifecycle point.
    """

    type: Literal["command"] = Field(
        description="Type of hook implementation",
        default="command",
    )
    command: str = Field(
        description="Shell command to execute",
        min_length=1,
    )
    timeout: float | None = Field(
        None,
        description="Optional timeout in seconds for this specific command",
        gt=0,
    )

    model_config = {"extra": "forbid"}


class HookMatcher(BaseModel):
    """Hook matcher configuration with multiple hooks.

    Allows executing multiple hooks based on an optional tool name pattern.
    """

    matcher: str | None = Field(
        None,
        description="Optional pattern to match tool names, case-sensitive (only applicable for PreToolUse and PostToolUse)",
    )
    hooks: list[HookCommand] = Field(
        description="Array of hooks to execute",
        min_length=1,
    )

    model_config = {"extra": "forbid"}


class HookEventName(str, Enum):
    """Valid hook event names in Claude Code."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    NOTIFICATION = "Notification"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"


class PermissionMode(str, Enum):
    """Default permission mode for tool execution."""

    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    DEFAULT = "default"
    PLAN = "plan"


class LoginMethod(str, Enum):
    """Available login methods."""

    CLAUDE_AI = "claudeai"
    CONSOLE = "console"


class Permissions(BaseModel):
    """Tool permissions configuration."""

    allow: list[str] | None = Field(
        None,
        description="List of allowed tool permission rules",
    )
    ask: list[str] | None = Field(
        None,
        description="List of ask tool permission rules",
    )
    deny: list[str] | None = Field(
        None,
        description="List of denied tool permission rules",
    )
    default_mode: PermissionMode | None = Field(
        None,
        alias="defaultMode",
        description="Default permission mode for tool execution",
    )
    disable_bypass_permissions_mode: Literal["disable"] | None = Field(
        None,
        alias="disableBypassPermissionsMode",
        description="Disable bypass permissions mode",
    )
    additional_directories: list[str] | None = Field(
        None,
        alias="additionalDirectories",
        description="Paths to additional directories Claude can access beyond the working directory",
    )

    model_config = {"extra": "forbid", "populate_by_name": True}

    @field_validator("allow", "ask", "deny")
    @classmethod
    def validate_unique_rules(cls, v: list[str] | None) -> list[str] | None:
        """Ensure permission rules are unique."""
        if v is not None and len(v) != len(set(v)):
            raise ValueError("Permission rules must be unique")
        return v


class StatusLine(BaseModel):
    """Custom status line configuration."""

    type: Literal["command"] = Field(
        description="Type of status line implementation",
        default="command",
    )
    command: str = Field(
        description="Shell command to execute to generate the status line",
        min_length=1,
    )
    padding: float | None = Field(
        None,
        description="Optional padding for the status line",
    )

    model_config = {"extra": "forbid"}


class ClaudeCodeSettings(BaseModel):
    """Complete Claude Code settings.json configuration.

    This model matches the official JSON schema from SchemaStore and provides
    type-safe access to all Claude Code settings.

    Example:
        >>> settings = ClaudeCodeSettings(
        ...     env={"ANTHROPIC_MODEL": "claude-opus-4-1"},
        ...     permissions=Permissions(
        ...         allow=["Bash(git add:*)"],
        ...         ask=["Bash(git commit:*)"],
        ...         deny=["Read(*.env)"],
        ...     ),
        ... )
    """

    schema_: str | None = Field(
        None,
        alias="$schema",
        description="The schema for the settings.json file",
    )

    # Core Settings
    api_key_helper: str | None = Field(
        None,
        alias="apiKeyHelper",
        description="Custom script path to generate an auth value",
        min_length=1,
    )
    cleanup_period_days: int | None = Field(
        None,
        alias="cleanupPeriodDays",
        description="How long to locally retain chat transcripts (in days)",
        ge=0,
    )
    env: dict[str, str] | None = Field(
        None,
        description="Environment variables applied to every session",
    )
    include_co_authored_by: bool | None = Field(
        None,
        alias="includeCoAuthoredBy",
        description="Include 'co-authored-by Claude' byline in git commits and pull requests",
    )
    model: str | None = Field(
        None,
        description="Deprecated: use env.ANTHROPIC_MODEL and env.ANTHROPIC_SMALL_FAST_MODEL instead",
    )

    # Permissions
    permissions: Permissions | None = Field(
        None,
        description="Tool permissions",
    )

    # MCP Server Management
    enable_all_project_mcp_servers: bool | None = Field(
        None,
        alias="enableAllProjectMcpServers",
        description="Whether to automatically approve all MCP servers in the project",
    )
    enabled_mcpjson_servers: list[str] | None = Field(
        None,
        alias="enabledMcpjsonServers",
        description="List of allowed MCP servers from .mcp.json",
    )
    disabled_mcpjson_servers: list[str] | None = Field(
        None,
        alias="disabledMcpjsonServers",
        description="List of denied MCP servers from .mcp.json",
    )

    # Hooks
    hooks: dict[str, list[HookMatcher]] | None = Field(
        None,
        description="Hooks configuration for executing commands at specific points in Claude Code's lifecycle",
    )
    disable_all_hooks: bool | None = Field(
        None,
        alias="disableAllHooks",
        description="Disable all hooks",
    )

    # Authentication
    force_login_method: LoginMethod | None = Field(
        None,
        alias="forceLoginMethod",
        description="Force a specific login method",
    )
    force_login_org_uuid: str | None = Field(
        None,
        alias="forceLoginOrgUUID",
        description="Force login with a specific organization UUID",
        min_length=1,
    )

    # AWS Configuration
    aws_auth_refresh: str | None = Field(
        None,
        alias="awsAuthRefresh",
        description="Command to refresh AWS credentials",
        min_length=1,
    )
    aws_credential_export: str | None = Field(
        None,
        alias="awsCredentialExport",
        description="Command to export AWS credentials as JSON",
        min_length=1,
    )

    # Interface & Output
    status_line: StatusLine | None = Field(
        None,
        alias="statusLine",
        description="Custom status line configuration",
    )
    output_style: str | None = Field(
        None,
        alias="outputStyle",
        description="The output style to use (case-sensitive)",
        min_length=1,
    )
    spinner_tips_enabled: bool | None = Field(
        None,
        alias="spinnerTipsEnabled",
        description="Whether to show tips in the spinner",
    )
    always_thinking_enabled: bool | None = Field(
        None,
        alias="alwaysThinkingEnabled",
        description="Whether extended thinking is always enabled",
    )

    model_config = {
        "extra": "allow",  # Allow additional properties per schema
        "populate_by_name": True,
    }

    @field_validator("env")
    @classmethod
    def validate_env_vars(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate environment variable names follow convention."""
        if v is not None:
            import re

            for key in v.keys():
                if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
                    raise ValueError(
                        f"Environment variable '{key}' must match pattern ^[A-Z_][A-Z0-9_]*$"
                    )
        return v

    @field_validator("hooks")
    @classmethod
    def validate_hook_events(
        cls, v: dict[str, list[HookMatcher]] | None
    ) -> dict[str, list[HookMatcher]] | None:
        """Validate hook event names."""
        if v is not None:
            valid_events = {e.value for e in HookEventName}
            for event_name in v.keys():
                if event_name not in valid_events:
                    raise ValueError(
                        f"Invalid hook event '{event_name}'. Must be one of: {', '.join(valid_events)}"
                    )
        return v

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON with proper field names."""
        return super().model_dump_json(by_alias=True, exclude_none=True, **kwargs)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize to dict with proper field names."""
        return super().model_dump(by_alias=True, exclude_none=True, **kwargs)
