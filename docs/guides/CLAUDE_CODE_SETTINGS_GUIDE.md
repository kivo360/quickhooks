# Claude Code Settings Management Guide

Complete guide for managing Claude Code settings.json files with QuickHooks utilities.

## Table of Contents

- [Overview](#overview)
- [Schema Compliance](#schema-compliance)
- [Pydantic Models](#pydantic-models)
- [Settings Manager](#settings-manager)
- [CLI Commands](#cli-commands)
- [Hook Configuration](#hook-configuration)
- [Examples](#examples)
- [API Reference](#api-reference)

## Overview

QuickHooks provides comprehensive tools for managing Claude Code `settings.json` files:

- **Pydantic Models**: Type-safe settings with validation
- **SettingsManager**: High-level API for reading/writing settings
- **CLI Commands**: Easy command-line management
- **Schema Validation**: Ensures compliance with official schema

## Schema Compliance

All tools follow the official Claude Code settings schema from:
```
https://json.schemastore.org/claude-code-settings.json
```

**Schema file location**: `.claude/settings_schema.json`

### Correct Settings Format

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "ANTHROPIC_MODEL": "claude-opus-4-1"
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/my_hook.py"
          }
        ]
      }
    ]
  }
}
```

### Hook Events

Valid hook event names (case-sensitive):

| Event | Description |
|-------|-------------|
| `PreToolUse` | Before tool calls |
| `PostToolUse` | After tool completion |
| `Notification` | On notifications |
| `UserPromptSubmit` | When user submits prompt |
| `Stop` | When agents finish responding |
| `SubagentStop` | When subagents finish |
| `PreCompact` | Before context compaction |
| `SessionStart` | When session starts |
| `SessionEnd` | When session ends |

## Pydantic Models

Type-safe models for settings validation.

### Basic Usage

```python
from quickhooks.claude_code import ClaudeCodeSettings, HookCommand, HookMatcher

# Create settings
settings = ClaudeCodeSettings(
    schema_="https://json.schemastore.org/claude-code-settings.json",
    env={"ANTHROPIC_MODEL": "claude-opus-4-1"},
    hooks={
        "UserPromptSubmit": [
            HookMatcher(
                hooks=[
                    HookCommand(
                        type="command",
                        command=".claude/hooks/my_hook.py"
                    )
                ]
            )
        ]
    }
)

# Serialize to JSON
json_str = settings.model_dump_json(indent=2)

# Validate from dict
data = {"env": {"ANTHROPIC_MODEL": "claude-opus-4-1"}}
settings = ClaudeCodeSettings.model_validate(data)
```

### Available Models

**ClaudeCodeSettings**: Main settings model
```python
class ClaudeCodeSettings(BaseModel):
    schema_: str | None  # $schema field
    env: dict[str, str] | None  # Environment variables
    hooks: dict[str, list[HookMatcher]] | None  # Hooks configuration
    permissions: Permissions | None  # Tool permissions
    # ... many more fields
```

**HookCommand**: Individual hook command
```python
class HookCommand(BaseModel):
    type: Literal["command"] = "command"
    command: str  # Command to execute
    timeout: float | None  # Optional timeout
```

**HookMatcher**: Hook matcher with pattern
```python
class HookMatcher(BaseModel):
    matcher: str | None  # Tool name pattern
    hooks: list[HookCommand]  # Commands to execute
```

**Permissions**: Tool permissions
```python
class Permissions(BaseModel):
    allow: list[str] | None
    ask: list[str] | None
    deny: list[str] | None
    default_mode: PermissionMode | None
    additional_directories: list[str] | None
```

## Settings Manager

High-level API for settings manipulation.

### Basic Operations

```python
from quickhooks.claude_code import SettingsManager, HookCommand, HookEventName

# Initialize manager
manager = SettingsManager(".claude/settings.json")

# Load settings
settings = manager.load()

# Load with creation if missing
settings = manager.load(create_if_missing=True)

# Save settings
manager.save()

# Validate against schema
manager.validate_schema()

# Convert to dict/JSON
data = manager.to_dict()
json_str = manager.to_json(indent=2)
```

### Hook Management

```python
# Add a hook
manager.add_hook(
    HookEventName.USER_PROMPT_SUBMIT,
    HookCommand(
        type="command",
        command=".claude/hooks/my_hook.py",
        timeout=30
    ),
    matcher="Edit|Write"  # Optional tool matcher
)

# Remove hooks
removed = manager.remove_hook(
    HookEventName.USER_PROMPT_SUBMIT,
    command_pattern="my_hook.py"
)

# List hooks
all_hooks = manager.list_hooks()
user_prompt_hooks = manager.list_hooks(HookEventName.USER_PROMPT_SUBMIT)
```

### Environment Variables

```python
# Set environment variable
manager.set_env("ANTHROPIC_MODEL", "claude-opus-4-1")

# Get environment variable
model = manager.get_env("ANTHROPIC_MODEL", default="claude-sonnet-4-1")

# Remove environment variable
removed = manager.remove_env("ANTHROPIC_MODEL")

# List all environment variables
env_vars = manager.list_env()
```

### Permissions

```python
# Add permission rules
manager.add_permission("allow", "Bash(git add:*)")
manager.add_permission("ask", "Bash(git commit:*)")
manager.add_permission("deny", "Read(*.env)")

# Remove permission
removed = manager.remove_permission("deny", "Read(*.env)")
```

## CLI Commands

Convenient command-line interface for settings management.

### Initialize Settings

```bash
# Create new settings.json
quickhooks settings init

# Create at custom path
quickhooks settings init --path /path/to/settings.json

# Force overwrite existing
quickhooks settings init --force
```

### Validate Settings

```bash
# Validate settings file
quickhooks settings validate

# Validate custom path
quickhooks settings validate --path /path/to/settings.json
```

### View Settings

```bash
# Display current settings
quickhooks settings show

# Show custom path
quickhooks settings show --path /path/to/settings.json
```

### Manage Hooks

```bash
# Add hook
quickhooks settings add-hook UserPromptSubmit ".claude/hooks/my_hook.py"

# Add with matcher and timeout
quickhooks settings add-hook PostToolUse "prettier --write" \
  --matcher "Edit|Write" \
  --timeout 5

# Remove hook
quickhooks settings remove-hook UserPromptSubmit "my_hook.py"

# List all hooks
quickhooks settings list-hooks

# List hooks for specific event
quickhooks settings list-hooks --event UserPromptSubmit
```

### Manage Environment Variables

```bash
# Set environment variable
quickhooks settings set-env ANTHROPIC_MODEL claude-opus-4-1

# List all environment variables
quickhooks settings list-env
```

### Manage Permissions

```bash
# Add permission
quickhooks settings add-permission allow "Bash(git add:*)"
quickhooks settings add-permission deny "Read(*.env)"
```

## Hook Configuration

### PEP 723 Hooks

QuickHooks provides self-contained PEP 723 hooks:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/example_hook_pep723.py"
          }
        ]
      }
    ]
  }
}
```

### Multiple Hooks per Event

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "eslint --fix"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "shellcheck"
          }
        ]
      }
    ]
  }
}
```

### Disabling Hooks

```json
{
  "disableAllHooks": true
}
```

## Examples

### Complete Settings File

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "ANTHROPIC_MODEL": "claude-opus-4-1",
    "ANTHROPIC_SMALL_FAST_MODEL": "claude-3-5-haiku-latest",
    "GROQ_API_KEY": "your_api_key_here"
  },
  "cleanupPeriodDays": 60,
  "permissions": {
    "allow": [
      "Bash(git add:*)",
      "Bash(git status:*)"
    ],
    "ask": [
      "Bash(git commit:*)",
      "Bash(gh pr create:*)"
    ],
    "deny": [
      "Read(*.env)",
      "Read(~/.ssh/*)",
      "Bash(rm:*)"
    ],
    "defaultMode": "default",
    "additionalDirectories": [
      "~/Documents",
      "~/projects"
    ]
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/agent_analysis_hook_pep723.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/context_portal_hook_pep723.py"
          }
        ]
      }
    ]
  },
  "includeCoAuthoredBy": true,
  "spinnerTipsEnabled": true
}
```

### Programmatic Management

```python
from quickhooks.claude_code import SettingsManager, HookCommand, HookEventName

# Load or create settings
manager = SettingsManager(".claude/settings.json")
manager.load(create_if_missing=True)

# Configure environment
manager.set_env("ANTHROPIC_MODEL", "claude-opus-4-1")
manager.set_env("GROQ_API_KEY", "your_api_key_here")

# Add hooks
manager.add_hook(
    HookEventName.USER_PROMPT_SUBMIT,
    HookCommand(
        type="command",
        command=".claude/hooks/agent_analysis_hook_pep723.py"
    )
)

manager.add_hook(
    HookEventName.POST_TOOL_USE,
    HookCommand(
        type="command",
        command="prettier --write",
        timeout=5
    ),
    matcher="Edit|Write"
)

# Add permissions
manager.add_permission("allow", "Bash(git add:*)")
manager.add_permission("ask", "Bash(git commit:*)")
manager.add_permission("deny", "Read(*.env)")

# Save changes
manager.save()

print("✅ Settings configured successfully!")
```

## API Reference

### ClaudeCodeSettings

Main settings model with full validation.

**Fields**:
- `schema_` (str | None): Schema URL
- `env` (dict[str, str] | None): Environment variables
- `hooks` (dict[str, list[HookMatcher]] | None): Hooks configuration
- `permissions` (Permissions | None): Tool permissions
- `cleanup_period_days` (int | None): Transcript retention days
- `enable_all_project_mcp_servers` (bool | None): Auto-approve MCP servers
- `disable_all_hooks` (bool | None): Disable all hooks
- `force_login_method` (LoginMethod | None): Force login method
- `status_line` (StatusLine | None): Custom status line
- `output_style` (str | None): Output style
- `spinner_tips_enabled` (bool | None): Show tips in spinner
- `always_thinking_enabled` (bool | None): Extended thinking mode

**Methods**:
- `model_dump()`: Serialize to dict
- `model_dump_json()`: Serialize to JSON
- `model_validate(data)`: Validate and create from dict

### SettingsManager

High-level settings management API.

**Constructor**:
```python
SettingsManager(settings_path: str | Path)
```

**Methods**:
- `load(create_if_missing=False)`: Load settings
- `save(indent=2)`: Save to file
- `validate_schema(schema_path=None)`: Validate against schema
- `add_hook(event, command, matcher=None)`: Add hook
- `remove_hook(event, command_pattern, matcher=None)`: Remove hook
- `list_hooks(event=None)`: List hooks
- `set_env(key, value)`: Set environment variable
- `get_env(key, default=None)`: Get environment variable
- `remove_env(key)`: Remove environment variable
- `list_env()`: List all environment variables
- `add_permission(type, rule, mode=None)`: Add permission
- `remove_permission(type, rule)`: Remove permission
- `to_dict()`: Convert to dict
- `to_json(indent=2)`: Convert to JSON

**Class Methods**:
- `from_dict(data, settings_path)`: Create from dict
- `from_json(json_str, settings_path)`: Create from JSON

### Enums

**HookEventName**: Valid hook event names
- `PRE_TOOL_USE = "PreToolUse"`
- `POST_TOOL_USE = "PostToolUse"`
- `NOTIFICATION = "Notification"`
- `USER_PROMPT_SUBMIT = "UserPromptSubmit"`
- `STOP = "Stop"`
- `SUBAGENT_STOP = "SubagentStop"`
- `PRE_COMPACT = "PreCompact"`
- `SESSION_START = "SessionStart"`
- `SESSION_END = "SessionEnd"`

**PermissionMode**: Permission execution modes
- `ACCEPT_EDITS = "acceptEdits"`
- `BYPASS_PERMISSIONS = "bypassPermissions"`
- `DEFAULT = "default"`
- `PLAN = "plan"`

**LoginMethod**: Available login methods
- `CLAUDE_AI = "claudeai"`
- `CONSOLE = "console"`

## Troubleshooting

### Validation Errors

If validation fails, check:

1. **Schema compliance**: Ensure using correct schema URL
2. **Environment variable names**: Must match `^[A-Z_][A-Z0-9_]*$`
3. **Hook event names**: Must use exact PascalCase names
4. **Hook structure**: Must use array of HookMatcher objects

### Permission Rules

Permission rules must match pattern:
```
^((Tool)(\\(pattern\\))?|mcp__.*)$
```

Examples:
- `Bash(git commit:*)`
- `Edit(/src/**/*.ts)`
- `Read(*.env)`
- `WebFetch(domain:github.com)`
- `mcp__github__search_repositories`

### Common Issues

**Issue**: Settings not loading

**Solution**:
```bash
# Validate JSON syntax
python3 -c "import json; print(json.load(open('.claude/settings.json')))"

# Validate with quickhooks
quickhooks settings validate
```

**Issue**: Hooks not executing

**Solution**:
1. Check `disableAllHooks` is not `true`
2. Verify hook file exists and is executable
3. Check hook event name is correct
4. Test hook manually: `echo '{}' | .claude/hooks/my_hook.py`

## Additional Resources

- [Official Claude Code Settings Schema](https://json.schemastore.org/claude-code-settings.json)
- [PEP 723 Hooks Guide](PEP723_HOOKS_GUIDE.md)
- [QuickHooks README](README.md)
- [UV Development Guide](docs/uv-guide.md)

## License

MIT - See LICENSE file for details
