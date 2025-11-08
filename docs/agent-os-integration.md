# Agent OS Integration for QuickHooks

QuickHooks now provides seamless integration with [Agent OS](https://buildermethods.com/agent-os), enabling spec-driven agentic development workflows within the QuickHooks framework.

## Overview

Agent OS transforms AI coding agents from confused interns into productive developers by providing structured workflows that capture your standards, stack, and codebase details. With this integration, QuickHooks can execute Agent OS instructions and workflows directly from your development environment or Claude Code.

## Features

### 🔄 Workflow Execution
- Execute predefined Agent OS workflows (product-planning, feature-development)
- Create custom workflows with multiple Agent OS instructions
- Resume workflows from saved state
- Track workflow progress and step results

### 📋 Instruction Management
- List and execute available Agent OS instructions
- Parse and validate Agent OS instruction files
- Support for both core and meta instruction categories
- Rich output formatting with progress tracking

### 🔗 Claude Code Integration
- Automatic detection of Agent OS intent in user prompts
- Seamless hook integration with Claude Code
- Context-aware execution with working directory support
- Pre/post-execution workflow support

## Installation

### Prerequisites
1. **Agent OS Installation**: Ensure Agent OS is installed at `~/.agent-os`
2. **QuickHooks with Agent OS Dependencies**:
   ```bash
   # Install with Agent OS support
   pip install quickhooks[agent_os]

   # Or install all dependencies
   pip install quickhooks[all]
   ```

### Environment Variables
```bash
# Enable/disable Agent OS integration
export QUICKHOOKS_AGENT_OS_ENABLED=true

# Custom Agent OS installation path
export AGENT_OS_PATH=~/.agent-os

# Default instruction category
export QUICKHOOKS_AGENT_OS_CATEGORY=core

# Enable verbose output
export QUICKHOOKS_AGENT_OS_VERBOSE=false
```

## CLI Commands

### List Available Instructions
```bash
# List all available instructions
quickhooks agent-os list-instructions

# Filter by category
quickhooks agent-os list-instructions --category core
quickhooks agent-os list-instructions --category meta

# Custom Agent OS path
quickhooks agent-os list-instructions --agent-os-path /custom/path/to/agent-os
```

### Execute Instructions
```bash
# Execute a single instruction
quickhooks agent-os execute-instruction plan-product

# With category and context
quickhooks agent-os execute-instruction create-spec \
  --category core \
  --context project_context.json \
  --verbose

# Show instruction details
quickhooks agent-os show-instruction plan-product --category core
```

### Workflow Management
```bash
# List available workflows
quickhooks agent-os list-workflows

# Initialize predefined workflows
quickhooks agent-os init-workflows

# Create a custom workflow
quickhooks agent-os create-workflow my-workflow \
  --description "My custom development workflow" \
  --instructions "plan-product,create-spec,analyze-product" \
  --category core

# Execute a workflow
quickhooks agent-os execute-workflow product-planning \
  --context project_context.json \
  --verbose

# Resume a workflow from saved state
quickhooks agent-os execute-workflow feature-development \
  --resume \
  --save-state
```

## Claude Code Integration

### Hook Installation
Add the Agent OS workflow hook to your Claude Code `settings.json`:

```json
{
  "hooks": [
    {
      "type": "pre_tool_use",
      "path": "/path/to/quickhooks/hooks/agent_os_workflow_hook.py",
      "enabled": true
    }
  ]
}
```

### Usage Examples

#### Product Planning
```
User: "Plan the product for a new task management app"
```
The hook will automatically:
1. Detect the "plan-product" intent
2. Execute the Agent OS `plan-product` instruction
3. Return structured results for product planning

#### Specification Creation
```
User: "Create detailed specs for the user authentication feature"
```
The hook will:
1. Detect the "create-spec" intent
2. Execute the Agent OS `create-spec` instruction
3. Generate comprehensive technical specifications

#### End-to-End Development
```
User: "I want to build a complete blog platform from idea to implementation"
```
The hook will:
1. Detect multi-step workflow intent
2. Execute the "product-planning" workflow
3. Chain through plan-product → create-spec → analyze-product

## Architecture

### Core Components

#### InstructionParser
- Parses Agent OS instruction files (`.md` format)
- Extracts process flows, steps, and metadata
- Resolves agent references and dependencies

#### AgentOSExecutor
- Executes individual Agent OS instructions
- Handles pre/post-flight checks
- Manages execution context and error handling

#### WorkflowManager
- Manages complex multi-instruction workflows
- Handles workflow state persistence
- Supports step dependencies and conditions

#### AgentOSHook
- Base hook for executing Agent OS instructions
- Integrates with QuickHooks hook framework
- Supports both instruction and workflow execution

### Workflow Types

#### Product Planning Workflow
1. **plan-product**: Generate product documentation and structure
2. **create-spec**: Create technical specifications
3. **analyze-product**: Analyze requirements and dependencies

#### Feature Development Workflow
1. **create-spec**: Define feature specifications
2. **execute-tasks**: Implement development tasks
3. **analyze-product**: Validate implementation

## Configuration

### Agent OS Path Configuration
```python
from quickhooks.agent_os import AgentOSExecutor

# Custom Agent OS installation path
executor = AgentOSExecutor(
    agent_os_path=Path("/custom/path/to/agent-os"),
    working_directory=Path("/project/working/directory")
)
```

### Workflow Definition
```python
from quickhooks.agent_os.workflow_manager import WorkflowManager, WorkflowStep

manager = WorkflowManager()

# Create custom workflow
workflow = manager.create_workflow(
    name="custom-workflow",
    description="My custom development workflow",
    steps=[
        WorkflowStep(
            instruction="plan-product",
            category="core"
        ),
        WorkflowStep(
            instruction="create-spec",
            category="core",
            depends_on=["plan-product"]
        )
    ]
)
```

## API Reference

### AgentOSExecutor
```python
class AgentOSExecutor:
    def __init__(self, agent_os_path, working_directory, verbose=False)

    async def execute_instruction(
        self,
        instruction_name: str,
        category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> HookResult
```

### WorkflowManager
```python
class WorkflowManager:
    def __init__(self, agent_os_path, workflows_path, working_directory)

    async def execute_workflow(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        resume_state: Optional[WorkflowState] = None
    ) -> WorkflowState
```

### AgentOSHook
```python
class AgentOSHook(BaseHook):
    def __init__(
        self,
        instruction: Optional[str] = None,
        workflow: Optional[str] = None,
        category: Optional[str] = None,
        agent_os_path: Optional[str] = None,
        resume: bool = False
    )
```

## Examples

### Basic Instruction Execution
```python
from quickhooks.agent_os import AgentOSExecutor

executor = AgentOSExecutor(verbose=True)
result = await executor.execute_instruction(
    "plan-product",
    category="core",
    context={"project_type": "web-app"}
)
```

### Custom Workflow Creation
```python
from quickhooks.agent_os.workflow_manager import WorkflowManager, WorkflowStep

manager = WorkflowManager()

# Define workflow steps
steps = [
    WorkflowStep(instruction="plan-product", category="core"),
    WorkflowStep(
        instruction="create-spec",
        category="core",
        depends_on=["plan-product"]
    ),
    WorkflowStep(
        instruction="analyze-product",
        category="core",
        depends_on=["create-spec"],
        condition="context.needs_analysis"
    )
]

# Create workflow
workflow = manager.create_workflow(
    name="custom-development",
    description="Custom development workflow",
    steps=steps
)

# Execute workflow
state = await manager.execute_workflow(
    "custom-development",
    context={"project_type": "api-service"}
)
```

### Hook Integration
```python
from quickhooks.agent_os.hooks import AgentOSHook

# Create hook for instruction execution
hook = AgentOSHook(
    instruction="create-spec",
    category="core",
    agent_os_path="~/.agent-os"
)

# Execute hook
result = await hook.execute(hook_input)
```

## Troubleshooting

### Common Issues

#### Agent OS Not Found
```
Error: Agent OS installation not found at ~/.agent-os
```
**Solution**: Install Agent OS or set custom path:
```bash
export AGENT_OS_PATH=/custom/path/to/agent-os
```

#### Instruction Not Found
```
Error: Instruction 'xyz' not found
```
**Solution**: Check available instructions:
```bash
quickhooks agent-os list-instructions
```

#### Workflow State Issues
```
Error: Cannot resume workflow - no saved state found
```
**Solution**: Start workflow without `--resume` flag or check workflow status:
```bash
quickhooks agent-os list-workflows
```

### Debug Mode
Enable verbose output for detailed execution information:
```bash
export QUICKHOOKS_AGENT_OS_VERBOSE=true
```

## Contributing

The Agent OS integration is designed to be extensible. To contribute:

1. **Core Components**: Modify files in `src/quickhooks/agent_os/`
2. **CLI Commands**: Add new commands in `src/quickhooks/cli/agent_os.py`
3. **Hooks**: Create new hooks in `hooks/` directory
4. **Documentation**: Update this file and add examples

### Testing
```bash
# Run Agent OS integration tests
uv run pytest tests/test_agent_os.py -v

# Test CLI commands
quickhooks agent-os version
quickhooks agent-os list-instructions
```

## Related Documentation

- [QuickHooks Main Documentation](../README.md)
- [Agent OS Official Documentation](https://buildermethods.com/agent-os)
- [Hook Development Guide](hook-development.md)
- [CLI Reference](cli-reference.md)

---

**QuickHooks Agent OS Integration** - Bringing spec-driven agentic development to your workflow ⚡