# QuickHooks Developer Guide

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Extending QuickHooks](#extending-quickhooks)
- [Plugin Development](#plugin-development)
- [Performance Optimization](#performance-optimization)
- [Testing Guidelines](#testing-guidelines)
- [Contributing](#contributing)

## Architecture Overview

### Core Principles
QuickHooks is built on these principles:
- **Modularity**: Each component has a single responsibility
- **Extensibility**: Easy to add new hook types and features
- **Performance**: Async-first design with efficient resource usage
- **Type Safety**: Full type annotations with Pydantic models
- **Testability**: Designed for test-driven development

### Component Architecture

```
quickhooks/
├── cli/              # Command-line interface
├── core/             # Core framework components
├── hooks/            # Hook base classes and implementations
├── agent_analysis/   # AI-powered agent analysis system
├── db/              # Database and persistence layer
├── utils/           # Utility functions and helpers
├── features/        # Feature flags and configuration
└── visualization/   # Diagram and visualization generation
```

## Core Components

### 1. BaseHook Class

The foundation for all hooks:

```python
from quickhooks.models import BaseHook, HookInput, HookOutput, HookStatus
from typing import Any, Dict
import asyncio

class CustomHook(BaseHook):
    """Base class for all QuickHooks implementations."""

    def __init__(self):
        """Initialize the hook with any required resources."""
        super().__init__()

    async def run(self, input_data: HookInput) -> HookOutput:
        """
        Main hook execution method.

        Args:
            input_data: The input data for hook execution

        Returns:
            HookOutput: Result of hook execution
        """
        try:
            # Your hook logic here
            result = await self.process_data(input_data.data)

            return HookOutput(
                status=HookStatus.SUCCESS,
                data=result,
                message="Hook executed successfully"
            )
        except Exception as e:
            return HookOutput(
                status=HookStatus.FAILED,
                error=HookError(
                    code="HOOK_ERROR",
                    message=str(e),
                    details={"input_data": input_data.dict()}
                )
            )

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override this method to implement your hook logic.

        Args:
            data: The data payload from input

        Returns:
            Processed data result
        """
        raise NotImplementedError("Subclasses must implement process_data")
```

### 2. Hook Runner

Manages hook execution and lifecycle:

```python
from quickhooks.runner import HookRunner
from quickhooks.models import HookInput

async def run_hook_example():
    """Example of running a hook programmatically."""
    runner = HookRunner()

    # Create input data
    input_data = HookInput(
        event_type="user_action",
        data={"user_id": "123", "action": "login"},
        context={"source": "web_app"}
    )

    # Execute hook
    result = await runner.run_hook("my_hook.py", input_data)

    if result.status == HookStatus.SUCCESS:
        print(f"Hook succeeded: {result.data}")
    else:
        print(f"Hook failed: {result.error.message}")
```

### 3. Test Runner

Comprehensive testing framework:

```python
from quickhooks.runner import TestRunner

# Configure test runner
runner = TestRunner(
    hooks_directory="./hooks",
    tests_directory="./tests",
    timeout=30
)

# Run tests with different options
results = runner.run_tests(
    pattern="user_*",           # Only test files matching pattern
    parallel=True,              # Run tests in parallel
    verbose=True                # Verbose output
)

# Generate different report formats
json_report = runner.generate_json_report(results)
junit_report = runner.generate_junit_report(results)
text_report = runner.generate_text_report(results)
```

### 4. Agent Analysis System

AI-powered prompt analysis:

```python
from quickhooks.agent_analysis.analyzer import AgentAnalyzer
from quickhooks.agent_analysis.types import AgentAnalysisRequest

async def analyze_prompt_example():
    """Example of prompt analysis."""
    analyzer = AgentAnalyzer(
        groq_api_key="your_api_key",
        model_name="llama-3.3-70b-versatile",
        enable_agent_discovery=True
    )

    request = AgentAnalysisRequest(
        prompt="Write a Python function that processes CSV files",
        context="Working on data import functionality",
        confidence_threshold=0.7
    )

    response = await analyzer.analyze_prompt(request)

    print(f"Recommended agents: {response.recommended_agents}")
    print(f"Modified prompt: {response.claude_code_prompt_modification}")
```

## Extending QuickHooks

### Creating Custom Hook Types

#### 1. Parallel Hook

Execute multiple operations concurrently:

```python
from quickhooks.hooks.parallel import ParallelHook
from typing import List, Dict, Any

class DataProcessingParallelHook(ParallelHook):
    """Hook that processes data in parallel."""

    async def execute_parallel_tasks(self, input_data: HookInput) -> List[Dict[str, Any]]:
        """Execute multiple data processing tasks in parallel."""
        data = input_data.data

        tasks = [
            self.validate_data(data),
            self.transform_data(data),
            self.enrich_data(data),
            self.calculate_metrics(data)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "task": i,
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "task": i,
                    "status": "success",
                    "result": result
                })

        return processed_results

    async def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data."""
        # Implementation
        return {"validation": "passed", "errors": []}

    async def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform input data."""
        # Implementation
        return {"transformed": True, "original_fields": list(data.keys())}

    async def enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich data with additional information."""
        # Implementation
        return {"enriched": True, "additional_fields": []}

    async def calculate_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics from data."""
        # Implementation
        return {"metrics": {"count": len(data), "complexity": "medium"}}
```

#### 2. Conditional Hook

Execute logic based on conditions:

```python
from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput, HookStatus

class ConditionalProcessingHook(BaseHook):
    """Hook that processes data based on conditions."""

    async def run(self, input_data: HookInput) -> HookOutput:
        """Execute conditional processing."""
        data = input_data.data
        conditions = self.evaluate_conditions(data)

        if conditions["is_premium_user"]:
            result = await self.process_premium_data(data)
        elif conditions["is_new_user"]:
            result = await self.process_new_user_data(data)
        else:
            result = await self.process_standard_data(data)

        return HookOutput(
            status=HookStatus.SUCCESS,
            data=result,
            metadata={"conditions_met": conditions}
        )

    def evaluate_conditions(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """Evaluate processing conditions."""
        return {
            "is_premium_user": data.get("user_type") == "premium",
            "is_new_user": data.get("account_age_days", 0) < 7,
            "has_complex_data": len(data.get("data_points", [])) > 100
        }

    async def process_premium_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data for premium users."""
        # Premium processing logic
        return {"processed_as": "premium", "features": ["advanced_analytics"]}

    async def process_new_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data for new users."""
        # New user processing logic
        return {"processed_as": "new_user", "features": ["onboarding"]}

    async def process_standard_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process standard user data."""
        # Standard processing logic
        return {"processed_as": "standard", "features": ["basic_processing"]}
```

### Adding Custom Commands

Extend the CLI with custom commands:

```python
# in quickhooks/cli/custom.py
import typer
from quickhooks import console

custom_app = typer.Typer(
    name="custom",
    help="Custom commands for specialized functionality"
)

@custom_app.command()
def deploy(
    environment: str = typer.Option(..., help="Target environment"),
    dry_run: bool = typer.Option(False, help="Perform dry run only")
):
    """Deploy hooks to specified environment."""
    console.print(f"Deploying to {environment}")

    if dry_run:
        console.print("🔍 Dry run mode - no changes made")
    else:
        # Actual deployment logic
        console.print("✅ Deployment completed")

@custom_app.command()
def validate(
    config_file: str = typer.Option("config.yaml", help="Configuration file"),
    strict: bool = typer.Option(False, help="Strict validation mode")
):
    """Validate hook configuration."""
    console.print(f"Validating configuration from {config_file}")

    if strict:
        console.print("🔒 Strict validation enabled")

    # Validation logic
    console.print("✅ Configuration is valid")

# Add to main CLI
from quickhooks.cli.main import app
app.add_typer(custom_app, name="custom")
```

## Plugin Development

### Plugin Architecture

Create plugins that extend QuickHooks functionality:

```python
# plugins/analytics_plugin.py
from quickhooks.plugins import BasePlugin
from typing import Dict, Any, List

class AnalyticsPlugin(BasePlugin):
    """Plugin for analytics and reporting."""

    name = "analytics"
    version = "1.0.0"
    description = "Provides analytics and reporting capabilities"

    def __init__(self):
        super().__init__()
        self.metrics_collector = MetricsCollector()

    async def on_hook_execution_start(self, hook_id: str, input_data: HookInput):
        """Called when hook execution starts."""
        self.metrics_collector.record_start(hook_id)

    async def on_hook_execution_complete(self, hook_id: str, output_data: HookOutput):
        """Called when hook execution completes."""
        self.metrics_collector.record_completion(hook_id, output_data)

    async def generate_report(self, time_range: str) -> Dict[str, Any]:
        """Generate analytics report."""
        return {
            "total_hooks": self.metrics_collector.get_total_hooks(),
            "success_rate": self.metrics_collector.get_success_rate(),
            "average_execution_time": self.metrics_collector.get_avg_execution_time(),
            "top_performing_hooks": self.metrics_collector.get_top_hooks(10)
        }

class MetricsCollector:
    """Collects and stores hook execution metrics."""

    def __init__(self):
        self.metrics = {}

    def record_start(self, hook_id: str):
        """Record the start of hook execution."""
        self.metrics[hook_id] = {
            "start_time": time.time(),
            "executions": []
        }

    def record_completion(self, hook_id: str, output_data: HookOutput):
        """Record the completion of hook execution."""
        if hook_id in self.metrics:
            execution_time = time.time() - self.metrics[hook_id]["start_time"]
            self.metrics[hook_id]["executions"].append({
                "execution_time": execution_time,
                "status": output_data.status,
                "timestamp": datetime.now()
            })
```

### Plugin Registration

Register plugins in your configuration:

```python
# quickhooks/plugins/registry.py
from typing import Dict, Type
from .base import BasePlugin
from .analytics_plugin import AnalyticsPlugin
from .monitoring_plugin import MonitoringPlugin

class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self):
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self._instances: Dict[str, BasePlugin] = {}

        # Register built-in plugins
        self.register_plugin("analytics", AnalyticsPlugin)
        self.register_plugin("monitoring", MonitoringPlugin)

    def register_plugin(self, name: str, plugin_class: Type[BasePlugin]):
        """Register a plugin class."""
        self._plugins[name] = plugin_class

    def get_plugin(self, name: str) -> BasePlugin:
        """Get a plugin instance."""
        if name not in self._instances:
            if name in self._plugins:
                self._instances[name] = self._plugins[name]()
            else:
                raise ValueError(f"Plugin '{name}' not found")

        return self._instances[name]

    def list_plugins(self) -> List[str]:
        """List all registered plugins."""
        return list(self._plugins.keys())

# Global plugin registry
plugin_registry = PluginRegistry()
```

## Performance Optimization

### Async Patterns

Use async/await for I/O-bound operations:

```python
import asyncio
import aiohttp
from typing import List, Dict

class OptimizedDataProcessor(BaseHook):
    """Optimized hook using async patterns."""

    async def run(self, input_data: HookInput) -> HookOutput:
        """Process data with optimized async patterns."""
        urls = input_data.data.get("urls", [])

        # Process URLs concurrently
        results = await asyncio.gather(
            *[self.fetch_url(url) for url in urls],
            return_exceptions=True
        )

        # Filter successful results
        successful_results = [
            result for result in results
            if not isinstance(result, Exception)
        ]

        return HookOutput(
            status=HookStatus.SUCCESS,
            data={"processed_urls": successful_results, "total": len(urls)}
        )

    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch URL with connection pooling."""
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                return {
                    "url": url,
                    "status": response.status,
                    "content_length": len(await response.text())
                }
```

### Caching Strategies

Implement caching for expensive operations:

```python
from functools import lru_cache
import asyncio
from typing import Dict, Any

class CachedDataHook(BaseHook):
    """Hook with intelligent caching."""

    def __init__(self):
        super().__init__()
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    @lru_cache(maxsize=128)
    async def get_expensive_data(self, key: str) -> Dict[str, Any]:
        """Get expensive data with caching."""
        # Check cache first
        if key in self._cache:
            cached_item = self._cache[key]
            if time.time() - cached_item["timestamp"] < self._cache_ttl:
                return cached_item["data"]

        # Expensive operation
        result = await self.compute_expensive_data(key)

        # Cache the result
        self._cache[key] = {
            "data": result,
            "timestamp": time.time()
        }

        return result

    async def compute_expensive_data(self, key: str) -> Dict[str, Any]:
        """Simulate expensive computation."""
        await asyncio.sleep(1)  # Simulate work
        return {"key": key, "value": f"computed_value_for_{key}"}
```

### Resource Management

Manage resources efficiently:

```python
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class ResourceManagedHook(BaseHook):
    """Hook with proper resource management."""

    def __init__(self):
        super().__init__()
        self._connection_pool = None
        self._semaphore = asyncio.Semaphore(10)  # Limit concurrent operations

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator:
        """Context manager for database connections."""
        if not self._connection_pool:
            self._connection_pool = await self.create_connection_pool()

        async with self._connection_pool.acquire() as connection:
            try:
                yield connection
            finally:
                # Connection automatically returned to pool
                pass

    async def run(self, input_data: HookInput) -> HookOutput:
        """Run with proper resource management."""
        async with self._semaphore:  # Limit concurrent operations
            async with self.get_connection() as connection:
                # Use connection safely
                result = await self.process_with_connection(
                    connection, input_data.data
                )

                return HookOutput(
                    status=HookStatus.SUCCESS,
                    data=result
                )

    async def create_connection_pool(self):
        """Create a connection pool."""
        # Implementation depends on your database
        pass

    async def process_with_connection(self, connection, data):
        """Process data using database connection."""
        # Implementation
        pass
```

## Testing Guidelines

### Test Structure

Follow this testing structure:

```python
# tests/test_custom_hook.py
import pytest
from unittest.mock import AsyncMock, patch
from quickhooks.models import HookInput, HookOutput, HookStatus, HookError
from hooks.custom_hook import CustomHook

class TestCustomHook:
    """Test suite for CustomHook."""

    @pytest.fixture
    def hook(self):
        """Create hook instance for testing."""
        return CustomHook()

    @pytest.fixture
    def valid_input(self):
        """Create valid input data."""
        return HookInput(
            event_type="test_event",
            data={"key": "value"},
            context={"test": True}
        )

    @pytest.mark.asyncio
    async def test_successful_execution(self, hook, valid_input):
        """Test successful hook execution."""
        result = await hook.run(valid_input)

        assert result.status == HookStatus.SUCCESS
        assert result.data is not None
        assert result.message is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, hook):
        """Test error handling."""
        invalid_input = HookInput(
            event_type="test_event",
            data={},  # Missing required data
        )

        result = await hook.run(invalid_input)

        assert result.status == HookStatus.FAILED
        assert result.error is not None
        assert result.error.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    @patch('hooks.custom_hook.external_service_call')
    async def test_with_mocks(self, mock_service, hook, valid_input):
        """Test hook behavior with mocked dependencies."""
        # Configure mock
        mock_service.return_value = {"mocked": "result"}

        result = await hook.run(valid_input)

        # Verify mock was called
        mock_service.assert_called_once()

        # Verify result
        assert result.status == HookStatus.SUCCESS
        assert "mocked" in result.data
```

### Integration Tests

Test hook integration:

```python
# tests/integration/test_hook_integration.py
import pytest
from quickhooks.runner import HookRunner, TestRunner

class TestHookIntegration:
    """Integration tests for hooks."""

    @pytest.mark.asyncio
    async def test_hook_runner_integration(self):
        """Test hook runner with real files."""
        runner = HookRunner()

        input_data = HookInput(
            event_type="integration_test",
            data={"test_data": "value"}
        )

        result = await runner.run_hook(
            "hooks/integration_test_hook.py",
            input_data
        )

        assert result.status == HookStatus.SUCCESS

    def test_test_runner_integration(self):
        """Test test runner with real test files."""
        runner = TestRunner(
            hooks_directory="./hooks",
            tests_directory="./tests/integration"
        )

        results = runner.run_tests(
            pattern="integration_*",
            parallel=False  # Sequential for integration tests
        )

        # Verify all integration tests passed
        for test_name, test_result in results.items():
            assert test_result.passed, f"Integration test {test_name} failed"
```

### Performance Tests

Test hook performance:

```python
# tests/performance/test_hook_performance.py
import pytest
import time
from quickhooks.models import HookInput
from hooks.performance_hook import PerformanceHook

class TestHookPerformance:
    """Performance tests for hooks."""

    @pytest.mark.asyncio
    async def test_execution_time(self):
        """Test hook execution time."""
        hook = PerformanceHook()

        input_data = HookInput(
            event_type="performance_test",
            data={"size": 1000}  # Test with larger data
        )

        start_time = time.time()
        result = await hook.run(input_data)
        execution_time = time.time() - start_time

        # Assert execution time is reasonable
        assert execution_time < 1.0  # Should complete within 1 second
        assert result.execution_time < 1.0

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test hook memory usage."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        hook = PerformanceHook()

        # Run hook multiple times
        for i in range(100):
            input_data = HookInput(
                event_type="memory_test",
                data={"iteration": i}
            )
            await hook.run(input_data)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Assert memory usage is reasonable
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase
```

## Contributing

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kivo360/quickhooks.git
   cd quickhooks
   ```

2. **Set up development environment**:
   ```bash
   uv sync --all-extras
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Code Style

Follow these coding standards:

- **Type Hints**: All functions should have type hints
- **Docstrings**: Use comprehensive docstrings
- **Error Handling**: Proper exception handling with meaningful error messages
- **Async/Await**: Use async patterns for I/O operations
- **Testing**: Write tests for all new functionality

Example of well-structured code:

```python
from typing import Dict, Any, Optional
from quickhooks.models import BaseHook, HookInput, HookOutput, HookStatus
import logging

logger = logging.getLogger(__name__)

class WellStructuredHook(BaseHook):
    """Example of a well-structured hook.

    This hook demonstrates best practices for QuickHooks development.

    Attributes:
        config: Configuration dictionary for the hook
        initialized: Whether the hook has been initialized
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the hook with optional configuration.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__()
        self.config = config or {}
        self.initialized = False
        self._initialize()

    def _initialize(self) -> None:
        """Initialize hook resources."""
        try:
            # Initialize resources
            self.initialized = True
            logger.info("Hook initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize hook: {e}")
            raise

    async def run(self, input_data: HookInput) -> HookOutput:
        """Execute the hook with proper error handling.

        Args:
            input_data: The input data for hook execution

        Returns:
            HookOutput: Result of hook execution

        Raises:
            ValueError: If input data is invalid
            RuntimeError: If hook is not initialized
        """
        if not self.initialized:
            raise RuntimeError("Hook not properly initialized")

        if not input_data.data:
            raise ValueError("Input data cannot be empty")

        try:
            result = await self._process_data(input_data.data)

            return HookOutput(
                status=HookStatus.SUCCESS,
                data=result,
                message="Hook executed successfully"
            )
        except Exception as e:
            logger.error(f"Hook execution failed: {e}")

            return HookOutput(
                status=HookStatus.FAILED,
                error=HookError(
                    code="EXECUTION_ERROR",
                    message=str(e),
                    details={"input_data": input_data.dict()}
                )
            )

    async def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data.

        Args:
            data: The data to process

        Returns:
            Processed data result
        """
        # Implementation here
        return {"processed": True, "original_data": data}
```

### Submitting Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code following the style guidelines
   - Add comprehensive tests
   - Update documentation

3. **Run quality checks**:
   ```bash
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   uv run mypy src/quickhooks
   uv run pytest tests/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   # Create Pull Request on GitHub
   ```

### Pull Request Guidelines

- **Clear description**: Explain what the PR does and why
- **Testing**: Include tests for new functionality
- **Documentation**: Update relevant documentation
- **Breaking changes**: Clearly label any breaking changes
- **Changelog**: Update CHANGELOG.md for user-facing changes

### Review Process

- **Automated checks**: CI/CD pipeline runs tests and quality checks
- **Code review**: Maintainers review code for quality and consistency
- **Testing**: All tests must pass before merge
- **Documentation**: Documentation must be updated for API changes

This developer guide provides comprehensive information for extending and contributing to QuickHooks. For more specific questions, refer to the API documentation or open an issue on GitHub.