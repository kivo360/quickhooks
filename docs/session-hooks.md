# SessionStart and SessionEnd Hooks

Complete guide to using SessionStart and SessionEnd hooks in Claude Code with QuickHooks.

## Overview

Claude Code now supports two additional lifecycle hooks for session management:

- **SessionStart**: Runs when a session starts or resumes
- **SessionEnd**: Runs when a session ends

These hooks enable powerful initialization and cleanup workflows.

## SessionStart Hook

### When It Runs

The SessionStart hook executes when:
- A new Claude Code session is created
- An existing session is resumed
- A previous session is restored

### Key Features

1. **Exclusive Environment Variable Access**
   - Only hook with access to `CLAUDE_ENV_FILE`
   - Can read environment configuration file

2. **Context Injection**
   - Output (stdout) is added as context for Claude
   - Perfect for loading project information
   - Can inject custom instructions or configurations

3. **Source Detection**
   - Receives `source` field indicating session type:
     - `"new"` - Brand new session
     - `"resume"` - Resuming existing session
     - `"restore"` - Restoring from backup/history

### Input Format

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.json",
  "cwd": "/project/directory",
  "hook_event_name": "SessionStart",
  "source": "new"
}
```

### Output Format

```json
{
  "continue": true,
  "additionalContext": "Custom context to inject for Claude"
}
```

### Use Cases

1. **Project Initialization**
   - Load project configuration
   - Read README or project documentation
   - Inject coding standards or guidelines

2. **Environment Setup**
   - Load environment variables from CLAUDE_ENV_FILE
   - Configure project-specific settings
   - Set up development tools

3. **Context Loading**
   - Load recent decisions or architecture notes
   - Inject project-specific knowledge
   - Provide session-specific instructions

### Example Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.quickhooks/hooks/session_start_example.py"
          }
        ]
      }
    ]
  }
}
```

### Example Implementation

See `hooks/session_start_example.py` for a complete working example that:
- Detects project type (Node.js, Python, etc.)
- Loads project metadata
- Injects welcome context
- Reads CLAUDE_ENV_FILE if available

## SessionEnd Hook

### When It Runs

The SessionEnd hook executes when a Claude Code session terminates.

### Key Features

1. **Debug-Only Logging**
   - Output logged to debug only (use `--debug` flag)
   - Won't clutter normal transcript
   - Perfect for analytics and cleanup

2. **Cleanup Operations**
   - Remove temporary files
   - Save session state
   - Archive logs

3. **Session Analytics**
   - Calculate session metrics
   - Track usage patterns
   - Generate reports

### Input Format

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.json",
  "cwd": "/project/directory",
  "hook_event_name": "SessionEnd"
}
```

### Output Format

```json
{
  "continue": true
}
```

### Use Cases

1. **State Persistence**
   - Save session metadata
   - Archive conversation history
   - Store session metrics

2. **Cleanup**
   - Remove temporary files
   - Clear caches
   - Reset configurations

3. **Analytics**
   - Track session duration
   - Log tools used
   - Generate usage reports

4. **Backups**
   - Archive important decisions
   - Save modified files list
   - Export session summary

### Example Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.quickhooks/hooks/session_end_example.py"
          }
        ]
      }
    ]
  }
}
```

### Example Implementation

See `hooks/session_end_example.py` for a complete working example that:
- Saves session metadata
- Calculates session metrics
- Performs cleanup
- Archives logs

## Complete Hook Event Types

QuickHooks now supports all 9 Claude Code hook events:

| Hook Event | When It Runs | Output Routing | Use Case |
|------------|--------------|----------------|----------|
| **PreToolUse** | Before tool calls | Transcript | Permission gating |
| **PostToolUse** | After tool completion | Transcript | Validation |
| **UserPromptSubmit** | User submits prompt | Context | Prompt modification |
| **Stop** | Agent finishes | Transcript | Pre-commit checks |
| **SubagentStop** | Subagent finishes | Transcript | Subagent cleanup |
| **Notification** | System notifications | Debug only | Event handling |
| **PreCompact** | Before compaction | Transcript | Context preservation |
| **SessionStart** ⭐ | Session starts | Context | Initialization |
| **SessionEnd** ⭐ | Session ends | Debug only | Cleanup |

## Best Practices

### SessionStart

1. **Keep It Fast**
   - Minimize initialization time
   - Load only essential context
   - Avoid heavy computations

2. **Provide Useful Context**
   - Include project overview
   - Add relevant guidelines
   - Inject recent decisions

3. **Handle Errors Gracefully**
   - Don't block session start on minor errors
   - Log issues to stderr
   - Provide fallback behavior

### SessionEnd

1. **Don't Block**
   - Exit cleanly even on errors
   - Use `continue: true` by default
   - Save critical data first

2. **Log Appropriately**
   - Use stderr for debug info
   - Save detailed logs to files
   - Don't spam console

3. **Cleanup Safely**
   - Check before deleting
   - Archive before removing
   - Handle missing files gracefully

## Migration Guide

### Upgrading from Previous Versions

If you're using an older version of QuickHooks, update your schema:

1. **Update QuickHooks**
   ```bash
   pip install --upgrade quickhooks
   ```

2. **Verify Schema**
   Your `.claude/settings.json` can now include:
   ```json
   {
     "hooks": {
       "SessionStart": [...],
       "SessionEnd": [...]
     }
   }
   ```

3. **Test Hooks**
   ```bash
   # Test SessionStart
   echo '{"session_id":"test","transcript_path":"","cwd":"'$(pwd)'","hook_event_name":"SessionStart","source":"new"}' | python hooks/session_start_example.py

   # Test SessionEnd
   echo '{"session_id":"test","transcript_path":"","cwd":"'$(pwd)'","hook_event_name":"SessionEnd"}' | python hooks/session_end_example.py
   ```

## Troubleshooting

### SessionStart Hook Not Running

- Check `.claude/settings.json` syntax
- Verify hook script is executable
- Test hook manually with sample input
- Check logs with `--debug` flag

### SessionEnd Hook Not Visible

- SessionEnd output goes to debug logs only
- Use `claude --debug` to see output
- Check stderr for error messages
- Verify hook doesn't exit with error code

### Context Not Injected

- Ensure `additionalContext` field is set
- Check output is valid JSON
- Verify hook exits with code 0
- Test with `--debug` flag

## Advanced Examples

### Multi-Project Context Loading

```python
# Detect and load context based on project type
if is_python_project(cwd):
    context = load_python_context()
elif is_nodejs_project(cwd):
    context = load_nodejs_context()
elif is_rust_project(cwd):
    context = load_rust_context()
```

### Session Metrics Dashboard

```python
# Save session metrics for analytics
metrics = {
    "duration": calculate_duration(),
    "tools_used": count_tools(),
    "files_modified": count_modifications(),
}
save_to_database(metrics)
```

### Environment Configuration

```python
# Load environment from CLAUDE_ENV_FILE (SessionStart only)
env_file = os.getenv("CLAUDE_ENV_FILE")
if env_file and Path(env_file).exists():
    config = load_env_config(env_file)
    inject_config_context(config)
```

## Resources

- Example SessionStart Hook: `hooks/session_start_example.py`
- Example SessionEnd Hook: `hooks/session_end_example.py`
- Schema Definition: `src/quickhooks/schema/claude_settings_schema.json`
- Response Models: `src/quickhooks/schema/models.py`

## Related Documentation

- [Hook Development Guide](../HOOK_DEVELOPMENT_GUIDE.md)
- [Getting Started](getting-started.md)
- [Claude Code Hooks Reference](https://docs.claude.com/en/docs/claude-code/hooks)
