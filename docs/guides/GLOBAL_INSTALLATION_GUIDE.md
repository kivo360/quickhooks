# Global Context Portal Installation Guide

This guide shows you how to install the Context Portal memory management system globally for Claude Code, so it works automatically across all your projects.

## 🚀 Quick Start

### Prerequisites

1. **Claude Code** installed and working
2. **Python 3.11+** 
3. **Virtual environment** (recommended but not required)

### Installation Steps

```bash
# 1. Clone and set up QuickHooks
git clone <quickhooks-repo>
cd quickhooks

# 2. Install dependencies
make install
# or: uv sync

# 3. Install Context Portal globally
quickhooks install install-global
```

That's it! Context Portal is now globally configured for Claude Code.

## 📋 Detailed Installation

### Step 1: Environment Setup

**With Virtual Environment (Recommended):**
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install QuickHooks
cd /path/to/quickhooks
make install
```

**With Conda:**
```bash
# Create conda environment
conda create -n claude-hooks python=3.12
conda activate claude-hooks

# Install QuickHooks
cd /path/to/quickhooks
make install
```

### Step 2: Verify Claude Code

```bash
# Check Claude Code is installed
claude --version

# Check Claude config directory
ls ~/.claude/
```

### Step 3: Install Context Portal Globally

```bash
# Install globally (from QuickHooks directory)
quickhooks install install-global
```

### Step 4: Verify Installation

```bash
# Check installation status
quickhooks install status
```

You should see:
```
📊 Overall Status: ✅ Fully Installed

   Hook Script: ✅ Installed (~/.claude/hooks/context_portal_memory.py)
   Claude Settings: ✅ Configured
   Global Config: ✅ Present (~/.claude/context_portal_config.json)
   Virtual Environment: ✅ Detected (/path/to/your/venv)
   Python Executable: /path/to/your/venv/bin/python
```

## 🔧 How It Works

### Virtual Environment Detection

The installer automatically detects and configures for your current environment:

- **Conda**: Uses `$CONDA_PREFIX`
- **Standard venv**: Uses `$VIRTUAL_ENV` 
- **Poetry**: Detects Poetry virtual environments
- **Pipenv**: Uses `$PIPENV_ACTIVE` + `$VIRTUAL_ENV`
- **System Python**: Falls back if no virtual environment detected

### File Structure Created

```
~/.claude/
├── settings.json                    # Updated with Context Portal hooks
├── context_portal_config.json       # Global Context Portal configuration
└── hooks/
    └── context_portal_memory.py     # Hook wrapper script
```

### Hook Wrapper System

The installer creates a smart wrapper script that:

1. **Environment Detection**: Uses the correct Python executable from your virtual environment
2. **Fallback Execution**: If environment issues occur, falls back to subprocess execution
3. **Fail-Safe Behavior**: Never blocks Claude Code execution, even on errors
4. **Context Enhancement**: Adds project memory to tool inputs when available

## 🎯 Usage After Installation

### Automatic Operation

Once installed, Context Portal works automatically:

```bash
# Use Claude Code normally - context is captured automatically
claude "Help me set up a new React project"
claude "Review this code for security issues" 
claude "Add unit tests for the authentication module"
```

### Project Memory Databases

Each project gets its own memory database:

```
your-project/
├── .context-portal/
│   ├── project.db           # SQLite database with project memory
│   └── hooks.log           # Hook execution log (if logging enabled)
├── src/
└── ...
```

### Manual Context Queries

You can also query the context portal directly:

```python
from quickhooks.hooks.context_portal_memory import ContextPortalMemoryManager

# Initialize manager for current project
manager = ContextPortalMemoryManager()

# Search for decisions
decisions = manager.search_decisions("database")
print(f"Found {len(decisions)} database-related decisions")

# Search for patterns  
patterns = manager.search_patterns("authentication")
print(f"Found {len(patterns)} authentication patterns")

# Search command history
history = manager.search_context(tool_name="Bash", query="npm")
print(f"Found {len(history)} npm commands in history")
```

## ⚙️ Configuration

### Global Configuration

Edit `~/.claude/context_portal_config.json`:

```json
{
  "context_portal": {
    "database": {
      "path": ".context-portal/project.db",
      "max_size": "100MB",
      "backup_interval": "daily"
    },
    "memory": {
      "max_decisions": 1000,
      "max_tasks": 500, 
      "max_patterns": 200,
      "max_context_entries": 2000,
      "cleanup_interval": "monthly"
    },
    "search": {
      "default_limit": 10,
      "max_limit": 50,
      "enable_fuzzy_search": true
    }
  }
}
```

### Claude Settings Integration

The installer updates `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write|Read|Grep|Glob|Task|WebFetch|WebSearch",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/you/.claude/hooks/context_portal_memory.py"
          }
        ]
      }
    ]
  }
}
```

### Environment Variables

You can customize behavior with environment variables:

```bash
# In your shell profile (.bashrc, .zshrc)
export CONTEXT_PORTAL_DEBUG=true                    # Enable debug logging
export CONTEXT_PORTAL_MAX_CONTEXT_ENTRIES=5000     # Increase context storage
export CONTEXT_PORTAL_ENABLE_PATTERNS=false        # Disable pattern storage
```

## 🔄 Management Commands

### Check Status
```bash
quickhooks install status
```

### Reinstall/Update
```bash
quickhooks install install-global  # Reinstalls and updates configuration
```

### Uninstall
```bash
quickhooks install uninstall-global
```

This removes:
- Hook script from `~/.claude/hooks/`
- Hook configuration from `~/.claude/settings.json`
- Global configuration file

**Note**: Project databases in `.context-portal/` directories are preserved.

## 🚨 Troubleshooting

### Hook Not Running

**Check Claude settings:**
```bash
claude config list | grep hooks
```

**Verify hook script:**
```bash
ls -la ~/.claude/hooks/context_portal_memory.py
```

**Test hook manually:**
```bash
echo '{"tool_name": "Bash", "tool_input": {"command": "echo test"}}' | \
  ~/.claude/hooks/context_portal_memory.py
```

### Virtual Environment Issues

**Wrong Python executable:**
```bash
# Check which Python the hook is using
head -20 ~/.claude/hooks/context_portal_memory.py

# Reinstall to update Python path
quickhooks install install-global
```

**Environment not detected:**
```bash
# Activate your environment first, then reinstall
source .venv/bin/activate
quickhooks install install-global
```

### Database Issues

**Permission errors:**
```bash
# Check project directory permissions
ls -la .context-portal/

# Reset database (loses data!)
rm -rf .context-portal/
```

**Database corruption:**
```bash
# Reset project database
rm .context-portal/project.db

# Context Portal will recreate on next use
```

### Performance Issues

**Large database:**
```bash
# Check database size
du -h .context-portal/project.db

# Manual cleanup (reduce max entries in config)
# Then restart Claude Code
```

**Slow hook execution:**
```bash
# Check hook logs
tail -f .context-portal/hooks.log

# Disable context enhancement temporarily
export CONTEXT_PORTAL_ENABLE_CONTEXT=false
```

## 🔒 Security Considerations

### Sensitive Information

Context Portal stores tool usage history. Be aware:

- **Commands** with secrets/passwords will be stored
- **File contents** are not stored, only file paths
- **Project context** is stored locally, not transmitted

### Recommendations

1. **Use environment variables** for secrets instead of command-line arguments
2. **Review `.context-portal/`** contents periodically
3. **Add `.context-portal/`** to `.gitignore` to avoid committing databases
4. **Set up regular cleanup** to remove old context entries

### Exclusions

To exclude sensitive projects:

```json
// In project's .claude/settings.local.json
{
  "hooks": {
    "PreToolUse": []  // Disables all hooks for this project
  }
}
```

## 🔄 Multiple Environments

### Development vs Production

**Development Environment:**
```bash
# In your dev environment
conda activate myproject-dev
quickhooks install install-global
```

**Production Environment:**
```bash
# In your production environment  
conda activate myproject-prod
quickhooks install install-global
```

Each environment gets its own hook configuration pointing to the correct Python executable.

### Team Setup

**Shared Configuration:**
```bash
# In project directory, create team-shared settings
mkdir -p .claude
cp ~/.claude/context_portal_config.json .claude/

# Team members can use:
quickhooks install install-global  # Still installs globally
```

**Per-Developer Customization:**
```json
// .claude/settings.local.json (not committed)
{
  "context_portal": {
    "memory": {
      "max_context_entries": 10000  // Higher limit for senior devs
    }
  }
}
```

## 📊 Monitoring and Analytics

### Database Queries

```python
import sqlite3
from pathlib import Path

# Connect to project database
db_path = Path(".context-portal/project.db")
with sqlite3.connect(db_path) as conn:
    # Most used tools
    cursor = conn.execute("""
        SELECT tool_name, COUNT(*) as count 
        FROM context_entries 
        GROUP BY tool_name 
        ORDER BY count DESC
    """)
    print("Most used tools:", cursor.fetchall())
    
    # Recent decisions
    cursor = conn.execute("""
        SELECT title, timestamp 
        FROM decisions 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    print("Recent decisions:", cursor.fetchall())
```

### Usage Statistics

```bash
# Database size over time
find . -name "project.db" -exec du -h {} \;

# Hook execution frequency
grep "Enhanced with Context Portal" .context-portal/hooks.log | wc -l
```

## 🚀 Advanced Features

### Custom Decision Keywords

Edit the hook script to add custom keywords:

```python
# In ~/.claude/hooks/context_portal_memory.py
# Find the decision_keywords list and add your terms
self.decision_keywords = [
    'decide', 'choose', 'implement', 'architecture', 'design',
    'refactor', 'migrate', 'adopt', 'switch', 'upgrade',
    # Your custom keywords:
    'technical-debt', 'performance', 'security-review'
]
```

### Integration with External Tools

**Export to Confluence:**
```python
def export_decisions_to_confluence():
    manager = ContextPortalMemoryManager()
    decisions = manager.search_decisions("")
    # Generate Confluence pages from decisions
    # ... implementation
```

**Sync with Notion:**
```python
def sync_patterns_to_notion():
    manager = ContextPortalMemoryManager()
    patterns = manager.search_patterns("")
    # Sync to Notion database
    # ... implementation
```

### Backup and Restore

**Automated Backup:**
```bash
#!/bin/bash
# backup-context-portal.sh
find . -name ".context-portal" -type d | while read dir; do
    tar -czf "${dir%/*}/context-portal-backup-$(date +%Y%m%d).tar.gz" "$dir"
done
```

**Add to crontab:**
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup-context-portal.sh
```

## 🎉 Success!

Context Portal is now globally configured for Claude Code. It will automatically:

✅ **Capture context** from all tool usage  
✅ **Store decisions** and architectural choices  
✅ **Build patterns** database from your code  
✅ **Enhance future interactions** with relevant history  
✅ **Create project memory** that compounds over time  

Your AI assistant now has persistent memory across all your projects! 🧠✨