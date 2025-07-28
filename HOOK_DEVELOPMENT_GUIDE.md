# QuickHooks Development Guide: Creating Your Own Hooks

This guide walks you through creating custom hooks for the QuickHooks framework, using the grep-to-ripgrep hook as a complete working example.

## What Are QuickHooks?

QuickHooks are Python scripts that intercept and modify tool usage in real-time. They can:

- **Pre-tool-use**: Modify commands before execution
- **Post-tool-use**: Process results after execution  
- **Event-driven**: React to specific events in your workflow

## The Complete Example: Grep to Ripgrep Hook

Our example hook automatically transforms `grep` commands to use `ripgrep` (rg) for faster searching.

### Key Transformations

```bash
# Before (grep)                          # After (ripgrep)
grep "pattern" file.txt          →       rg "pattern" file.txt
grep -r "pattern" dir            →       rg "pattern" dir
grep -i "pattern" file           →       rg -i "pattern" file
grep -rni "pattern" /src         →       rg -n -i "pattern" /src
grep --include="*.py" "TODO"     →       rg --glob "*.py" "TODO"
```

## Step-by-Step Implementation

### Step 1: Understand the Hook Architecture

QuickHooks communicate via JSON through stdin/stdout:

**Input Format:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "grep -i 'pattern' file.txt",
    "description": "Search for pattern"
  }
}
```

**Output Format:**
```json
{
  "allowed": true,
  "modified": true,
  "tool_name": "Bash",
  "tool_input": {
    "command": "rg -i 'pattern' file.txt",
    "description": "Search for pattern"
  },
  "message": "Transformed grep to ripgrep"
}
```

### Step 2: Create the Core Transformer Class

```python
class GrepToRipgrepTransformer:
    """Transforms grep commands to equivalent ripgrep commands."""
    
    def __init__(self):
        # Direct flag mappings (grep flag -> rg flag)
        self.direct_mappings = {
            '-i': '-i',      # case insensitive
            '-n': '-n',      # show line numbers
            '-v': '-v',      # invert match
            # ... more mappings
        }
        
        # Flags that need special handling
        self.special_flags = {
            '-r', '--recursive',     # recursive (default in rg)
            '-F', '--fixed-strings', # literal strings
            # ... more special cases
        }
```

**Key Design Decisions:**

1. **Separation of Concerns**: Transformer class handles logic, main() handles I/O
2. **Robust Parsing**: Use `shlex.split()` for proper shell command parsing
3. **Flag Mapping**: Direct mappings for simple cases, special handling for complex ones
4. **Error Handling**: Always allow original command on errors

### Step 3: Implement Command Parsing

```python
def parse_grep_command(self, command: str) -> Optional[Dict[str, Any]]:
    """Parse a grep command into components."""
    try:
        tokens = shlex.split(command)
        
        # Find grep in the command
        grep_index = -1
        for i, token in enumerate(tokens):
            if token.endswith('grep'):
                grep_index = i
                break
        
        if grep_index == -1:
            return None
            
        return {
            'prefix': tokens[:grep_index],  # sudo, env vars, etc.
            'grep_cmd': tokens[grep_index],
            'args': tokens[grep_index + 1:],
            'full_tokens': tokens
        }
    except ValueError:
        return None  # Shell parsing failed
```

**Why This Approach:**
- Handles complex shell syntax correctly
- Preserves command prefixes (sudo, env vars)
- Gracefully handles parsing errors

### Step 4: Implement Argument Transformation

```python
def transform_args(self, args: List[str]) -> Tuple[List[str], List[str]]:
    """Transform grep arguments to ripgrep arguments."""
    rg_flags = []
    remaining_args = []
    i = 0
    
    while i < len(args):
        arg = args[i]
        
        # Handle combined short flags (e.g., -rni)
        if arg.startswith('-') and len(arg) > 2 and not arg.startswith('--'):
            for char in arg[1:]:
                flag = f'-{char}'
                if flag in self.direct_mappings:
                    mapped = self.direct_mappings[flag]
                    if mapped not in rg_flags:
                        rg_flags.append(mapped)
                elif flag == '-r':  # Skip recursive (default in rg)
                    continue
                # ... handle other cases
            i += 1
            continue
            
        # Handle flags with values (e.g., -A 3)
        if arg in ['-A', '--after-context']:
            if i + 1 < len(args):
                rg_flags.extend([arg, args[i + 1]])
                i += 2
                continue
                
        # ... more transformation logic
```

**Key Patterns:**
- **Combined Flags**: Split `-rni` into individual flags
- **Value Flags**: Handle flags that take parameters
- **Special Cases**: Skip redundant flags, transform syntax
- **Preserve Unknown**: Pass through unrecognized flags

### Step 5: Create the Main Hook Entry Point

```python
def main():
    """Main hook entry point."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Default response (allow original command)
        response = {
            'allowed': True,
            'modified': False,
            'tool_name': input_data.get('tool_name', ''),
            'tool_input': input_data.get('tool_input', {}),
            'message': None
        }
        
        # Only process Bash commands
        if input_data.get('tool_name') != 'Bash':
            print(json.dumps(response))
            return
            
        # Transform the command
        command = input_data.get('tool_input', {}).get('command', '')
        transformer = GrepToRipgrepTransformer()
        transformed = transformer.transform_command(command)
        
        if transformed and transformed != command:
            # Update response with transformation
            response.update({
                'modified': True,
                'tool_input': {
                    **input_data['tool_input'],
                    'command': transformed
                },
                'message': f'Transformed grep to ripgrep: {command[:50]}...'
            })
        
        print(json.dumps(response))
        
    except Exception as e:
        # Always allow original command on errors
        error_response = {
            'allowed': True,
            'modified': False,
            'message': f'Hook error (proceeding): {str(e)}'
        }
        print(json.dumps(error_response))
```

**Critical Design Principles:**

1. **Fail-Safe**: Always allow original command on errors
2. **Selective Processing**: Only modify relevant tools/commands
3. **Preserve Data**: Keep all original tool_input fields
4. **Clear Communication**: Provide informative messages

## Step 6: Comprehensive Testing

### Unit Tests for Transformer Logic

```python
class TestGrepToRipgrepTransformer:
    def test_transform_basic_grep(self):
        transformer = GrepToRipgrepTransformer()
        result = transformer.transform_command('grep "hello" file.txt')
        assert result == 'rg "hello" file.txt'
        
    def test_transform_combined_flags(self):
        transformer = GrepToRipgrepTransformer()
        result = transformer.transform_command('grep -rni "pattern" /path')
        assert result == 'rg -n -i "pattern" /path'  # -r omitted
```

### Integration Tests for Complete Hook

```python
class TestHookIntegration:
    def run_hook(self, input_data):
        """Run the actual hook script."""
        process = subprocess.run(
            ['python', 'hooks/grep_to_ripgrep.py'],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        return json.loads(process.stdout)
    
    def test_hook_transforms_grep(self):
        input_data = {
            'tool_name': 'Bash',
            'tool_input': {'command': 'grep "hello" file.txt'}
        }
        result = self.run_hook(input_data)
        
        assert result['allowed'] is True
        assert result['modified'] is True
        assert result['tool_input']['command'] == 'rg "hello" file.txt'
```

### Edge Case Testing

```python
@pytest.mark.parametrize("command,expected", [
    ('grep "test" file.txt', 'rg "test" file.txt'),
    ('grep -rni "pattern" dir/', 'rg -n -i "pattern" dir/'),
    ('sudo grep -i "pattern" file.txt', 'sudo rg -i "pattern" file.txt'),
    # ... more test cases
])
def test_parametrized_transformations(command, expected):
    transformer = GrepToRipgrepTransformer()
    result = transformer.transform_command(command)
    assert result == expected
```

## Step 7: Configuration and Deployment

### Hook Configuration

```yaml
# quickhooks.yaml
hooks:
  directory: "hooks"
  timeout: 30.0
  
  pre_tool_use:
    - name: "grep_to_ripgrep"
      script: "grep_to_ripgrep.py"
      enabled: true
      tool_filters: ["Bash"]
      environment:
        RG_PATH: "/usr/local/bin/rg"
        DEBUG_TRANSFORMS: "false"
```

### Directory Structure

```
your-project/
├── hooks/
│   └── grep_to_ripgrep.py      # The hook implementation
├── tests/
│   └── test_grep_to_ripgrep.py # Comprehensive tests
├── examples/
│   └── config_with_grep_hook.yaml # Example configuration
├── quickhooks.yaml             # Your configuration
└── HOOK_DEVELOPMENT_GUIDE.md   # This guide
```

## Creating Your Own Hook: Template

Here's a template for creating your own hook:

```python
#!/usr/bin/env python3
"""
QuickHook: [Your Hook Name]

Description of what your hook does.
"""

import json
import sys
from typing import Dict, Any, Optional


class YourTransformer:
    """Your hook's main logic class."""
    
    def __init__(self):
        """Initialize your transformer."""
        pass
    
    def should_process(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Determine if this command should be processed."""
        # Add your logic here
        return tool_name == 'YourTargetTool'
    
    def transform(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform the tool input."""
        # Add your transformation logic here
        # Return modified tool_input or None if no changes
        pass


def main():
    """Main hook entry point."""
    try:
        # Read input
        input_data = json.loads(sys.stdin.read())
        
        # Default response
        response = {
            'allowed': True,
            'modified': False,
            'tool_name': input_data.get('tool_name', ''),
            'tool_input': input_data.get('tool_input', {}),
            'message': None
        }
        
        # Process if applicable
        transformer = YourTransformer()
        if transformer.should_process(
            input_data.get('tool_name', ''),
            input_data.get('tool_input', {})
        ):
            transformed = transformer.transform(input_data.get('tool_input', {}))
            if transformed:
                response.update({
                    'modified': True,
                    'tool_input': transformed,
                    'message': 'Your transformation message'
                })
        
        print(json.dumps(response))
        
    except Exception as e:
        # Fail-safe: allow original command
        error_response = {
            'allowed': True,
            'modified': False,
            'message': f'Hook error: {str(e)}'
        }
        print(json.dumps(error_response))


if __name__ == '__main__':
    main()
```

## Best Practices Summary

1. **Always Fail-Safe**: Never block execution on errors
2. **Parse Carefully**: Use proper shell parsing libraries
3. **Test Thoroughly**: Unit tests + integration tests + edge cases
4. **Document Well**: Clear comments and examples
5. **Performance**: Keep hooks fast (< 100ms typically)
6. **Logging**: Use stderr for debug info, stdout for JSON response
7. **Configuration**: Make behavior configurable via environment variables
8. **Backwards Compatibility**: Handle different input formats gracefully

## Advanced Patterns

### Conditional Transformations

```python
def transform(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    command = tool_input.get('command', '')
    
    # Only transform if ripgrep is available
    if not shutil.which('rg'):
        return None  # Skip transformation
        
    # Only transform for certain file types
    if not any(ext in command for ext in ['.py', '.js', '.go']):
        return None
        
    return self.do_transform(tool_input)
```

### Context-Aware Transformations

```python
def transform(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    command = tool_input.get('command', '')
    context = tool_input.get('context', {})
    
    # Different behavior based on project type
    if context.get('project_type') == 'python':
        # Add Python-specific optimizations
        pass
    elif context.get('project_type') == 'javascript':
        # Add JS-specific optimizations
        pass
        
    return modified_input
```

### Chained Transformations

```python
def transform(self, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = tool_input.copy()
    
    # Apply multiple transformations
    result = self.transform_grep_to_rg(result)
    result = self.add_performance_flags(result)
    result = self.optimize_patterns(result)
    
    return result if result != tool_input else None
```

## Deployment and Usage

1. **Place your hook** in the `hooks/` directory
2. **Make it executable**: `chmod +x hooks/your_hook.py`
3. **Add to configuration**: Update `quickhooks.yaml`
4. **Test thoroughly**: Run your test suite
5. **Monitor performance**: Check execution times
6. **Iterate based on usage**: Improve based on real-world usage

Your hook is now ready to automatically transform commands and enhance your development workflow!

## Real-World Examples

### File Path Optimizer Hook
Transforms relative paths to absolute paths for consistency.

### Language Server Hook  
Automatically configures language servers based on file types.

### Performance Monitor Hook
Adds timing and profiling flags to commands automatically.

### Security Scanner Hook
Intercepts file operations to run security scans.

The possibilities are endless - QuickHooks let you customize your entire development workflow!