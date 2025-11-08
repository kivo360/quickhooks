# QuickHooks - Claude Code Hooks (PEP 723)

This directory contains self-contained Claude Code hooks using **PEP 723 inline script metadata**.

## 🚀 What is PEP 723?

[PEP 723](https://peps.python.org/pep-0723/) allows Python scripts to declare their dependencies inline, making them completely self-contained:

```python
#!/usr/bin/env python3
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
#   "groq>=0.13.0",
# ]
# requires-python = ">=3.12"
# ///
```

## 🎯 Why PEP 723 for Claude Code Hooks?

1. **Self-Contained**: Each hook declares its own dependencies
2. **No Installation Required**: Dependencies are installed automatically from PyPI
3. **Fast Execution**: UV caches dependencies for instant subsequent runs
4. **Portable**: Scripts work anywhere UV is installed
5. **Version Controlled**: Dependencies are versioned within the script

## 📦 Available Hooks

### 1. Example Hook (`example_hook_pep723.py`)
A basic example demonstrating the PEP 723 pattern.

**Dependencies**: `quickhooks>=0.1.0`

**Usage**:
```json
{
  "hooks": {
    "user-prompt-submit": {
      "command": "uv run -s ${workspace}/.claude/hooks/example_hook_pep723.py",
      "enabled": true
    }
  }
}
```

### 2. Agent Analysis Hook (`agent_analysis_hook_pep723.py`)
AI-powered agent discovery and prompt modification.

**Dependencies**:
- `quickhooks>=0.1.0`
- `groq>=0.13.0`
- `pydantic-ai-slim[groq]>=0.0.49`
- `chromadb>=0.4.0`
- `sentence-transformers>=2.2.0`

**Configuration**:
```json
{
  "environment": {
    "GROQ_API_KEY": "your_api_key_here",
    "QUICKHOOKS_AGENT_ANALYSIS_ENABLED": "true",
    "QUICKHOOKS_AGENT_MODEL": "qwen/qwen3-32b",
    "QUICKHOOKS_CONFIDENCE_THRESHOLD": "0.7",
    "QUICKHOOKS_VERBOSE": "false"
  }
}
```

**Features**:
- Automatic agent discovery from `~/.claude/agents`
- Semantic similarity matching
- Smart prompt modification
- Context-aware chunking for large inputs

### 3. Context Portal Hook (`context_portal_hook_pep723.py`)
Persistent memory and context management across sessions.

**Dependencies**: `quickhooks>=0.1.0`

**Configuration**:
```json
{
  "environment": {
    "QUICKHOOKS_CONTEXT_PORTAL_ENABLED": "true",
    "QUICKHOOKS_CONTEXT_DB_PATH": "~/.quickhooks/context_db",
    "QUICKHOOKS_VERBOSE": "false"
  }
}
```

**Features**:
- Stores context from conversations
- Retrieves relevant context for new prompts
- Maintains conversation continuity
- Project-specific knowledge tracking

## 🛠️ Setup Instructions

### Prerequisites

1. **Install UV** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows PowerShell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Verify UV Installation**:
   ```bash
   uv --version
   ```

### Quick Start

1. **Copy hooks to your project**:
   ```bash
   mkdir -p .claude/hooks
   cp /path/to/quickhooks/.claude/hooks/*_pep723.py .claude/hooks/
   ```

2. **Copy settings template**:
   ```bash
   cp /path/to/quickhooks/.claude/settings.json .claude/settings.json
   ```

3. **Configure environment variables** in `.claude/settings.json`:
   - Set `GROQ_API_KEY` for agent analysis
   - Adjust other settings as needed

4. **Enable desired hooks** in `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "user-prompt-submit": {
         "command": "uv run -s ${workspace}/.claude/hooks/example_hook_pep723.py",
         "enabled": true  // <-- Set to true
       }
     }
   }
   ```

5. **Test hook execution**:
   ```bash
   # Test hook manually
   echo '{"session_id": "test", "tool_name": "test", "prompt": "Hello"}' | uv run -s .claude/hooks/example_hook_pep723.py
   ```

## 🔍 How UV Script Execution Works

When you run `uv run -s script.py`:

1. **UV parses the PEP 723 metadata** from the script
2. **Creates a cached virtual environment** with the specified dependencies
3. **Installs dependencies from PyPI** (only on first run or when dependencies change)
4. **Executes the script** in the cached environment
5. **Subsequent runs are instant** - dependencies are already cached

## 📋 Command Reference

```bash
# Run a hook manually
uv run -s .claude/hooks/example_hook_pep723.py < input.json

# Test hook with sample data
echo '{"session_id": "test", "prompt": "Write a function"}' | \
  uv run -s .claude/hooks/agent_analysis_hook_pep723.py

# Check UV cache
uv cache dir

# Clean UV cache (forces reinstall)
uv cache clean

# View hook dependencies
head -n 10 .claude/hooks/example_hook_pep723.py
```

## 🎨 Creating Your Own PEP 723 Hooks

Template for a new hook:

```python
#!/usr/bin/env python3
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
#   "your-package>=1.0.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Your hook description here.

Configuration via environment variables:
- YOUR_VAR: Description
"""

import json
import sys
from typing import Any


def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """Process Claude Code hook event."""
    # Your logic here
    return {
        "continue": True,
        "suppressOutput": False,
        "message": "Your message"
    }


def main() -> None:
    """Main entry point."""
    try:
        input_data = json.loads(sys.stdin.read())
        response = process_hook_event(input_data)
        print(json.dumps(response))
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)


if __name__ == "__main__":
    main()
```

## 🐛 Troubleshooting

### Hook not executing
- Check that UV is in your PATH: `which uv`
- Verify hook file is executable: `chmod +x .claude/hooks/*.py`
- Test hook manually with sample input

### Dependencies not installing
- Check UV cache: `uv cache dir`
- Clean cache and retry: `uv cache clean && uv run -s your_hook.py`
- Verify internet connection for PyPI access

### Hook errors not visible
- Hooks log to stderr, check Claude Code logs
- Enable verbose mode: `QUICKHOOKS_VERBOSE=true` in settings.json
- Test hook manually to see error output

### Slow first execution
- First run downloads dependencies from PyPI (normal)
- Subsequent runs use cached dependencies (instant)
- Cache persists across system reboots

## 📚 Additional Resources

- [PEP 723 Specification](https://peps.python.org/pep-0723/)
- [UV Documentation](https://docs.astral.sh/uv/)
- [QuickHooks Documentation](https://github.com/kivo360/quickhooks)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)

## 🤝 Contributing

To add new hooks to QuickHooks:

1. Create hook with PEP 723 metadata
2. Add to `.claude/hooks/` directory
3. Update `.claude/settings.json` with hook configuration
4. Document in this README
5. Submit pull request

## 📄 License

MIT - See LICENSE file for details
