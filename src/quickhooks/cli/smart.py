"""Smart hook generator using Fireworks AI for intent interpretation."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import Parameter
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from quickhooks.config import get_config, get_global_hooks_dir

smart_app = cyclopts.App(help="Smart hook generation using AI intent interpretation")
console = Console()

# Initialize Fireworks AI client
client = None


def get_fireworks_client():
    """Get or create Fireworks AI client."""
    global client
    if client is None:
        # Use Pydantic AI with Fireworks
        config = get_config()

        if not config.ai.api_key:
            console.print(
                "🔑 Fireworks AI API key required for smart hook generation", style="yellow"
            )
            console.print(
                "💡 Set FIREWORKS_API_KEY environment variable", style="cyan",
            )
            sys.exit(1)

        try:
            client = Agent(OpenAIModel(
                model=config.ai.llm,
                api_key=config.ai.api_key,
                base_url=config.ai.base_url
            ))
        except Exception as e:
            console.print(f"❌ Failed to initialize Fireworks AI client: {e}", style="red")
            sys.exit(1)

    return client


@smart_app.command
def generate(
    intent: str,
    model: Annotated[
        str, Parameter("--model", alias="-m", help="Fireworks AI model to use")
    ] = "accounts/fireworks/models/llama-v3p1-70b-instruct",
    open_vscode: Annotated[
        bool, Parameter("--vscode/--no-vscode", help="Open in VSCode after generation")
    ] = True,
    dry_run: Annotated[
        bool,
        Parameter(
            "--dry-run", help="Show what would be generated without creating files"
        ),
    ] = False,
):
    """Generate hooks based on natural language intent using Fireworks AI LLM.

    Parameters
    ----------
    intent
        Describe what you want the hook to do
    model
        Fireworks AI model to use (default: "accounts/fireworks/models/llama-v3p1-70b-instruct")
    open_vscode
        Open in VSCode after generation (default: True)
    dry_run
        Show what would be generated without creating files (default: False)
    """
    asyncio.run(_generate_async(intent, model, open_vscode, dry_run))


async def _generate_async(intent: str, model: str, open_vscode: bool, dry_run: bool):
    """Async implementation of generate command."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Analyze intent
        task = progress.add_task(
            "🧠 Analyzing your intent with Fireworks AI...", total=None
        )

        try:
            fireworks_client = get_fireworks_client()
            analysis = await _analyze_intent(fireworks_client, intent, model)
            progress.update(task, description="✅ Intent analyzed successfully")

        except Exception as e:
            progress.update(task, description=f"❌ Error: {e!s}")
            console.print(f"Error: {e}", style="bold red")
            sys.exit(1)

    # Display analysis (outside progress context to avoid spinner interference)
    _display_analysis(analysis)

    if not Confirm.ask("Does this analysis look correct?"):
        console.print("❌ Aborted by user", style="red")
        return

    # Continue with file generation in new progress context
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        try:
            # Step 2: Generate hook structure
            task = progress.add_task("🏗️ Generating hook structure...", total=None)

            hook_specs = _create_hook_specs(analysis)

            # Step 3: Generate code
            progress.update(task, description="⚡ Generating hook code...")

            generated_files = await _generate_hook_files(fireworks_client, hook_specs, model)

            if dry_run:
                _display_dry_run(generated_files)
                return

            # Step 4: Create files
            progress.update(
                task, description="📁 Creating files in global hooks directory..."
            )

            created_files = _create_files(generated_files)

            # Step 5: Open in VSCode
            if open_vscode:
                progress.update(task, description="🚀 Opening in VSCode...")
                _open_in_vscode(created_files)

            progress.update(task, description="🎉 Hook generation complete!")

            _display_success(created_files, analysis)

        except Exception as e:
            progress.update(task, description=f"❌ Error: {e!s}")
            console.print(f"Error: {e}", style="bold red")
            sys.exit(1)


async def _analyze_intent(client: Agent, intent: str, model: str) -> dict:
    """Analyze user intent using Fireworks AI."""

    system_prompt = """You are an expert at interpreting user intents for creating Claude Code hooks.

    Analyze the user's description and return a JSON object with these fields:
    - hook_name: A snake_case name for the hook
    - hook_type: One of "validator", "transformer", "analyzer"
    - description: A clear description of what the hook does
    - target_tool: The Claude Code tool this hook targets (e.g., "Bash", "Read", "Write", etc.)
    - hook_category: One of "security", "performance", "utility", "validation", "transformation"
    - key_features: List of main features/capabilities
    - transformation_rules: If transformer, list of transformation patterns
    - validation_rules: If validator, list of validation criteria
    - analysis_aspects: If analyzer, list of what to analyze
    - examples: 2-3 example use cases

    Be specific and technical. Focus on Claude Code hook development patterns."""

    response = await client.run(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"I want to create a hook that: {intent}"},
        ],
        model=model,
        temperature=0.1,
        max_tokens=2000,
    )

    try:
        return json.loads(response.data)
    except json.JSONDecodeError as e:
        console.print(f"Error parsing LLM response: {e}", style="red")
        console.print("Raw response:", response.data)
        raise


def _display_analysis(analysis: dict):
    """Display the LLM analysis results."""

    content = f"""
**Hook Name:** `{analysis["hook_name"]}`
**Type:** {analysis["hook_type"].title()}
**Target Tool:** {analysis["target_tool"]}
**Category:** {analysis["hook_category"].title()}

**Description:**
{analysis["description"]}

**Key Features:**
{chr(10).join(f"• {feature}" for feature in analysis["key_features"])}

**Examples:**
{chr(10).join(f"{i + 1}. {example}" for i, example in enumerate(analysis["examples"]))}
"""

    console.print(Panel(content, title="🎯 Intent Analysis", style="cyan"))


def _create_hook_specs(analysis: dict) -> dict:
    """Create detailed hook specifications from analysis."""

    return {
        "name": analysis["hook_name"],
        "type": analysis["hook_type"],
        "description": analysis["description"],
        "target_tool": analysis["target_tool"],
        "category": analysis["hook_category"],
        "features": analysis["key_features"],
        "rules": analysis.get(
            "transformation_rules",
            analysis.get("validation_rules", analysis.get("analysis_aspects", [])),
        ),
        "examples": analysis["examples"],
    }


async def _generate_hook_files(
    client: Agent, specs: dict, model: str
) -> dict[str, str]:
    """Generate actual hook code using Jinja2 templates."""

    from quickhooks.utils.jinja_utils import TemplateRenderer

    # Initialize template renderer
    template_dir = Path(__file__).parent.parent.parent / "templates"
    renderer = TemplateRenderer(template_dir=str(template_dir))

    # Prepare template context
    context = {
        "hook_name": specs["name"],
        "class_name": _to_pascal_case(specs["name"]),
        "description": specs["description"],
        "hook_type": specs["type"],
        "target_tool": specs["target_tool"],
        "category": specs["category"],
        "features": specs["features"],
        "rules": specs["rules"],
        "examples": specs["examples"],
        "timestamp": _get_current_timestamp(),
    }

    # Generate files using hook templates
    if specs["type"] == "validator":
        hook_code = renderer.render("validator_hook.py.j2", **context)
        test_code = renderer.render("validator_test.py.j2", **context)
    elif specs["type"] == "transformer":
        hook_code = renderer.render("transformer_hook.py.j2", **context)
        test_code = renderer.render("transformer_test.py.j2", **context)
    elif specs["type"] == "analyzer":
        hook_code = renderer.render("skill_integration_hook.py.j2", **context)
        test_code = renderer.render("analyzer_test.py.j2", **context)
    else:
        hook_code = renderer.render("basic_hook.py.j2", **context)
        test_code = renderer.render("basic_test.py.j2", **context)

    readme_content = renderer.render("hook_readme.md.j2", **context)

    return {
        f"{specs['name']}.py": hook_code,
        f"test_{specs['name']}.py": test_code,
        f"{specs['name']}_README.md": readme_content,
    }


def _to_pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    import datetime

    return datetime.datetime.now().isoformat()


def _display_dry_run(generated_files: dict[str, str]):
    """Display what would be generated in dry run mode."""

    console.print(Panel("🔍 Dry Run - Files that would be generated:", style="yellow"))

    for filename, content in generated_files.items():
        console.print(f"\n📄 **{filename}**")
        console.print("─" * 50)
        console.print(content[:500] + "..." if len(content) > 500 else content)


def _create_files(generated_files: dict[str, str]) -> list[Path]:
    """Create the actual files in global hooks directory."""

    global_dir = get_global_hooks_dir()
    global_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    for filename, content in generated_files.items():
        if filename.startswith("test_"):
            # Put tests in tests subdirectory
            test_dir = global_dir / "tests"
            test_dir.mkdir(exist_ok=True)
            file_path = test_dir / filename
        else:
            file_path = global_dir / filename

        with open(file_path, "w") as f:
            f.write(content)

        created_files.append(file_path)
        console.print(f"✅ Created: {file_path}")

    return created_files


def _open_in_vscode(created_files: list[Path]):
    """Open the created files in VSCode."""

    try:
        # Open the main hook file (non-test, non-README)
        main_file = next(
            (
                f
                for f in created_files
                if not f.name.startswith("test_") and not f.name.endswith("README.md")
            ),
            created_files[0],
        )

        subprocess.run(["code", str(main_file)], check=True)
        console.print(f"🚀 Opened {main_file.name} in VSCode")

        # Also open the directory in VSCode sidebar
        subprocess.run(["code", str(main_file.parent)], check=True)

    except subprocess.CalledProcessError as e:
        console.print(f"⚠️  Could not open in VSCode: {e}", style="yellow")
        console.print(
            "💡 Make sure VSCode is installed and 'code' command is available"
        )
    except Exception as e:
        console.print(f"⚠️  Error opening VSCode: {e}", style="yellow")


def _display_success(created_files: list[Path], analysis: dict):
    """Display success message with next steps."""

    files_list = "\n".join(f"• {f.name}" for f in created_files)

    content = f"""
🎉 **Successfully Generated Hook: `{analysis["hook_name"]}`**

**Files Created:**
{files_list}

**Next Steps:**
1. Review and customize the generated hook code
2. Run tests: `pytest ~/.quickhooks/hooks/tests/test_{analysis["hook_name"]}.py -v`
3. Add to your Claude Code settings.json to use globally
4. Test with real Claude Code commands

**Location:** `{get_global_hooks_dir()}`
"""

    console.print(Panel(content, title="🚀 Generation Complete", style="green"))


if __name__ == "__main__":
    smart_app()
