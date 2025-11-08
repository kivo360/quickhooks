# QuickHooks User Guide

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Basic Concepts](#basic-concepts)
- [Creating Your First Hook](#creating-your-first-hook)
- [Agent Analysis](#agent-analysis)
- [Testing Hooks](#testing-hooks)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
- Python 3.12 or higher
- UV package manager (recommended)
- Groq API key (for agent analysis features)

### Option 1: Install with UV (Recommended)

1. **Install UV** if you haven't already:
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows PowerShell
   powershell -ExecutionPolicy ByPass -c "irm https://uv.sh/uv.ps1 | iex"
   ```

2. **Install QuickHooks**:
   ```bash
   uv add quickhooks
   ```

3. **Set up your Groq API key**:
   ```bash
   export GROQ_API_KEY=your_groq_api_key_here
   ```

### Option 2: Install from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kivo360/quickhooks.git
   cd quickhooks
   ```

2. **Install dependencies**:
   ```bash
   uv sync --all-extras
   ```

### Option 3: Install with pip (when published)

```bash
pip install quickhooks[agent-analysis]
```

## Quick Start

### 1. Verify Installation

```bash
quickhooks version
```

You should see: `QuickHooks v0.1.1`

### 2. Test Basic Functionality

```bash
quickhooks hello
```

### 3. Create Your First Hook

Create a file called `hello_hook.py`:

```python
from quickhooks.models import BaseHook, HookInput, HookOutput, HookStatus

class HelloHook(BaseHook):
    """A simple hook that greets users."""

    async def run(self, input_data: HookInput) -> HookOutput:
        """Execute the hook logic."""
        name = input_data.data.get("name", "World")

        return HookOutput(
            status=HookStatus.SUCCESS,
            data={"greeting": f"Hello, {name}!"},
            message="Greeting generated successfully"
        )
```

### 4. Run Your Hook

```bash
quickhooks run hello_hook.py --input '{"name": "QuickHooks"}'
```

## Basic Concepts

### Hooks
Hooks are the core building blocks of QuickHooks. A hook is a Python class that:
- Inherits from `BaseHook`
- Implements the `run` method
- Takes `HookInput` and returns `HookOutput`

### Hook Input Structure
```python
HookInput(
    event_type="user_action",           # What triggered the hook
    data={"user_id": "123"},           # Event data
    timestamp=datetime.now(),           # When it happened
    context={},                        # Additional context
    metadata=HookMetadata(...)         # Metadata information
)
```

### Hook Output Structure
```python
HookOutput(
    status=HookStatus.SUCCESS,          # Execution status
    data={"result": "value"},          # Result data
    message="Operation completed",      # User message
    error=None,                        # Error info if failed
    execution_time=1.23                 # Performance metrics
)
```

### Agent Analysis
QuickHooks can analyze your prompts and recommend the best Claude Code agents:
- **Automatic Discovery**: Scans your `~/.claude/agents` directory
- **Semantic Matching**: Uses AI to match prompts to agent capabilities
- **Prompt Enhancement**: Modifies prompts to ensure proper agent usage

## Creating Your First Hook

### Step 1: Define Your Hook Class

Create a new Python file with your hook class:

```python
from quickhooks.models import BaseHook, HookInput, HookOutput, HookStatus
from typing import Any, Dict

class DataProcessorHook(BaseHook):
    """Processes user data and validates it."""

    async def run(self, input_data: HookInput) -> HookOutput:
        """Process and validate user data."""
        try:
            # Extract data from input
            user_data = input_data.data.get("user_data", {})

            # Validate required fields
            if not user_data.get("email"):
                return HookOutput(
                    status=HookStatus.FAILED,
                    error=HookError(
                        code="VALIDATION_ERROR",
                        message="Email is required"
                    )
                )

            # Process the data
            processed_data = {
                "email": user_data["email"],
                "name": user_data.get("name", "Unknown"),
                "normalized_email": user_data["email"].lower().strip(),
                "has_phone": bool(user_data.get("phone"))
            }

            return HookOutput(
                status=HookStatus.SUCCESS,
                data=processed_data,
                message="User data processed successfully"
            )

        except Exception as e:
            return HookOutput(
                status=HookStatus.FAILED,
                error=HookError(
                    code="PROCESSING_ERROR",
                    message=str(e)
                )
            )
```

### Step 2: Create a Test File

Create `test_data_processor.py`:

```python
import pytest
from quickhooks.models import HookInput, HookStatus
from data_processor_hook import DataProcessorHook

@pytest.mark.asyncio
async def test_data_processor_valid_input():
    """Test with valid user data."""
    hook = DataProcessorHook()
    input_data = HookInput(
        event_type="user_registration",
        data={
            "user_data": {
                "email": "USER@EXAMPLE.COM",
                "name": "John Doe",
                "phone": "555-1234"
            }
        }
    )

    result = await hook.run(input_data)

    assert result.status == HookStatus.SUCCESS
    assert result.data["normalized_email"] == "user@example.com"
    assert result.data["has_phone"] is True

@pytest.mark.asyncio
async def test_data_processor_missing_email():
    """Test with missing email."""
    hook = DataProcessorHook()
    input_data = HookInput(
        event_type="user_registration",
        data={"user_data": {"name": "John Doe"}}
    )

    result = await hook.run(input_data)

    assert result.status == HookStatus.FAILED
    assert result.error.code == "VALIDATION_ERROR"
```

### Step 3: Run Tests

```bash
quickhooks test --hooks-dir ./ --tests-dir ./tests --verbose
```

## Agent Analysis

### Analyze a Prompt

Use the agent analysis feature to get recommendations for your prompts:

```bash
quickhooks agents analyze "Write a Python function that processes user data and validates email formats"
```

### Example Response

```json
{
  "analysis_summary": "The prompt requires coding and data validation capabilities",
  "threshold_met": true,
  "recommended_agents": [
    {
      "agent_type": "coding",
      "confidence": 0.92,
      "priority": 1,
      "reasoning": "The prompt involves writing Python code with data validation"
    }
  ],
  "claude_code_prompt_modification": "Use the coding agent to write a Python function that processes user data and validates email formats"
}
```

### Include Context

Provide additional context for better analysis:

```bash
quickhooks agents analyze "Debug this authentication issue" \
  --context "Working on a Flask application with JWT authentication" \
  --threshold 0.8
```

### Discover Local Agents

If you have custom agents in `~/.claude/agents`, QuickHooks will automatically discover and prioritize them:

```bash
# QuickHooks will scan your local agents first
quickhooks agents analyze "Analyze this financial data"
```

## Testing Hooks

### Test Structure

Organize your tests like this:

```
project/
├── hooks/
│   ├── data_processor.py
│   ├── auth_validator.py
│   └── notification_sender.py
├── tests/
│   ├── test_data_processor.py
│   ├── test_auth_validator.py
│   └── test_notification_sender.py
```

### Running Tests

**Basic test run:**
```bash
quickhooks test
```

**Run tests in parallel:**
```bash
quickhooks test --parallel
```

**Generate JSON report:**
```bash
quickhooks test --format json > test_report.json
```

**Run specific test pattern:**
```bash
quickhooks test --pattern "data_processor"
```

### Test Output Examples

**Text format:**
```
Test Results Summary:
====================
Total Tests: 5
Passed: 4
Failed: 1
Execution Time: 2.34s

Failed Tests:
- test_auth_validator_invalid_token: AssertionError: Expected status FAILED but got SUCCESS
```

**JSON format:**
```json
{
  "total_tests": 5,
  "passed_tests": 4,
  "failed_tests": 1,
  "execution_time": 2.34,
  "results": {
    "test_data_processor_valid_input": {
      "passed": true,
      "execution_time": 0.12,
      "output": "✓ Test passed"
    }
  }
}
```

## Development Workflow

### 1. Development Server

Start the development server with hot reload:

```bash
quickhooks-dev run hooks/ --delay 0.5
```

The server will automatically restart when you make changes to your hooks.

### 2. Write Tests First (TDD)

Follow the test-driven development approach:

```python
# 1. Write the test first
@pytest.mark.asyncio
async def test_email_validation():
    hook = EmailValidatorHook()
    input_data = HookInput(
        event_type="validation",
        data={"email": "invalid-email"}
    )

    result = await hook.run(input_data)
    assert result.status == HookStatus.FAILED
    assert "invalid" in result.error.message.lower()

# 2. Run the test (it will fail)
# 3. Implement the hook to make the test pass
# 4. Refactor and improve
```

### 3. Use Agent Analysis for Complex Tasks

When working on complex features, use agent analysis:

```bash
# Get recommendations for implementing a feature
quickhooks agents analyze "Create a hook that processes CSV files and validates data structure"

# Use the recommended agent approach in your implementation
```

### 4. Continuous Integration

Add QuickHooks testing to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Test Hooks
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: astral-sh/setup-uv@v2
    - run: uv sync --all-extras
    - run: quickhooks test --format junit --timeout 60
```

## Troubleshooting

### Common Issues

#### "GROQ_API_KEY environment variable must be set"
**Solution**: Set your Groq API key:
```bash
export GROQ_API_KEY=your_api_key_here
```

#### "No hook class found in the module"
**Solution**: Make sure your hook file contains a class that inherits from `BaseHook`:
```python
from quickhooks.models import BaseHook

class MyHook(BaseHook):  # Must inherit from BaseHook
    async def run(self, input_data):
        return HookOutput(status=HookStatus.SUCCESS)
```

#### "Invalid JSON input"
**Solution**: Ensure your input JSON is properly formatted:
```bash
# Correct
quickhooks run my_hook.py --input '{"key": "value"}'

# Incorrect - missing quotes
quickhooks run my_hook.py --input '{key: value}'
```

#### Tests are not found
**Solution**: Check your directory structure:
```bash
# Correct structure
project/
├── hooks/
├── tests/

# Run with correct paths
quickhooks test --hooks-dir hooks/ --tests-dir tests/
```

### Debug Mode

Enable verbose output for debugging:

```bash
quickhooks test --verbose
quickhooks run my_hook.py --input '{"data": "test"}' --verbose
```

### Getting Help

- Check the logs for detailed error messages
- Use `--verbose` flag to see more information
- Review the [API Documentation](../api/README.md)
- Open an issue on GitHub

## Next Steps

- Read the [Developer Guide](../developer/README.md)
- Explore the [API Reference](../api/README.md)
- Check out [Examples](../examples/README.md)
- Learn about [Advanced Features](../advanced/README.md)