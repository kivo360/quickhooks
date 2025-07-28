# Context Portal Integration for Claude Code

This document explains how to use the Context Portal Memory Management hook with Claude Code to automatically manage project memory and context.

## Overview

The Context Portal integration provides:

- **Automatic Context Capture**: Intercepts Claude Code tool usage and stores relevant context
- **Decision Tracking**: Detects and stores important architectural and technical decisions
- **Pattern Recognition**: Captures and categorizes code patterns and solutions
- **Memory Enhancement**: Adds relevant historical context to tool inputs
- **Project Intelligence**: Builds a searchable knowledge base of your project

## Installation

1. **Copy the hook file** to your project's hooks directory:
   ```bash
   cp hooks/context_portal_memory.py /path/to/your/project/hooks/
   chmod +x /path/to/your/project/hooks/context_portal_memory.py
   ```

2. **Create a configuration file** (copy from `examples/config_with_context_portal.yaml`):
   ```bash
   cp examples/config_with_context_portal.yaml /path/to/your/project/quickhooks.yaml
   ```

3. **Install dependencies** (if using the advanced version):
   ```bash
   pip install sqlite3  # Usually included with Python
   ```

## Configuration

### Basic Configuration

```yaml
# quickhooks.yaml
hooks:
  directory: "hooks"
  timeout: 30.0
  
  pre_tool_use:
    - name: "context_portal_memory"
      script: "context_portal_memory.py"
      enabled: true
      tool_filters: [
        "Bash", "Edit", "Write", "Read", "Grep", "Glob",
        "Task", "WebFetch", "WebSearch"
      ]
```

### Advanced Configuration

```yaml
# Full configuration with Context Portal settings
context_portal:
  database:
    path: ".context-portal/project.db"
    max_size: "100MB"
  
  memory:
    max_decisions: 1000
    max_patterns: 200
    max_context_entries: 2000
  
  categories:
    decisions: ["architecture", "technical", "tooling"]
    patterns: ["design_patterns", "code_patterns"]
```

## How It Works

### 1. Context Capture

The hook automatically captures context from Claude Code tool usage:

```python
# When you run: Claude Code -> Bash -> "npm install express"
# Hook captures:
{
  "tool": "Bash",
  "command": "npm install express",
  "timestamp": "2024-01-20T10:30:00",
  "session": "session_123"
}
```

### 2. Decision Detection

Keywords like "decide", "choose", "implement", "architecture" trigger decision storage:

```python
# When Claude processes: "We decide to use FastAPI for the REST API"
# Hook stores:
{
  "title": "Tool Decision: Task",
  "description": "We decide to use FastAPI for the REST API...",
  "decision": "FastAPI framework selection",
  "tags": ["decide", "architecture"]
}
```

### 3. Memory Enhancement

The hook searches for relevant context and adds it to tool inputs:

```python
# Before: {"command": "git status"}
# After: {
#   "command": "git status",
#   "_context_portal_history": [
#     {"command": "git add .", "result": "success"},
#     {"command": "git commit", "result": "committed changes"}
#   ]
# }
```

## Database Schema

The Context Portal creates a SQLite database with these tables:

### Decisions Table
```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    decision TEXT,
    rationale TEXT,
    alternatives TEXT,
    tags TEXT,
    timestamp DATETIME,
    hash TEXT UNIQUE
);
```

### Tasks Table
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    context TEXT,
    timestamp DATETIME,
    hash TEXT UNIQUE
);
```

### Patterns Table
```sql
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    code_example TEXT,
    use_cases TEXT,
    category TEXT,
    timestamp DATETIME,
    hash TEXT UNIQUE
);
```

### Context Entries Table
```sql
CREATE TABLE context_entries (
    id INTEGER PRIMARY KEY,
    tool_name TEXT,
    command TEXT,
    context TEXT,
    result TEXT,
    timestamp DATETIME,
    session_id TEXT,
    hash TEXT UNIQUE
);
```

## Usage Examples

### 1. Automatic Context Storage

```bash
# Run Claude Code commands normally
claude-code "Help me set up a new React project"

# Context Portal automatically captures:
# - Tool usage (Bash, Edit, Write, etc.)
# - Decision points ("choose React", "use TypeScript")
# - Patterns (project structure, configuration)
```

### 2. Query the Context Portal

You can query the database directly:

```python
from hooks.context_portal_memory import ContextPortalMemoryManager

manager = ContextPortalMemoryManager()

# Search for decisions about React
decisions = manager.search_decisions("React")
print(f"Found {len(decisions)} React-related decisions")

# Search for patterns in testing
patterns = manager.search_patterns("test", category="test_patterns")
print(f"Found {len(patterns)} testing patterns")

# Search for recent context
context = manager.search_context(tool_name="Bash", query="npm")
print(f"Found {len(context)} npm-related commands")
```

### 3. Manual Context Addition

```python
# Add a decision manually
manager.store_decision(
    title="Database Choice",
    description="Need to choose between PostgreSQL and MongoDB",
    decision="PostgreSQL for ACID compliance",
    rationale="Better data consistency and mature ecosystem",
    alternatives="MongoDB, MySQL, SQLite",
    tags=["architecture", "database"]
)

# Add a code pattern
manager.store_pattern(
    name="Repository Pattern",
    description="Data access abstraction layer",
    code_example="class UserRepository: ...",
    use_cases="Data layer separation, testing",
    category="design_patterns"
)
```

## Integration with Claude Code Memory

To integrate with Claude Code's existing memory system, add to your `CLAUDE.md`:

```markdown
# Context Portal Integration

Before answering questions, search the Context Portal for relevant project context:

1. Check for similar decisions: `manager.search_decisions(query)`
2. Look for applicable patterns: `manager.search_patterns(query)`
3. Review recent context: `manager.search_context(query)`

Store new insights:
- Important decisions
- Useful code patterns
- Problem solutions
- Architecture choices
```

## Performance Considerations

### Database Optimization

```yaml
# In your configuration
context_portal:
  database:
    vacuum_interval: "weekly"    # Clean up database
    max_size: "100MB"           # Rotate when exceeded
    backup_interval: "daily"     # Backup schedule
```

### Memory Management

```yaml
context_portal:
  memory:
    max_decisions: 1000         # Limit decisions stored
    max_patterns: 200           # Limit patterns stored
    max_context_entries: 2000   # Limit context entries
    cleanup_interval: "monthly" # Clean old entries
```

## Troubleshooting

### Hook Not Running

1. Check hook is executable: `chmod +x hooks/context_portal_memory.py`
2. Verify configuration: Check `quickhooks.yaml` syntax
3. Check tool filters: Ensure target tools are listed

### Database Issues

1. Check permissions: Ensure write access to `.context-portal/`
2. Check disk space: Database needs room to grow
3. Manual cleanup: `rm -rf .context-portal/` to reset

### Performance Issues

1. Reduce context storage: Lower `max_context_entries`
2. Optimize searches: Use specific queries instead of broad ones
3. Regular cleanup: Enable automatic cleanup intervals

## Advanced Features

### Custom Decision Keywords

```python
# Add custom keywords to ContextPortalHook
self.decision_keywords = [
    'decide', 'choose', 'implement', 'architecture', 'design',
    'refactor', 'migrate', 'adopt', 'switch', 'upgrade'  # Custom additions
]
```

### Context Enhancement Rules

```python
def enhance_with_context(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    # Custom enhancement logic
    if 'test' in str(tool_input).lower():
        # Add testing-related context
        test_patterns = self.memory_manager.search_patterns("", category="test_patterns")
        if test_patterns:
            tool_input['_testing_context'] = test_patterns[:3]
    
    return tool_input
```

### Integration with External Tools

```python
# Export to other tools
def export_to_confluence():
    decisions = manager.search_decisions("")
    # Generate Confluence page from decisions
    
def export_to_notion():
    patterns = manager.search_patterns("")
    # Sync patterns to Notion database
```

## Best Practices

1. **Regular Maintenance**: Set up automatic cleanup and backups
2. **Categorization**: Use consistent tags and categories
3. **Quality Control**: Review stored decisions periodically
4. **Integration**: Connect with existing documentation systems
5. **Privacy**: Be mindful of sensitive information in context storage

## Conclusion

The Context Portal integration transforms Claude Code into an intelligent development assistant that learns from your project history. It automatically captures context, tracks decisions, and enhances future interactions with relevant historical information.

This creates a compound effect where Claude Code becomes more effective over time as it builds a comprehensive understanding of your project's context, decisions, and patterns.