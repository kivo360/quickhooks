"""AI-powered scaffolding CLI commands for QuickHooks."""

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from quickhooks.config import get_global_hooks_dir
from quickhooks.features import has_feature, require_feature

console = Console()
app = cyclopts.App(help="AI-powered scaffolding and project generation")


@app.command
def project(
    name: Annotated[str, Parameter(help="Project name")],
    project_type: Annotated[
        str, Parameter("--type", alias="-t", help="Type of project to scaffold")
    ] = "web-app",
    description: Annotated[
        str, Parameter("--description", alias="-d", help="Project description")
    ] = "",
    interactive: Annotated[
        bool, Parameter("--interactive", alias="-i", help="Interactive mode")
    ] = False,
    output_dir: Annotated[
        Path | None, Parameter("--output", alias="-o", help="Output directory")
    ] = None,
) -> None:
    """Generate a new project using AI-powered scaffolding.

    Args:
        name: Project name
        project_type: Type of project (web-app, api, cli, library, etc.)
        description: Project description
        interactive: Enable interactive mode
        output_dir: Output directory (defaults to current directory)
    """
    require_feature("scaffold")

    if interactive:
        name = Prompt.ask("Project name", default=name)
        project_type = Prompt.ask("Project type", default=project_type)
        description = Prompt.ask("Project description", default=description)

    if output_dir is None:
        output_dir = Path.cwd() / name

    console.print(f"🏗️ Scaffolding project: {name}", style="bold green")
    console.print(f"Type: {project_type}")
    console.print(f"Description: {description}")
    console.print(f"Output: {output_dir}")

    # For now, create a basic project structure
    # In a full implementation, this would use AI to generate based on requirements
    _create_basic_project_structure(output_dir, name, project_type, description)

    console.print("✅ Project scaffolded successfully!", style="green")


@app.command
def hook(
    name: Annotated[str, Parameter(help="Hook name")],
    description: Annotated[
        str, Parameter("--description", alias="-d", help="Hook description")
    ] = "",
    hook_type: Annotated[
        str, Parameter("--type", alias="-t", help="Hook type")
    ] = "transformer",
    complexity: Annotated[
        str, Parameter("--complexity", alias="-c", help="Hook complexity")
    ] = "simple",
    global_hook: Annotated[
        bool, Parameter("--global", alias="-g", help="Create as global hook")
    ] = False,
    with_tests: Annotated[
        bool, Parameter("--tests/--no-tests", help="Generate tests")
    ] = True,
    interactive: Annotated[
        bool, Parameter("--interactive", alias="-i", help="Interactive mode")
    ] = False,
) -> None:
    """Generate a new hook using AI-powered scaffolding.

    Args:
        name: Hook name
        description: Hook description
        hook_type: Hook type (validator, transformer, analyzer, etc.)
        complexity: Hook complexity (simple, moderate, advanced, expert)
        global_hook: Create as global hook
        with_tests: Generate tests
        interactive: Enable interactive mode
    """
    require_feature("scaffold")

    if interactive:
        name = Prompt.ask("Hook name", default=name)
        description = Prompt.ask("Hook description", default=description)
        hook_type = Prompt.ask("Hook type", default=hook_type)
        complexity = Prompt.ask("Hook complexity", default=complexity)
        global_hook = Confirm.ask("Create as global hook?", default=global_hook)
        with_tests = Confirm.ask("Generate tests?", default=with_tests)

    console.print(f"🪝 Scaffolding hook: {name}", style="bold green")
    console.print(f"Type: {hook_type}")
    console.print(f"Complexity: {complexity}")
    console.print(f"Global: {global_hook}")

    # Determine output directory
    if global_hook:
        output_dir = get_global_hooks_dir() / "hooks"
    else:
        output_dir = Path.cwd() / "hooks"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate hook file
    hook_file = output_dir / f"{name}.py"
    hook_content = _generate_hook_content(name, description, hook_type, complexity)

    with open(hook_file, "w", encoding="utf-8") as f:
        f.write(hook_content)

    console.print(f"Created hook: {hook_file}")

    # Generate tests if requested
    if with_tests:
        test_file = output_dir / "tests" / f"test_{name}.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)

        test_content = _generate_test_content(name, hook_type)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        console.print(f"Created test: {test_file}")

    console.print("✅ Hook scaffolded successfully!", style="green")


@app.command
def template(
    name: Annotated[str, Parameter(help="Template name")],
    template_type: Annotated[
        str, Parameter("--type", alias="-t", help="Template type")
    ] = "hook",
    description: Annotated[
        str, Parameter("--description", alias="-d", help="Template description")
    ] = "",
    variables: Annotated[
        str, Parameter("--vars", alias="-v", help="Template variables (JSON)")
    ] = "",
) -> None:
    """Create a new Jinja2 template for scaffolding.

    Args:
        name: Template name
        template_type: Template type (hook, config, cli, etc.)
        description: Template description
        variables: Template variables as JSON
    """
    require_feature("scaffold")

    console.print(f"📝 Creating template: {name}", style="bold green")
    console.print(f"Type: {template_type}")
    console.print(f"Description: {description}")

    # Parse variables
    template_vars = {}
    if variables:
        try:
            template_vars = json.loads(variables)
        except json.JSONDecodeError:
            console.print("Invalid JSON for variables", style="red")
            sys.exit(1)

    # Create template directory
    template_dir = Path.cwd() / "templates"
    template_dir.mkdir(exist_ok=True)

    # Generate template file
    template_file = template_dir / f"{name}.j2"
    template_content = _generate_template_content(
        name, template_type, description, template_vars
    )

    with open(template_file, "w", encoding="utf-8") as f:
        f.write(template_content)

    console.print(f"Created template: {template_file}")
    console.print("✅ Template created successfully!", style="green")


@app.command
def list_templates() -> None:
    """List available scaffolding templates."""
    require_feature("scaffold")

    console.print("Available Templates:", style="bold")

    # Built-in templates
    builtin_templates = [
        ("hook", "Basic hook template"),
        ("validator", "Validation hook template"),
        ("transformer", "Transformation hook template"),
        ("analyzer", "Analysis hook template"),
        ("config", "Configuration class template"),
        ("cli", "CLI command template"),
    ]

    table = Table(title="Built-in Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="dim")

    for name, desc in builtin_templates:
        table.add_row(name, desc)

    console.print(table)

    # Custom templates
    template_dir = Path.cwd() / "templates"
    if template_dir.exists():
        custom_templates = list(template_dir.glob("*.j2"))
        if custom_templates:
            console.print("\nCustom Templates:", style="bold")
            for template_file in custom_templates:
                console.print(f"• {template_file.stem}")


@app.command
def analyze(
    requirements: Annotated[str, Parameter(help="Project requirements description")],
    format: Annotated[
        str, Parameter("--format", alias="-f", help="Output format (text, json)")
    ] = "text",
) -> None:
    """Analyze requirements and suggest scaffolding approach.

    Args:
        requirements: Description of what you want to build
        format: Output format (text or json)
    """
    if has_feature("ai"):
        require_feature("ai")
        console.print("🤖 Analyzing requirements with AI...", style="bold blue")
    else:
        console.print("📋 Analyzing requirements...", style="bold blue")

    # Simple rule-based analysis (would use AI in full implementation)
    analysis = _analyze_requirements(requirements)

    if format == "json":
        console.print(json.dumps(analysis, indent=2))
    else:
        _print_analysis(analysis)


def _create_basic_project_structure(
    output_dir: Path, name: str, project_type: str, description: str
) -> None:
    """Create basic project structure."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create basic files
    files = {
        "README.md": f"# {name}\n\n{description}\n\n## Project Type\n{project_type}\n",
        "pyproject.toml": _generate_pyproject_toml(name, description),
        "src/__init__.py": "",
        f"src/{name}/__init__.py": f'"""Package {name}."""\n__version__ = "0.1.0"\n',
        f"src/{name}/main.py": _generate_main_py(name, project_type),
        "tests/__init__.py": "",
        f"tests/test_{name}.py": _generate_project_test(name),
    }

    for file_path, content in files.items():
        full_path = output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)


def _generate_hook_content(
    name: str, description: str, hook_type: str, complexity: str
) -> str:
    """Generate hook content based on parameters."""
    return f'''"""AI-generated hook: {name}."""

from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput


class {name.title().replace("_", "")}Hook(BaseHook):
    """{"".join(description) or f"{hook_type.title()} hook for {name}"}."""

    name = "{name}"
    version = "1.0.0"
    description = "{description or f"{hook_type.title()} hook"}"
    hook_type = "{hook_type}"
    complexity = "{complexity}"

    def process(self, hook_input: HookInput) -> HookOutput:
        """Process the hook input.

        Args:
            hook_input: Input data for the hook

        Returns:
            Processed hook output
        """
        # TODO: Implement your {hook_type} logic here

        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message=f"{hook_type.title()} hook processed successfully"
        )
'''


def _generate_test_content(name: str, hook_type: str) -> str:
    """Generate test content for the hook."""
    class_name = name.title().replace("_", "") + "Hook"
    return f'''"""Tests for {name} hook."""

import pytest
from quickhooks.models import HookInput, ExecutionContext
from hooks.{name} import {class_name}


def test_{name}_basic():
    """Test basic {name} functionality."""
    hook = {class_name}()

    # Create test input
    hook_input = HookInput(
        tool_name="TestTool",
        tool_input={{"data": "test"}},
        context=ExecutionContext()
    )

    # Process the hook
    result = hook.process(hook_input)

    # Verify results
    assert result.allowed is True
    assert result.tool_name == "TestTool"
    assert result.tool_input["data"] == "test"


def test_{name}_error_handling():
    """Test {name} error handling."""
    hook = {class_name}()

    # Test with invalid input
    hook_input = HookInput(
        tool_name="TestTool",
        tool_input={{}},  # Empty input
        context=ExecutionContext()
    )

    # Should handle gracefully
    result = hook.process(hook_input)
    assert isinstance(result.allowed, bool)
    assert result.message is not None


@pytest.mark.parametrize("test_input,expected", [
    ({{"data": "test1"}}, True),
    ({{"data": "test2"}}, True),
    ({{}}, True),  # Should handle empty input
])
def test_{name}_parametrized(test_input, expected):
    """Parametrized tests for {name}."""
    hook = {class_name}()

    hook_input = HookInput(
        tool_name="TestTool",
        tool_input=test_input,
        context=ExecutionContext()
    )

    result = hook.process(hook_input)
    assert isinstance(result.allowed, bool) == expected
'''


def _generate_template_content(
    name: str, template_type: str, description: str, variables: dict
) -> str:
    """Generate Jinja2 template content."""
    return f'''{{{{- """
Template: {name}
Type: {template_type}
Description: {description}
Variables: {list(variables.keys()) if variables else "None"}
""" -}}}}

{{% if template_type == "hook" %}}
"""{{{{ description or 'Generated hook' }}}}."""

from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput


class {{{{ class_name }}}}Hook(BaseHook):
    """{{{{ description or 'Generated hook' }}}}."""

    name = "{{{{ name }}}}"
    version = "{{{{ version or '1.0.0' }}}}"
    description = "{{{{ description }}}}"

    def process(self, hook_input: HookInput) -> HookOutput:
        """Process the hook input."""
        # TODO: Implement hook logic

        return HookOutput(
            allowed=True,
            modified=False,
            tool_name=hook_input.tool_name,
            tool_input=hook_input.tool_input,
            message="Hook processed successfully"
        )

{{% elif template_type == "config" %}}
"""Configuration for {{{{ name }}}}."""

from pydantic import BaseModel, Field
from typing import Optional


class {{{{ class_name }}}}Config(BaseModel):
    """Configuration model for {{{{ name }}}}."""

    {{% for var_name, var_info in variables.items() %}}
    {{{{ var_name }}}}: {{{{ var_info.get('type', 'str') }}}} = Field(
        default={{{{ var_info.get('default', 'None') }}}},
        description="{{{{ var_info.get('description', '') }}}}"
    )
    {{% endfor %}}

{{% else %}}
# Template for {{{{ template_type }}}}
# Generated by QuickHooks scaffolding system

{{{{ content or '# Add your content here' }}}}
{{% endif %}}
'''


def _generate_pyproject_toml(name: str, description: str) -> str:
    """Generate pyproject.toml for new project."""
    return f'''[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
authors = [
    {{name = "Your Name", email = "your.email@example.com"}}
]
requires-python = ">=3.12"
dependencies = [
    "quickhooks>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.1.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=src", "--cov-report=term-missing"]
'''


def _generate_main_py(name: str, project_type: str) -> str:
    """Generate main.py based on project type."""
    if project_type in ["api", "web-app"]:
        return f'''"""Main module for {name}."""

from fastapi import FastAPI

app = FastAPI(title="{name}", description="Generated by QuickHooks")


@app.get("/")
async def root():
    return {{"message": "Hello from {name}!"}}


@app.get("/health")
async def health():
    return {{"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    if project_type == "cli":
        return f'''"""CLI application for {name}."""

import cyclopts
from cyclopts import Parameter
from rich.console import Console

app = cyclopts.App(name="{name}")
console = Console()


@app.command
def hello(name: str = Parameter("World", help="Name to greet")):
    """Say hello."""
    console.print(f"Hello {{name}}!")


@app.command
def version():
    """Show version."""
    console.print("{name} v0.1.0")


if __name__ == "__main__":
    app()
'''
    return f'''"""Main module for {name}."""


def main():
    """Main function for {name}."""
    print("Hello from {name}!")


if __name__ == "__main__":
    main()
'''


def _generate_project_test(name: str) -> str:
    """Generate basic project test."""
    return f'''"""Tests for {name}."""

import pytest


def test_basic():
    """Basic test for {name}."""
    assert True  # Replace with actual tests


def test_import():
    """Test that we can import the package."""
    import {name}
    assert hasattr({name}, '__version__')
'''


def _analyze_requirements(requirements: str) -> dict:
    """Analyze requirements and suggest scaffolding approach."""
    requirements_lower = requirements.lower()

    # Simple keyword-based analysis
    analysis = {
        "project_type": "library",
        "suggested_hooks": [],
        "technologies": [],
        "complexity": "simple",
        "estimated_files": 5,
    }

    # Determine project type
    if any(
        word in requirements_lower for word in ["api", "rest", "endpoint", "server"]
    ):
        analysis["project_type"] = "api"
        analysis["technologies"].extend(["fastapi", "uvicorn"])
    elif any(
        word in requirements_lower for word in ["web", "dashboard", "ui", "frontend"]
    ):
        analysis["project_type"] = "web-app"
        analysis["technologies"].extend(["streamlit", "fastapi"])
    elif any(word in requirements_lower for word in ["cli", "command", "terminal"]):
        analysis["project_type"] = "cli"
        analysis["technologies"].extend(["cyclopts", "rich"])

    # Suggest hooks
    if "validate" in requirements_lower or "validation" in requirements_lower:
        analysis["suggested_hooks"].append("validator")
    if "transform" in requirements_lower or "convert" in requirements_lower:
        analysis["suggested_hooks"].append("transformer")
    if "analyze" in requirements_lower or "analysis" in requirements_lower:
        analysis["suggested_hooks"].append("analyzer")
    if "security" in requirements_lower or "auth" in requirements_lower:
        analysis["suggested_hooks"].append("security_validator")

    # Determine complexity
    word_count = len(requirements.split())
    if word_count > 50:
        analysis["complexity"] = "advanced"
        analysis["estimated_files"] = 15
    elif word_count > 20:
        analysis["complexity"] = "moderate"
        analysis["estimated_files"] = 10

    return analysis


def _print_analysis(analysis: dict) -> None:
    """Print analysis results in a formatted way."""
    console.print("📊 Requirements Analysis:", style="bold")
    console.print()

    console.print(f"Project Type: {analysis['project_type']}", style="cyan")
    console.print(f"Complexity: {analysis['complexity']}", style="yellow")
    console.print(f"Estimated Files: {analysis['estimated_files']}")

    if analysis["technologies"]:
        console.print(
            f"Suggested Technologies: {', '.join(analysis['technologies'])}",
            style="green",
        )

    if analysis["suggested_hooks"]:
        console.print(
            f"Suggested Hooks: {', '.join(analysis['suggested_hooks'])}", style="blue"
        )

    console.print()
    console.print("💡 Next Steps:", style="bold")
    console.print("1. Run scaffold commands to generate project structure")
    console.print("2. Implement core functionality")
    console.print("3. Add tests and documentation")
    console.print("4. Set up CI/CD pipeline")


if __name__ == "__main__":
    app()
