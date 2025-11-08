# Environment Variables in Claude Code Hooks

Complete guide to managing environment variables in Claude Code hooks using QuickHooks' Pydantic Settings integration.

## Overview

QuickHooks provides a type-safe, validated approach to accessing environment variables in Claude Code hooks using `pydantic-settings`. This eliminates manual `os.getenv()` calls and provides proper typing, validation, and defaults.

## Quick Start

```python
from quickhooks.schema.hook_env import load_hook_env

# Load all environment variables
env = load_hook_env()

# Access variables with proper typing
if env.is_session_start:
    # Write environment variables to CLAUDE_ENV_FILE
    env.write_env_file({
        "NODE_ENV": "production",
        "API_KEY": "secret123"
    })

# Check if Groq API key is available
if env.has_groq_api_key:
    print(f"API key available: {env.groq_api_key[:10]}...")

# Get configuration with defaults
model = env.get_agent_model()  # Returns "qwen/qwen3-32b" if not set
threshold = env.get_confidence_threshold()  # Returns 0.7 if not set
```

## Core Models

### ClaudeCodeHookEnv

Main model for all Claude Code hook environment variables.

```python
from quickhooks.schema.hook_env import ClaudeCodeHookEnv

env = ClaudeCodeHookEnv()
```

**Fields:**

| Field | Type | Available In | Description |
|-------|------|--------------|-------------|
| `claude_env_file` | `Path \| None` | SessionStart only | Path to persist environment variables |
| `groq_api_key` | `str \| None` | All hooks | Groq API key for agent analysis |
| `anthropic_api_key` | `str \| None` | All hooks | Anthropic API key |
| `quickhooks_agent_analysis_enabled` | `bool \| None` | All hooks | Enable agent analysis |
| `quickhooks_agent_model` | `str \| None` | All hooks | Groq model name |
| `quickhooks_confidence_threshold` | `float \| None` | All hooks | Confidence threshold |
| `quickhooks_min_similarity` | `float \| None` | All hooks | Minimum similarity |
| `quickhooks_verbose` | `bool \| None` | All hooks | Enable verbose logging |
| `home` | `Path \| None` | All hooks | User home directory |
| `path` | `str \| None` | All hooks | System PATH |
| `shell` | `str \| None` | All hooks | Current shell |
| `user` | `str \| None` | All hooks | Current user |

**Properties:**

| Property | Returns | Description |
|----------|---------|-------------|
| `is_session_start` | `bool` | True if CLAUDE_ENV_FILE is available |
| `has_groq_api_key` | `bool` | True if Groq API key is set |
| `agent_analysis_enabled` | `bool` | True if agent analysis is enabled |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_agent_model()` | `str` | Get agent model with default |
| `get_confidence_threshold()` | `float` | Get threshold with default (0.7) |
| `get_min_similarity()` | `float` | Get similarity with default (0.3) |
| `is_verbose()` | `bool` | Check if verbose mode enabled |
| `to_dict()` | `dict` | Convert to dict (excludes None) |
| `write_env_file(exports)` | `bool` | Write vars to CLAUDE_ENV_FILE |
| `read_env_file()` | `dict` | Read vars from CLAUDE_ENV_FILE |

### QuickHooksSettings

Application-level settings separate from hook environment.

```python
from quickhooks.schema.hook_env import load_quickhooks_settings

settings = load_quickhooks_settings()
print(f"Hooks directory: {settings.hooks_directory}")
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_analysis_enabled` | `bool` | `True` | Enable agent analysis |
| `agent_model` | `str` | `"qwen/qwen3-32b"` | Groq model |
| `confidence_threshold` | `float` | `0.7` | Confidence threshold |
| `min_similarity` | `float` | `0.3` | Minimum similarity |
| `verbose` | `bool` | `False` | Verbose logging |
| `hooks_directory` | `Path` | `~/.quickhooks/hooks` | Hooks directory |
| `sessions_directory` | `Path` | `~/.quickhooks/sessions` | Sessions directory |
| `agent_db_path` | `Path` | `~/.quickhooks/agent_db` | Agent DB path |

All fields can be overridden with environment variables prefixed with `QUICKHOOKS_`, e.g.:
- `QUICKHOOKS_AGENT_MODEL=llama-3.3-70b-versatile`
- `QUICKHOOKS_VERBOSE=true`

## Environment Variables by Hook Type

### SessionStart Hook (Exclusive)

SessionStart is the ONLY hook type with access to `CLAUDE_ENV_FILE`.

```python
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()

if env.is_session_start:
    # Write environment variables that persist for the session
    env.write_env_file({
        "NODE_ENV": "production",
        "PYTHONPATH": "$PYTHONPATH:/project/src",
        "PATH": "$PATH:./node_modules/.bin"
    })
```

**Available Variables:**
- `CLAUDE_ENV_FILE` - Path to environment file
- All standard environment variables
- All QuickHooks configuration variables

### All Other Hooks

Other hook types (PreToolUse, PostToolUse, etc.) can read environment variables but cannot write to CLAUDE_ENV_FILE.

```python
env = load_hook_env()

# Check if we're in a SessionStart hook
if env.is_session_start:
    env.write_env_file({"KEY": "value"})
else:
    # Just read environment variables
    api_key = env.groq_api_key
```

## Usage Examples

### Example 1: SessionStart with Environment Setup

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from quickhooks.schema.hook_env import load_hook_env

def main():
    # Read hook input
    input_data = json.loads(sys.stdin.read())
    cwd = input_data.get("cwd", "")

    # Load environment
    env = load_hook_env()

    # Configure project environment
    if env.is_session_start:
        project_env = {}

        # Detect project type
        if (Path(cwd) / "package.json").exists():
            project_env["NODE_ENV"] = "development"
            project_env["PATH"] = f"$PATH:{cwd}/node_modules/.bin"

        if (Path(cwd) / "pyproject.toml").exists():
            project_env["PYTHONPATH"] = f"$PYTHONPATH:{cwd}/src"

        # Write to environment file
        if project_env:
            success = env.write_env_file(project_env)
            if success:
                print(f"Configured {len(project_env)} env vars", file=sys.stderr)

    # Return response
    response = {"continue": True}
    print(json.dumps(response))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Example 2: Agent Analysis with Environment Config

```python
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()

# Check if agent analysis is available
if env.has_groq_api_key and env.agent_analysis_enabled:
    from quickhooks.agent_analysis import AgentAnalyzer

    analyzer = AgentAnalyzer(
        groq_api_key=env.groq_api_key,
        model_name=env.get_agent_model(),
    )

    # Use analyzer...
else:
    print("Agent analysis not configured", file=sys.stderr)
```

### Example 3: Reading CLAUDE_ENV_FILE

```python
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()

# Read previously set environment variables
if env.is_session_start:
    existing_vars = env.read_env_file()
    print(f"Found {len(existing_vars)} existing environment variables")

    for key, value in existing_vars.items():
        print(f"  {key}={value}")
```

### Example 4: Conditional Configuration

```python
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()

# Configure based on environment
if env.is_verbose():
    print("Verbose mode enabled - detailed logging active")

# Use configuration with defaults
model = env.get_agent_model()
threshold = env.get_confidence_threshold()

print(f"Using model: {model} with threshold: {threshold}")
```

## Configuration Methods

### Via Environment Variables

Set environment variables before running hooks:

```bash
export GROQ_API_KEY=gsk_xxx
export QUICKHOOKS_AGENT_MODEL=llama-3.3-70b-versatile
export QUICKHOOKS_VERBOSE=true
```

### Via .claude/settings.json

Configure in Claude Code settings:

```json
{
  "env": {
    "GROQ_API_KEY": "gsk_xxx",
    "QUICKHOOKS_AGENT_MODEL": "llama-3.3-70b-versatile",
    "QUICKHOOKS_VERBOSE": "true"
  }
}
```

### Via CLAUDE_ENV_FILE (SessionStart only)

Persist variables for the entire session:

```python
env = load_hook_env()
env.write_env_file({
    "PROJECT_ROOT": "/path/to/project",
    "CUSTOM_CONFIG": "value"
})
```

## CLAUDE_ENV_FILE Deep Dive

### What Is It?

CLAUDE_ENV_FILE is a special environment variable available ONLY in SessionStart hooks that points to a file where you can persist environment variables for the entire Claude Code session.

### How It Works

1. SessionStart hook runs when session begins
2. Hook receives `CLAUDE_ENV_FILE` environment variable
3. Hook writes `export` statements to this file
4. Claude Code sources this file for all subsequent tool calls
5. Environment variables persist throughout the session

### Writing to CLAUDE_ENV_FILE

```python
env = load_hook_env()

if env.is_session_start:
    # Simple approach
    env.write_env_file({
        "API_KEY": "secret123",
        "NODE_ENV": "production"
    })

    # Manual approach
    with open(env.claude_env_file, "a") as f:
        f.write('export MY_VAR="value"\n')
```

### Reading from CLAUDE_ENV_FILE

```python
env = load_hook_env()

if env.is_session_start and env.claude_env_file.exists():
    vars = env.read_env_file()
    for key, value in vars.items():
        print(f"{key}={value}")
```

### Best Practices

1. **Use Absolute Paths**: Environment variables with paths should be absolute
2. **Escape Properly**: QuickHooks handles escaping automatically
3. **Check Existence**: Verify file exists before reading
4. **Append Only**: Always append (`>>` or mode `"a"`), never overwrite
5. **Session-Specific**: Variables persist only for current session

## Type Safety Benefits

### Before (Manual os.getenv)

```python
import os

# No type checking
api_key = os.getenv("GROQ_API_KEY")  # str | None
if api_key:  # Manual None check
    # Use api_key

# Manual parsing
threshold = float(os.getenv("THRESHOLD", "0.7"))

# Manual validation
verbose = os.getenv("VERBOSE", "false").lower() == "true"
```

### After (Pydantic Settings)

```python
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()

# Type-safe access
if env.has_groq_api_key:  # Property with clear intent
    api_key = env.groq_api_key  # Type: str (never None here)

# Automatic parsing
threshold = env.get_confidence_threshold()  # Type: float

# Automatic validation
verbose = env.is_verbose()  # Type: bool
```

## Troubleshooting

### CLAUDE_ENV_FILE Not Available

**Problem**: `env.claude_env_file` is None

**Solution**:
- Only available in SessionStart hooks
- Check `env.is_session_start` property
- Verify hook is configured as SessionStart type

### Environment Variables Not Persisting

**Problem**: Variables written to CLAUDE_ENV_FILE not available

**Solution**:
- Ensure using `env.write_env_file()` or append mode
- Check file exists: `env.claude_env_file.exists()`
- Verify export syntax: `export KEY="value"`
- Check Claude Code logs for errors

### Pydantic Settings Import Error

**Problem**: Cannot import `ClaudeCodeHookEnv`

**Solution**:
```bash
# Install pydantic-settings
pip install pydantic-settings>=2.10.1

# Or with QuickHooks
pip install quickhooks
```

### Type Validation Errors

**Problem**: Pydantic validation fails

**Solution**:
- Check environment variable format
- Verify types match (e.g., "true" for boolean)
- Use `extra="allow"` for custom variables

## Testing

### Test Environment Loading

```python
import os
from quickhooks.schema.hook_env import load_hook_env

# Set test environment variables
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["QUICKHOOKS_VERBOSE"] = "true"

# Load environment
env = load_hook_env()

# Verify
assert env.has_groq_api_key
assert env.groq_api_key == "test-key"
assert env.is_verbose()
```

### Test CLAUDE_ENV_FILE

```python
import tempfile
from pathlib import Path
from quickhooks.schema.hook_env import ClaudeCodeHookEnv

# Create temporary file
with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    env_file = Path(f.name)

# Set environment variable
os.environ["CLAUDE_ENV_FILE"] = str(env_file)

# Test writing
env = ClaudeCodeHookEnv()
success = env.write_env_file({"TEST_VAR": "value"})

assert success
assert env_file.exists()

# Test reading
vars = env.read_env_file()
assert "TEST_VAR" in vars
assert vars["TEST_VAR"] == "value"

# Cleanup
env_file.unlink()
```

## Migration Guide

### From Manual os.getenv

```python
# Old code
import os

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("API key not set")
    sys.exit(1)

model = os.getenv("MODEL", "qwen/qwen3-32b")
```

```python
# New code
from quickhooks.schema.hook_env import load_hook_env

env = load_hook_env()
if not env.has_groq_api_key:
    print("API key not set")
    sys.exit(1)

model = env.get_agent_model()  # Has default
```

### Benefits of Migration

1. **Type Safety**: Full IDE autocomplete and type checking
2. **Validation**: Automatic validation of values
3. **Defaults**: Built-in default values
4. **Documentation**: Self-documenting code
5. **Testing**: Easier to mock and test

## Resources

- Source Code: `src/quickhooks/schema/hook_env.py`
- Example Hook: `hooks/session_start_example.py`
- Pydantic Settings Docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Related Documentation

- [Session Hooks Guide](session-hooks.md)
- [Hook Development Guide](../HOOK_DEVELOPMENT_GUIDE.md)
- [Getting Started](getting-started.md)
