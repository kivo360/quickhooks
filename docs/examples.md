# QuickHooks Examples

This document provides practical examples of using QuickHooks for various scenarios.

## Basic Hook Examples

### 1. Simple Validation Hook

```python
# hooks/validation_hook.py
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class ValidationHook(BaseHook):
    """Validates that Bash commands don't contain dangerous operations."""
    
    name = "safety-validator"
    description = "Prevents dangerous bash commands"
    
    DANGEROUS_COMMANDS = ['rm -rf', 'sudo rm', 'dd if=', '> /dev/']
    
    def process(self, hook_input: HookInput) -> HookOutput:
        if hook_input.tool_name != "Bash":
            return HookOutput(
                allowed=True,
                modified=False,
                tool_name=hook_input.tool_name,
                tool_input=hook_input.tool_input,
                message="Non-bash tool, validation skipped"
            )
        
        command = hook_input.tool_input.get('command', '')
        
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                return HookOutput(
                    allowed=False,
                    modified=False,
                    tool_name=hook_input.tool_name,
                    tool_input=hook_input.tool_input,
                    message=f"Blocked dangerous command containing: {dangerous}"
                )
        
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Command validated successfully"
        )
```

### 2. Path Enhancement Hook

```python
# hooks/path_enhancement_hook.py
import os
from pathlib import Path
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class PathEnhancementHook(BaseHook):
    """Enhances file paths to use absolute paths when appropriate."""
    
    name = "path-enhancer"
    description = "Converts relative paths to absolute paths"
    
    def process(self, hook_input: HookInput) -> HookOutput:
        if hook_input.tool_name not in ["Read", "Write", "Edit"]:
            return HookOutput(
                allowed=True,
                modified=False,
                tool_name=hook_input.tool_name,
                tool_input=hook_input.tool_input,
                message="Non-file tool, no path enhancement needed"
            )
        
        modified_input = hook_input.tool_input.copy()
        modified = False
        
        # Enhance file_path parameter
        if 'file_path' in modified_input:
            original_path = modified_input['file_path']
            if not os.path.isabs(original_path):
                absolute_path = str(Path(original_path).resolve())
                modified_input['file_path'] = absolute_path
                modified = True
        
        return HookOutput(
            allowed=True,
            modified=modified,
            tool_name=hook_input.tool_name,
            tool_input=modified_input,
            message=f"Path enhanced: {modified}" if modified else "No path enhancement needed"
        )
```

### 3. Logging Hook

```python
# hooks/logging_hook.py
import json
import logging
from datetime import datetime
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class LoggingHook(BaseHook):
    """Logs all tool calls for audit purposes."""
    
    name = "audit-logger"
    description = "Logs all tool calls for auditing"
    
    def __init__(self):
        super().__init__()
        logging.basicConfig(
            filename='quickhooks_audit.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
    
    def process(self, hook_input: HookInput) -> HookOutput:
        # Create audit log entry
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': hook_input.tool_name,
            'tool_input': hook_input.tool_input,
            'context_id': str(hook_input.context.context_id)
        }
        
        # Log the entry
        self.logger.info(f"TOOL_CALL: {json.dumps(audit_entry)}")
        
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Tool call logged successfully"
        )
```

## Advanced Hook Examples

### 4. Content Transformation Hook

```python
# hooks/content_transformer_hook.py
import re
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class ContentTransformerHook(BaseHook):
    """Transforms content in Write operations to follow conventions."""
    
    name = "content-transformer"
    description = "Applies coding conventions to written content"
    
    def process(self, hook_input: HookInput) -> HookOutput:
        if hook_input.tool_name != "Write":
            return HookOutput(
                allowed=True,
                modified=False,
                tool_name=hook_input.tool_name,
                tool_input=hook_input.tool_input,
                message="Non-write operation, no transformation needed"
            )
        
        content = hook_input.tool_input.get('content', '')
        file_path = hook_input.tool_input.get('file_path', '')
        
        modified_content = content
        modified = False
        
        # Apply Python-specific transformations
        if file_path.endswith('.py'):
            # Ensure proper imports order
            lines = modified_content.split('\n')
            import_lines = []
            other_lines = []
            
            for line in lines:
                if line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                else:
                    other_lines.append(line)
            
            if import_lines:
                # Sort imports
                import_lines.sort()
                modified_content = '\n'.join(import_lines + [''] + other_lines)
                modified = True
        
        # Apply Markdown transformations
        elif file_path.endswith('.md'):
            # Ensure consistent heading format
            modified_content = re.sub(r'^#{1,6}\s*(.+)$', lambda m: f"{'#' * len(m.group(0).split()[0])} {m.group(1).strip()}", modified_content, flags=re.MULTILINE)
            modified = modified_content != content
        
        modified_input = hook_input.tool_input.copy()
        modified_input['content'] = modified_content
        
        return HookOutput(
            allowed=True,
            modified=modified,
            tool_name=hook_input.tool_name,
            tool_input=modified_input,
            message=f"Content transformed: {modified}"
        )
```

### 5. Multi-Tool Hook Chain

```python
# hooks/multi_tool_chain_hook.py
from typing import List, Dict, Any
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class MultiToolChainHook(BaseHook):
    """Demonstrates chaining multiple tool operations."""
    
    name = "multi-tool-chain"
    description = "Chains multiple tool operations together"
    
    def process(self, hook_input: HookInput) -> HookOutput:
        # Example: When writing a Python file, also suggest running tests
        if (hook_input.tool_name == "Write" and 
            hook_input.tool_input.get('file_path', '').endswith('.py')):
            
            # Add metadata suggesting next actions
            metadata = {
                'suggested_next_tools': [
                    {
                        'tool_name': 'Bash',
                        'tool_input': {'command': 'python -m pytest tests/'},
                        'reason': 'Run tests after writing Python code'
                    },
                    {
                        'tool_name': 'Bash', 
                        'tool_input': {'command': 'ruff check .'},
                        'reason': 'Check code style'
                    }
                ]
            }
            
            return HookOutput(
                allowed=True,
                modified=False,
                tool_name=hook_input.tool_name,
                tool_input=hook_input.tool_input,
                message="Python file write approved, tests recommended",
                metadata=metadata
            )
        
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Standard processing"
        )
```

## Testing Examples

### Unit Tests for Hooks

```python
# tests/test_validation_hook.py
import pytest
from quickhooks.models import HookInput, HookOutput, ExecutionContext
from hooks.validation_hook import ValidationHook

class TestValidationHook:
    def setup_method(self):
        self.hook = ValidationHook()
        self.context = ExecutionContext()
    
    def test_allows_safe_commands(self):
        hook_input = HookInput(
            tool_name="Bash",
            tool_input={"command": "ls -la"},
            context=self.context
        )
        
        result = self.hook.process(hook_input)
        
        assert result.allowed is True
        assert "validated successfully" in result.message.lower()
    
    def test_blocks_dangerous_commands(self):
        hook_input = HookInput(
            tool_name="Bash",
            tool_input={"command": "rm -rf /"},
            context=self.context
        )
        
        result = self.hook.process(hook_input)
        
        assert result.allowed is False
        assert "blocked dangerous command" in result.message.lower()
    
    def test_ignores_non_bash_tools(self):
        hook_input = HookInput(
            tool_name="Read",
            tool_input={"file_path": "test.txt"},
            context=self.context
        )
        
        result = self.hook.process(hook_input)
        
        assert result.allowed is True
        assert "validation skipped" in result.message.lower()
```

### Integration Tests

```python
# tests/test_hook_integration.py
import pytest
from quickhooks.executor import HookExecutor
from quickhooks.models import HookInput, ExecutionContext
from hooks.validation_hook import ValidationHook
from hooks.logging_hook import LoggingHook

class TestHookIntegration:
    def setup_method(self):
        self.executor = HookExecutor()
        self.executor.register_hook(ValidationHook())
        self.executor.register_hook(LoggingHook())
        self.context = ExecutionContext()
    
    def test_multiple_hooks_process_input(self):
        hook_input = HookInput(
            tool_name="Bash",
            tool_input={"command": "echo 'hello'"},
            context=self.context
        )
        
        results = self.executor.execute_hooks(hook_input)
        
        # Should have results from both hooks
        assert len(results) == 2
        
        # All should allow the command
        assert all(result.allowed for result in results)
        
        # Check that logging hook was executed
        logging_result = next(r for r in results if "logged" in r.message.lower())
        assert logging_result is not None
```

## Development Workflow Examples

### 1. TDD Hook Development

```python
# First, write the test
def test_my_new_hook():
    hook = MyNewHook()
    hook_input = HookInput(
        tool_name="TestTool",
        tool_input={"test": "data"},
        context=ExecutionContext()
    )
    
    result = hook.process(hook_input)
    
    assert result.allowed is True
    assert result.message == "Expected message"

# Then implement the hook
class MyNewHook(BaseHook):
    def process(self, hook_input: HookInput) -> HookOutput:
        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Expected message"
        )
```

### 2. Hot Reload Development

```bash
# Terminal 1: Start development server
quickhooks-dev --watch hooks/ --reload

# Terminal 2: Make changes to hooks
# The server automatically reloads and runs tests
```

### 3. Configuration-Driven Development

```toml
# quickhooks.toml
[hooks]
directory = "hooks"
auto_discover = true
enabled = ["validation-hook", "logging-hook"]

[development]
hot_reload = true
test_on_change = true
watch_patterns = ["*.py", "*.toml"]

[testing]
parallel = true
timeout = 30
coverage_threshold = 80
```

## Real-World Use Cases

### 1. Code Quality Enforcement

```python
class CodeQualityHook(BaseHook):
    """Enforces code quality standards before file operations."""
    
    def process(self, hook_input: HookInput) -> HookOutput:
        if hook_input.tool_name == "Write":
            file_path = hook_input.tool_input.get('file_path', '')
            content = hook_input.tool_input.get('content', '')
            
            if file_path.endswith('.py'):
                # Check for basic quality issues
                issues = []
                if 'TODO' in content:
                    issues.append("Contains TODO comments")
                if len(content.split('\n')) > 1000:
                    issues.append("File too long (>1000 lines)")
                
                if issues:
                    return HookOutput(
                        allowed=False,
                        modified=False,
                        tool_name=hook_input.tool_name,
                        tool_input=hook_input.tool_input,
                        message=f"Quality issues: {', '.join(issues)}"
                    )
        
        return HookOutput(allowed=True, modified=False, 
                         tool_name=hook_input.tool_name, 
                         tool_input=hook_input.tool_input,
                         message="Quality check passed")
```

### 2. Environment-Specific Behavior

```python
import os

class EnvironmentHook(BaseHook):
    """Modifies behavior based on environment."""
    
    def process(self, hook_input: HookInput) -> HookOutput:
        env = os.getenv('ENVIRONMENT', 'development')
        
        if env == 'production' and hook_input.tool_name == "Bash":
            command = hook_input.tool_input.get('command', '')
            
            # In production, add safety flags
            if command.startswith('rm '):
                modified_input = hook_input.tool_input.copy()
                modified_input['command'] = command.replace('rm ', 'rm -i ')
                
                return HookOutput(
                    allowed=True,
                    modified=True,
                    tool_name=hook_input.tool_name,
                    tool_input=modified_input,
                    message="Added interactive flag for production safety"
                )
        
        return HookOutput(allowed=True, modified=False,
                         tool_name=hook_input.tool_name,
                         tool_input=hook_input.tool_input,
                         message=f"Environment: {env}")
```

### 3. Team Collaboration Hook

```python
class TeamCollaborationHook(BaseHook):
    """Facilitates team collaboration through notifications."""
    
    def process(self, hook_input: HookInput) -> HookOutput:
        if hook_input.tool_name == "Write":
            file_path = hook_input.tool_input.get('file_path', '')
            
            # Notify team of important file changes
            important_files = ['README.md', 'pyproject.toml', 'requirements.txt']
            
            if any(important in file_path for important in important_files):
                # Add notification metadata
                metadata = {
                    'team_notification': {
                        'type': 'important_file_change',
                        'file': file_path,
                        'timestamp': hook_input.context.timestamp.isoformat(),
                        'notify_channels': ['#dev-team', '#notifications']
                    }
                }
                
                return HookOutput(
                    allowed=True,
                    modified=False,
                    tool_name=hook_input.tool_name,
                    tool_input=hook_input.tool_input,
                    message="Important file change - team notified",
                    metadata=metadata
                )
        
        return HookOutput(allowed=True, modified=False,
                         tool_name=hook_input.tool_name,
                         tool_input=hook_input.tool_input,
                         message="Standard processing")
```

These examples demonstrate the flexibility and power of QuickHooks for various development scenarios. Each hook can be customized and combined to create sophisticated workflows tailored to your specific needs.