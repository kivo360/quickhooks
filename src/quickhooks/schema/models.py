"""Pydantic models for Claude Code hook configurations and validation."""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class HookCommand(BaseModel):
    """Model for a Claude Code hook command."""
    type: Literal["command"] = Field("command", description="Command type (only 'command' supported)")
    command: str = Field(..., description="The shell command to execute")
    timeout: Optional[int] = Field(None, gt=0, description="Timeout in seconds (must be > 0)")

    class Config:
        extra = "forbid"  # Don't allow extra fields like 'description'


class HookMatcher(BaseModel):
    """Model for a Claude Code hook matcher configuration."""
    matcher: Optional[str] = Field(None, description="Pattern to match tool names (regex string)")
    hooks: List[HookCommand] = Field(..., min_items=1, description="Array of hook commands")

    class Config:
        extra = "forbid"


class HookInput(BaseModel):
    """Model for Claude Code hook input (stdin)."""
    session_id: str = Field(..., description="Unique session identifier")
    transcript_path: str = Field(..., description="Path to conversation transcript")
    cwd: str = Field(..., description="Current working directory")
    hook_event_name: str = Field(..., description="Name of the hook event")
    tool_name: str = Field(..., description="Name of the tool being used")
    tool_input: Dict[str, Any] = Field(..., description="Input parameters for the tool")

    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class HookResponse(BaseModel):
    """Model for Claude Code hook response (stdout)."""
    continue_: bool = Field(True, alias="continue", description="Whether Claude should continue")
    suppress_output: Optional[bool] = Field(None, alias="suppressOutput", description="Hide stdout from transcript")
    stop_reason: Optional[str] = Field(None, alias="stopReason", description="Reason when continue=false")

    class Config:
        extra = "allow"  # Allow additional hook-specific fields
        allow_population_by_field_name = True


class PreToolUseResponse(HookResponse):
    """Extended response model for PreToolUse hooks."""
    permission_decision: Optional[Literal["allow", "deny", "ask"]] = Field(
        None, alias="permissionDecision", description="Permission decision for the tool call"
    )
    permission_decision_reason: Optional[str] = Field(
        None, alias="permissionDecisionReason", description="Reason for permission decision"
    )

    class Config:
        extra = "allow"
        populate_by_name = True


class PostToolUseResponse(HookResponse):
    """Extended response model for PostToolUse hooks."""
    decision: Optional[Literal["block"]] = Field(None, description="Whether to block with feedback")
    reason: Optional[str] = Field(None, description="Reason for blocking (required if decision='block')")

    @model_validator(mode='after')
    def validate_block_reason(self):
        """Ensure reason is provided when decision is 'block'."""
        if self.decision == 'block' and not self.reason:
            raise ValueError("'reason' is required when decision='block'")
        return self


class UserPromptSubmitResponse(HookResponse):
    """Extended response model for UserPromptSubmit hooks."""
    decision: Optional[Literal["block"]] = Field(None, description="Whether to block prompt processing")
    reason: Optional[str] = Field(None, description="Reason for blocking")
    additional_context: Optional[str] = Field(None, description="Context to add to the prompt")

    class Config:
        extra = "allow"
        populate_by_name = True


class ClaudeSettings(BaseModel):
    """Model for Claude Code settings.json file."""
    schema_: Optional[str] = Field(None, alias="$schema", description="JSON schema reference")
    api_key_helper: Optional[str] = Field(None, alias="apiKeyHelper", description="API key helper command")
    cleanup_period_days: Optional[int] = Field(30, alias="cleanupPeriodDays", ge=0, description="Cleanup period in days")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    hooks: Optional[Dict[str, List[HookMatcher]]] = Field(None, description="Hook configurations")
    include_co_authored_by: Optional[bool] = Field(False, alias="includeCoAuthoredBy", description="Include co-authored-by")
    model: Optional[Literal["haiku", "sonnet", "opus"]] = Field("sonnet", description="Model to use")
    permissions: Optional[Dict[str, List[str]]] = Field(None, description="Tool permissions")

    @field_validator('env', mode='before')
    @classmethod
    def validate_env_keys(cls, v):
        """Validate environment variable keys follow naming convention."""
        if v is None:
            return v
        
        for key in v.keys():
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                raise ValueError(f"Environment variable key '{key}' must follow pattern ^[A-Z_][A-Z0-9_]*$")
        
        return v

    @field_validator('hooks')
    @classmethod
    def validate_hook_types(cls, v):
        """Validate hook event names are supported."""
        if v is None:
            return v
        
        valid_hook_types = {
            "PreToolUse", "PostToolUse", "Notification", "UserPromptSubmit",
            "Stop", "SubagentStop", "PreCompact"
        }
        
        for hook_type in v.keys():
            if hook_type not in valid_hook_types:
                raise ValueError(f"Hook type '{hook_type}' is not supported. Valid types: {valid_hook_types}")
        
        return v

    class Config:
        extra = "allow"  # Allow additional fields for extensibility
        populate_by_name = True


class ValidatedClaudeSettings(ClaudeSettings):
    """Claude settings with strict validation against the official schema."""
    
    class Config:
        extra = "forbid"  # Strict mode - no extra fields allowed


def create_context_portal_hook_config(
    tools: List[str], 
    command: str, 
    timeout: Optional[int] = 30
) -> Dict[str, List[HookMatcher]]:
    """
    Create a validated Context Portal hook configuration.
    
    Args:
        tools: List of tools to match
        command: Command to execute
        timeout: Optional timeout in seconds
        
    Returns:
        Validated hook configuration
    """
    # Validate tools against known valid tools
    valid_tools = {
        "Agent", "Bash", "Edit", "Glob", "Grep", "LS", "MultiEdit",
        "NotebookEdit", "NotebookRead", "Read", "Task", "TodoRead", "TodoWrite",
        "WebFetch", "WebSearch", "Write"
    }
    
    invalid_tools = set(tools) - valid_tools
    if invalid_tools:
        raise ValueError(f"Invalid tools: {invalid_tools}. Valid tools: {valid_tools}")
    
    # Create matcher pattern
    if len(tools) == 1:
        matcher = tools[0]
    elif len(tools) == len(valid_tools):
        matcher = "*"
    else:
        matcher = "|".join(tools)
    
    # Create hook command
    hook_command = HookCommand(
        type="command",
        command=command,
        timeout=timeout
    )
    
    # Create hook matcher
    hook_matcher = HookMatcher(
        matcher=matcher,
        hooks=[hook_command]
    )
    
    return {"PreToolUse": [hook_matcher.model_dump()]}


def validate_hook_input(data: Dict[str, Any]) -> HookInput:
    """
    Validate and parse hook input data.
    
    Args:
        data: Raw input data dictionary
        
    Returns:
        Validated HookInput instance
        
    Raises:
        ValidationError: If input data is invalid
    """
    return HookInput(**data)


def create_hook_response(
    continue_execution: bool = True,
    suppress_output: bool = False,
    stop_reason: Optional[str] = None,
    **kwargs
) -> HookResponse:
    """
    Create a validated hook response.
    
    Args:
        continue_execution: Whether execution should continue
        suppress_output: Whether to suppress output
        stop_reason: Reason for stopping (if continue_execution=False)
        **kwargs: Additional hook-specific fields
        
    Returns:
        Validated HookResponse instance
    """
    return HookResponse(
        **{"continue": continue_execution},
        suppressOutput=suppress_output,
        stopReason=stop_reason,
        **kwargs
    )


def validate_settings_file(settings_path: str) -> ClaudeSettings:
    """
    Validate a Claude Code settings file.
    
    Args:
        settings_path: Path to the settings.json file
        
    Returns:
        Validated ClaudeSettings instance
        
    Raises:
        ValidationError: If settings are invalid
        FileNotFoundError: If file doesn't exist
    """
    import json
    from pathlib import Path
    
    path = Path(settings_path)
    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return ClaudeSettings(**data)