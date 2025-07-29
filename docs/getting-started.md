# QuickHooks Getting Started Guide

QuickHooks is a streamlined framework for creating and managing Claude Code hooks with real-time feedback and TDD workflows.

## Installation

```bash
pip install quickhooks
```

## Quick Start

### 1. Create Your First Hook

```python
# hooks/my_first_hook.py
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class MyFirstHook(BaseHook):
    """A simple hook that adds a timestamp to tool calls."""
    
    def process(self, hook_input: HookInput) -> HookOutput:
        # Add timestamp to the tool call
        modified_input = hook_input.tool_input.copy()
        modified_input['timestamp'] = hook_input.context.timestamp.isoformat()
        
        return HookOutput(
            allowed=True,
            modified=True,
            tool_name=hook_input.tool_name,
            tool_input=modified_input,
            message="Added timestamp to tool call"
        )
```

### 2. Test Your Hook

```python
# test_my_hook.py
import pytest
from quickhooks.models import HookInput, ExecutionContext
from hooks.my_first_hook import MyFirstHook

def test_my_first_hook():
    hook = MyFirstHook()
    
    # Create test input
    hook_input = HookInput(
        tool_name="TestTool",
        tool_input={"data": "test"},
        context=ExecutionContext()
    )
    
    # Process the hook
    result = hook.process(hook_input)
    
    # Verify results
    assert result.allowed is True
    assert result.modified is True
    assert 'timestamp' in result.tool_input
    assert result.tool_input['data'] == 'test'
```

### 3. Run Development Server

```bash
quickhooks-dev --watch hooks/
```

This starts a hot-reload development server that automatically tests your hooks when files change.

## Core Concepts

### Hook Structure

Every hook inherits from `BaseHook` and implements the `process` method:

```python
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput

class MyHook(BaseHook):
    name = "my-custom-hook"
    description = "What this hook does"
    version = "1.0.0"
    
    def process(self, hook_input: HookInput) -> HookOutput:
        # Your hook logic here
        return HookOutput(
            allowed=True,  # Allow the tool call
            modified=False,  # Whether input was modified
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Hook processed successfully"
        )
```

### Hook Input/Output

**HookInput** contains:
- `tool_name`: Name of the Claude Code tool being called
- `tool_input`: Parameters passed to the tool
- `context`: Execution context with metadata

**HookOutput** contains:
- `allowed`: Whether to allow the tool call
- `modified`: Whether the input was modified
- `tool_name`: Tool name (can be changed)
- `tool_input`: Tool parameters (can be modified)
- `message`: Status message
- `metadata`: Additional metadata

### Configuration

Create `quickhooks.toml` for project configuration:

```toml
[hooks]
directory = "hooks"
auto_discover = true

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[development]
hot_reload = true
test_on_change = true
```

## Built-in Hooks

### Grep to Ripgrep Transformer

Automatically converts `grep` commands to `rg` (ripgrep):

```python
from quickhooks.hooks.grep_to_ripgrep import GrepToRipgrepHook

# This hook automatically transforms:
# grep -r "pattern" dir/
# Into:
# rg "pattern" dir/
```

### Context Portal Memory

Integrates with Claude Code's context portal for enhanced memory:

```bash
quickhooks install context-portal
```

## CLI Commands

### Development Server
```bash
quickhooks-dev [OPTIONS]
  --watch TEXT     Directory to watch for changes
  --port INTEGER   Port for development server
  --reload         Enable hot reload
```

### Hook Management
```bash
quickhooks list                    # List available hooks
quickhooks test [HOOK_NAME]        # Test specific hook
quickhooks validate [HOOK_PATH]    # Validate hook syntax
```

### Installation
```bash
quickhooks install context-portal  # Install context portal integration
quickhooks uninstall [HOOK_NAME]   # Remove installed hook
```

## Advanced Features

### Agent Analysis

QuickHooks can analyze prompts and recommend appropriate agents:

```python
from quickhooks.agent_analysis import AgentAnalyzer, AgentAnalysisRequest

analyzer = AgentAnalyzer(groq_api_key="your-key")
request = AgentAnalysisRequest(
    prompt="Write a Python function to sort a list",
    confidence_threshold=0.7
)

result = analyzer.analyze_prompt_sync(request)
print(f"Recommended agents: {[r.agent_type for r in result.recommendations]}")
```

### Parallel Processing

Run multiple hooks in parallel:

```python
from quickhooks.hooks.parallel import ParallelHookProcessor

processor = ParallelHookProcessor([hook1, hook2, hook3])
results = processor.process_parallel(hook_input)
```

### Custom Validators

Create custom validation logic:

```python
from quickhooks.schema.validator import SchemaValidator

class CustomValidator(SchemaValidator):
    def validate_hook_output(self, output: HookOutput) -> bool:
        # Custom validation logic
        return output.allowed and len(output.message) > 0
```

## Best Practices

1. **Keep hooks focused**: Each hook should have a single responsibility
2. **Use descriptive names**: Make hook purposes clear from their names
3. **Add comprehensive tests**: Test both success and failure cases
4. **Handle errors gracefully**: Always return valid HookOutput even on errors
5. **Use the development server**: Take advantage of hot reload for faster iteration
6. **Document your hooks**: Include docstrings and usage examples

## Troubleshooting

### Common Issues

**Import errors**: Ensure QuickHooks is installed in your environment
```bash
pip install --upgrade quickhooks
```

**Hook not found**: Check that your hook inherits from `BaseHook` and is in the hooks directory

**Development server not reloading**: Verify file permissions and that watchfiles is installed

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
export QUICKHOOKS_LOG_LEVEL=DEBUG
```

## Examples Repository

Check out the `examples/` directory for complete working examples:

- `examples/basic_hook_demo.py` - Basic hook implementation
- `examples/agent_analysis_demo.py` - Agent analysis usage
- `examples/context_portal_demo.py` - Context portal integration
- `examples/parallel_processing_demo.py` - Parallel hook processing

## Next Steps

1. Explore the [API Reference](api-reference.md)
2. Check out [Advanced Patterns](advanced-patterns.md)
3. Join our community discussions
4. Contribute to the project

Happy hooking! 🪝