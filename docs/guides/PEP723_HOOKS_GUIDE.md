# QuickHooks PEP 723 Claude Code Integration Guide

Complete guide for setting up self-contained Claude Code hooks using PEP 723 inline script metadata and UV.

## Table of Contents

- [What is PEP 723?](#what-is-pep-723)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Hook Configuration](#hook-configuration)
- [Available Hooks](#available-hooks)
- [Creating Custom Hooks](#creating-custom-hooks)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## What is PEP 723?

[PEP 723](https://peps.python.org/pep-0723/) is the Python standard for **inline script metadata**. It allows Python scripts to declare their dependencies directly within the script using a special comment format:

```python
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
#   "groq>=0.13.0",
# ]
# requires-python = ">=3.12"
# ///
```

### Benefits for Claude Code Hooks

1. **Self-Contained**: Each hook is a single file with all dependencies declared
2. **No Installation**: Dependencies install automatically from PyPI on first run
3. **Fast Execution**: UV caches dependencies for instant subsequent runs
4. **Portable**: Works anywhere UV is installed
5. **Version Controlled**: Dependency versions are in the script itself

## Quick Start

### 1. Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### 2. Install Hooks

Using the setup script:

```bash
# Install hooks to current project
uv run -s scripts/setup_pep723_hooks.py install

# Install to specific directory
uv run -s scripts/setup_pep723_hooks.py install --target /path/to/project
```

Or manually:

```bash
# Create hooks directory
mkdir -p .claude/hooks

# Copy hook files
cp /path/to/quickhooks/.claude/hooks/*_pep723.py .claude/hooks/
cp /path/to/quickhooks/.claude/settings.json .claude/

# Make hooks executable
chmod +x .claude/hooks/*.py
```

### 3. Configure Environment

Edit `.claude/settings.json` and set environment variables:

```json
{
  "environment": {
    "GROQ_API_KEY": "your_groq_api_key_here",
    "QUICKHOOKS_VERBOSE": "false"
  }
}
```

### 4. Enable Hooks

In `.claude/settings.json`, set `enabled: true` for desired hooks:

```json
{
  "hooks": {
    "example-hook": {
      "command": ".claude/hooks/example_hook_pep723.py",
      "enabled": true
    }
  }
}
```

### 5. Test

```bash
# Test manually
echo '{"session_id": "test", "prompt": "Hello"}' | .claude/hooks/example_hook_pep723.py

# Use setup script
uv run -s scripts/setup_pep723_hooks.py test
```

## Installation

### Prerequisites

- **Python 3.12+**: Required for all hooks
- **UV**: Package manager for running PEP 723 scripts
- **Groq API Key**: Required only for agent analysis hook

### Automated Installation

The setup script handles everything:

```bash
# Check requirements
uv run -s scripts/setup_pep723_hooks.py check

# Install to current directory
uv run -s scripts/setup_pep723_hooks.py install

# Install with specific target
uv run -s scripts/setup_pep723_hooks.py install --target ~/my-project

# Skip requirements check
uv run -s scripts/setup_pep723_hooks.py install --skip-check
```

### Manual Installation

1. **Create directory structure**:
   ```bash
   mkdir -p .claude/hooks
   ```

2. **Copy hook files**:
   ```bash
   cp /path/to/quickhooks/.claude/hooks/*_pep723.py .claude/hooks/
   chmod +x .claude/hooks/*.py
   ```

3. **Copy settings template**:
   ```bash
   cp /path/to/quickhooks/.claude/settings.json .claude/
   ```

4. **Configure settings**:
   - Edit `.claude/settings.json`
   - Set environment variables
   - Enable desired hooks

## Hook Configuration

### Settings Format

`.claude/settings.json` structure:

```json
{
  "name": "QuickHooks PEP 723 Integration",
  "version": "0.1.1",
  "hooks": {
    "hook-name": {
      "command": ".claude/hooks/hook_script.py",
      "enabled": true,
      "description": "Hook description"
    }
  },
  "environment": {
    "ENV_VAR_NAME": "value"
  }
}
```

### Environment Variables

Common environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | Groq API key (required for agent analysis) |
| `QUICKHOOKS_VERBOSE` | `false` | Enable verbose logging |
| `QUICKHOOKS_AGENT_ANALYSIS_ENABLED` | `true` | Enable/disable agent analysis |
| `QUICKHOOKS_AGENT_MODEL` | `qwen/qwen3-32b` | Groq model to use |
| `QUICKHOOKS_CONFIDENCE_THRESHOLD` | `0.7` | Confidence threshold (0.0-1.0) |
| `QUICKHOOKS_CONTEXT_PORTAL_ENABLED` | `true` | Enable/disable context portal |
| `QUICKHOOKS_CONTEXT_DB_PATH` | `~/.quickhooks/context_db` | Context database path |

## Available Hooks

### 1. Example Hook (`example_hook_pep723.py`)

**Purpose**: Minimal example demonstrating PEP 723 pattern

**Dependencies**: None (demonstrates zero-dependency setup)

**Configuration**:
```json
{
  "hooks": {
    "example-hook": {
      "command": ".claude/hooks/example_hook_pep723.py",
      "enabled": true
    }
  }
}
```

**Features**:
- Minimal overhead
- No external dependencies
- Instant execution
- Good starting point for custom hooks

### 2. Agent Analysis Hook (`agent_analysis_hook_pep723.py`)

**Purpose**: AI-powered agent discovery and prompt modification

**Dependencies**:
- `quickhooks>=0.1.0`
- `groq>=0.13.0`
- `pydantic-ai-slim[groq]>=0.0.49`
- `chromadb>=0.4.0`
- `sentence-transformers>=2.2.0`

**Configuration**:
```json
{
  "hooks": {
    "agent-analysis-hook": {
      "command": ".claude/hooks/agent_analysis_hook_pep723.py",
      "enabled": true
    }
  },
  "environment": {
    "GROQ_API_KEY": "your_api_key_here",
    "QUICKHOOKS_AGENT_ANALYSIS_ENABLED": "true",
    "QUICKHOOKS_AGENT_MODEL": "qwen/qwen3-32b",
    "QUICKHOOKS_CONFIDENCE_THRESHOLD": "0.7"
  }
}
```

**Features**:
- Automatic agent discovery from `~/.claude/agents`
- Semantic similarity matching
- Smart prompt modification
- Context-aware analysis

**First Run**: Downloads ~3GB of dependencies (CUDA, PyTorch, etc.). Subsequent runs are instant.

### 3. Context Portal Hook (`context_portal_hook_pep723.py`)

**Purpose**: Persistent memory and context management

**Dependencies**:
- `quickhooks>=0.1.0`

**Configuration**:
```json
{
  "hooks": {
    "context-portal-hook": {
      "command": ".claude/hooks/context_portal_hook_pep723.py",
      "enabled": true
    }
  },
  "environment": {
    "QUICKHOOKS_CONTEXT_PORTAL_ENABLED": "true",
    "QUICKHOOKS_CONTEXT_DB_PATH": "~/.quickhooks/context_db"
  }
}
```

**Features**:
- Stores conversation context
- Retrieves relevant context for new prompts
- Maintains conversation continuity
- Project-specific knowledge tracking

## Creating Custom Hooks

### Template

```python
#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#   "package-name>=1.0.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Your hook description.

Configuration via environment variables:
- YOUR_VAR: Description
"""

import json
import sys
from typing import Any


def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process Claude Code hook event.

    Args:
        event_data: Event data from Claude Code with fields:
            - session_id: Current session identifier
            - tool_name: Name of the tool being invoked
            - tool_input: Input parameters for the tool
            - hook_event_name: Name of the hook event
            - transcript_path: Path to conversation transcript
            - cwd: Current working directory
            - prompt: User prompt (for prompt hooks)
            - context: Additional context

    Returns:
        Response dict with:
            - continue: Whether to continue tool execution (default: True)
            - suppressOutput: Whether to suppress tool output (default: False)
            - message: Optional message to display to user
    """
    # Your logic here
    session_id = event_data.get("session_id", "unknown")
    prompt = event_data.get("prompt", "")

    # Process the event
    print(f"Processing prompt: {prompt}", file=sys.stderr)

    return {
        "continue": True,
        "suppressOutput": False,
        "message": "Hook processed successfully"
    }


def main() -> None:
    """Main entry point."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Process the event
        response = process_hook_event(input_data)

        # Output JSON response
        print(json.dumps(response))

        sys.exit(0)

    except Exception as e:
        # Log errors to stderr
        print(f"Hook error: {e}", file=sys.stderr)

        # Fail-safe: allow execution to continue
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Best Practices

1. **Shebang Line**: Always use `#!/usr/bin/env -S uv run -s`
2. **PEP 723 Block**: Place immediately after shebang
3. **Minimal Dependencies**: Only include what you need
4. **Error Handling**: Always fail-safe (return `{"continue": True}`)
5. **Logging**: Use stderr for logs, stdout for JSON response
6. **Documentation**: Include docstring with environment variables

### Adding Dependencies

```python
# /// script
# dependencies = [
#   "requests>=2.31.0",          # Specific version
#   "beautifulsoup4",             # Latest version
#   "package[extra]>=1.0.0",     # With extras
# ]
# requires-python = ">=3.12"
# ///
```

### Testing Custom Hooks

```bash
# Make executable
chmod +x .claude/hooks/my_custom_hook.py

# Test manually
echo '{"session_id": "test", "prompt": "test"}' | .claude/hooks/my_custom_hook.py

# Test with setup script
uv run -s scripts/setup_pep723_hooks.py test
```

## Troubleshooting

### Hook Not Executing

**Problem**: Hook doesn't run when expected

**Solutions**:
```bash
# Check UV is installed
uv --version

# Verify hook is executable
ls -la .claude/hooks/*.py
chmod +x .claude/hooks/*.py

# Test hook manually
echo '{"session_id": "test"}' | .claude/hooks/your_hook.py

# Check Claude Code settings
cat .claude/settings.json | grep -A 5 "hooks"
```

### Dependencies Not Installing

**Problem**: UV fails to install dependencies

**Solutions**:
```bash
# Check UV cache
uv cache dir

# Clean cache
uv cache clean

# Test dependency installation
uv run -s .claude/hooks/your_hook.py <<< '{"session_id": "test"}'

# Check internet connection
ping pypi.org
```

### Slow First Execution

**Problem**: Hook takes long time on first run

**Explanation**: Normal behavior - UV downloads and caches dependencies from PyPI

**Solutions**:
```bash
# Monitor download progress
uv run -s .claude/hooks/your_hook.py <<< '{"test": true}' 2>&1 | grep -i downloading

# Check cache size
du -sh $(uv cache dir)

# Subsequent runs will be instant
```

### Hook Errors Not Visible

**Problem**: Can't see hook error messages

**Solutions**:
```bash
# Enable verbose logging
export QUICKHOOKS_VERBOSE=true

# Test hook manually to see stderr
.claude/hooks/your_hook.py <<< '{"test": true}' 2>&1

# Check Claude Code logs
tail -f ~/.claude/logs/claude-code.log
```

### GROQ API Key Issues

**Problem**: Agent analysis hook fails due to missing/invalid API key

**Solutions**:
```bash
# Set API key
export GROQ_API_KEY=your_key_here

# Verify in settings.json
grep GROQ_API_KEY .claude/settings.json

# Test with API key
GROQ_API_KEY=your_key .claude/hooks/agent_analysis_hook_pep723.py <<< '{"prompt": "test"}'
```

## Advanced Usage

### Multiple Hook Events

Configure hooks for different events:

```json
{
  "hooks": {
    "prompt-hook": {
      "command": ".claude/hooks/prompt_hook.py",
      "enabled": true,
      "events": ["user-prompt-submit"]
    },
    "tool-hook": {
      "command": ".claude/hooks/tool_hook.py",
      "enabled": true,
      "events": ["before-tool-use", "after-tool-use"]
    }
  }
}
```

### Conditional Hook Execution

Implement logic in your hook:

```python
def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """Process event conditionally."""

    # Skip for certain tools
    tool_name = event_data.get("tool_name", "")
    if tool_name in ["Bash", "Read"]:
        return {"continue": True, "suppressOutput": False}

    # Only process long prompts
    prompt = event_data.get("prompt", "")
    if len(prompt) < 20:
        return {"continue": True, "suppressOutput": False}

    # Your processing logic
    # ...

    return {"continue": True, "suppressOutput": False}
```

### Chaining Hooks

Run multiple hooks in sequence:

```json
{
  "hooks": {
    "hook-1": {
      "command": ".claude/hooks/hook1.py",
      "enabled": true,
      "order": 1
    },
    "hook-2": {
      "command": ".claude/hooks/hook2.py",
      "enabled": true,
      "order": 2
    }
  }
}
```

### Using Local QuickHooks Development Version

For development, you can use a local quickhooks installation:

```python
# /// script
# dependencies = [
#   "quickhooks @ file:///path/to/quickhooks",
# ]
# requires-python = ">=3.12"
# ///
```

Or use editable install:

```bash
# Install quickhooks in development mode
cd /path/to/quickhooks
uv pip install -e .

# Hook will use the local development version
```

### Performance Optimization

1. **Minimize Dependencies**: Only include what you need
2. **Lazy Imports**: Import inside functions when possible
3. **Cache Results**: Store expensive computations
4. **Early Exit**: Return quickly for non-applicable events

Example:

```python
def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """Optimized hook processing."""

    # Early exit for irrelevant events
    if not should_process(event_data):
        return {"continue": True, "suppressOutput": False}

    # Lazy import heavy dependencies
    from heavy_module import expensive_function

    # Process only when needed
    result = expensive_function(event_data)

    return {"continue": True, "suppressOutput": False}
```

## Additional Resources

- [PEP 723 Specification](https://peps.python.org/pep-0723/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [QuickHooks GitHub](https://github.com/kivo360/quickhooks)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [QuickHooks Main README](README.md)
- [UV Development Guide](docs/uv-guide.md)

## Contributing

To contribute new PEP 723 hooks:

1. Create hook using the template above
2. Add to `.claude/hooks/` directory
3. Update `.claude/settings.json`
4. Test with setup script
5. Document in this guide
6. Submit pull request

## License

MIT - See LICENSE file for details
