#!/usr/bin/env python3
"""
Setup script for integrating QuickHooks Agent Analysis with Claude Code.

This script helps users set up the agent analysis hook in their Claude Code
configuration for automatic agent discovery and prompt modification.

Usage:
    python scripts/setup_claude_code_integration.py
"""

import json
import os
import shutil
import sys
from pathlib import Path

import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()
app = cyclopts.App(help="Setup QuickHooks Agent Analysis integration with Claude Code")


def check_requirements() -> dict[str, bool]:
    """Check if all required components are available."""
    checks = {}

    # Check for Groq API key
    checks["groq_api_key"] = bool(os.getenv("GROQ_API_KEY"))

    # Check for Claude directory
    claude_dir = Path.home() / ".claude"
    checks["claude_directory"] = claude_dir.exists()

    # Check for agents directory
    agents_dir = claude_dir / "agents"
    checks["agents_directory"] = agents_dir.exists()

    # Check for QuickHooks installation
    try:
        import importlib.util

        spec = importlib.util.find_spec("quickhooks.agent_analysis")
        checks["quickhooks_installed"] = spec is not None
    except ImportError:
        checks["quickhooks_installed"] = False

    # Check for required dependencies
    try:
        import importlib.util

        deps = ["chromadb", "groq", "sentence_transformers"]
        checks["dependencies_installed"] = all(
            importlib.util.find_spec(dep) is not None for dep in deps
        )
    except ImportError:
        checks["dependencies_installed"] = False

    return checks


def display_requirements_check(checks: dict[str, bool]):
    """Display the requirements check results."""
    table = Table(
        title="Requirements Check", show_header=True, header_style="bold magenta"
    )
    table.add_column("Requirement", style="cyan", width=30)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Description", width=50)

    requirements = [
        ("groq_api_key", "Groq API Key", "Required for agent analysis"),
        ("claude_directory", "Claude Directory", "~/.claude directory exists"),
        ("agents_directory", "Agents Directory", "~/.claude/agents directory exists"),
        ("quickhooks_installed", "QuickHooks", "QuickHooks package is installed"),
        (
            "dependencies_installed",
            "Dependencies",
            "All required dependencies are installed",
        ),
    ]

    for key, name, description in requirements:
        status = "✅" if checks.get(key, False) else "❌"
        color = "green" if checks.get(key, False) else "red"

        table.add_row(name, f"[{color}]{status}[/{color}]", description)

    console.print(table)


def setup_directories():
    """Set up required directories."""
    console.print("\n[bold blue]Setting up directories...[/bold blue]")

    # Create QuickHooks directory
    quickhooks_dir = Path.home() / ".quickhooks"
    quickhooks_dir.mkdir(exist_ok=True)
    console.print(f"✅ Created QuickHooks directory: {quickhooks_dir}")

    # Create hooks directory
    hooks_dir = quickhooks_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    console.print(f"✅ Created hooks directory: {hooks_dir}")

    # Create database directory
    db_dir = quickhooks_dir / "agent_db"
    db_dir.mkdir(exist_ok=True)
    console.print(f"✅ Created database directory: {db_dir}")

    # Create Claude agents directory if it doesn't exist
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(exist_ok=True)

    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        agents_dir.mkdir(exist_ok=True)
        console.print(f"✅ Created agents directory: {agents_dir}")

        # Create a sample agent
        sample_agent = agents_dir / "sample_coding_agent.py"
        sample_agent.write_text('''"""
Sample coding agent for demonstration.

This agent helps with Python programming tasks including:
- Writing functions and classes
- Code debugging and optimization
- Testing and validation

Capabilities: coding, python, debugging, testing
Usage: Use for Python development tasks
"""

class SampleCodingAgent:
    """A sample coding agent for Python development."""

    def help_with_coding(self, task: str) -> str:
        """Help with coding tasks."""
        return f"I can help you with: {task}"

    def debug_code(self, code: str) -> str:
        """Debug Python code."""
        return f"Analyzing code for issues: {code[:100]}..."

    def write_tests(self, function_name: str) -> str:
        """Write tests for a function."""
        return f"Creating tests for {function_name}..."
''')
        console.print(f"✅ Created sample agent: {sample_agent}")
    else:
        console.print(f"✅ Agents directory already exists: {agents_dir}")


def copy_hook_script():
    """Copy the agent analysis hook script."""
    console.print("\n[bold blue]Installing hook script...[/bold blue]")

    # Find the hook script
    current_dir = Path(__file__).parent.parent
    hook_script = current_dir / "hooks" / "agent_analysis_hook.py"

    if not hook_script.exists():
        console.print(f"[red]❌ Hook script not found: {hook_script}[/red]")
        return False

    # Copy to QuickHooks hooks directory
    target_dir = Path.home() / ".quickhooks" / "hooks"
    target_script = target_dir / "agent_analysis_hook.py"

    shutil.copy2(hook_script, target_script)
    target_script.chmod(0o755)  # Make executable

    console.print(f"✅ Copied hook script to: {target_script}")
    return True


def create_settings_json():
    """Create or update Claude Code settings.json."""
    console.print("\n[bold blue]Setting up Claude Code configuration...[/bold blue]")

    # Load the example settings
    current_dir = Path(__file__).parent.parent
    example_settings = current_dir / "examples" / "claude_code_settings.json"

    if not example_settings.exists():
        console.print(f"[red]❌ Example settings not found: {example_settings}[/red]")
        return False

    with open(example_settings) as f:
        settings_data = json.load(f)

    # Ask user for configuration options
    console.print("\n[bold yellow]Configuration Options:[/bold yellow]")

    model = Prompt.ask(
        "Groq model to use",
        default=settings_data["environment"]["QUICKHOOKS_AGENT_MODEL"],
        choices=["qwen/qwen3-32b", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    )

    confidence_threshold = float(
        Prompt.ask(
            "Confidence threshold (0.0-1.0)",
            default=settings_data["environment"]["QUICKHOOKS_CONFIDENCE_THRESHOLD"],
        )
    )

    verbose = Confirm.ask("Enable verbose logging?", default=False)

    # Update settings
    settings_data["environment"]["QUICKHOOKS_AGENT_MODEL"] = model
    settings_data["environment"]["QUICKHOOKS_CONFIDENCE_THRESHOLD"] = str(
        confidence_threshold
    )
    settings_data["environment"]["QUICKHOOKS_VERBOSE"] = str(verbose).lower()

    # Save to QuickHooks directory for reference
    settings_file = Path.home() / ".quickhooks" / "claude_code_settings.json"
    with open(settings_file, "w") as f:
        json.dump(settings_data, f, indent=2)

    console.print(f"✅ Created settings file: {settings_file}")

    # Show instructions for Claude Code integration
    console.print("\n[bold yellow]Claude Code Integration Instructions:[/bold yellow]")
    console.print("1. Open your Claude Code settings.json file")
    console.print("2. Add the following hook configuration:")

    hook_config = {
        "user-prompt-submit": {
            "script": str(
                Path.home() / ".quickhooks" / "hooks" / "agent_analysis_hook.py"
            ),
            "function": "on_user_prompt_submit",
            "enabled": True,
            "description": "Analyzes user prompts and modifies them to use appropriate agents",
        }
    }

    console.print(
        Panel(
            json.dumps(hook_config, indent=2),
            title="Hook Configuration",
            border_style="green",
        )
    )

    return True


def test_setup():
    """Test the setup by running a sample analysis."""
    console.print("\n[bold blue]Testing setup...[/bold blue]")

    try:
        from quickhooks.agent_analysis import AgentAnalysisRequest, AgentAnalyzer

        # Create analyzer
        analyzer = AgentAnalyzer(model_name="qwen/qwen3-32b")

        # Test analysis
        request = AgentAnalysisRequest(
            prompt="Write a Python function that sorts a list", confidence_threshold=0.5
        )

        result = analyzer.analyze_prompt_sync(request)

        console.print("✅ Agent analysis test completed successfully!")
        console.print(f"   Found {len(result.discovered_agents)} local agents")
        console.print(f"   Generated {len(result.recommendations)} recommendations")
        console.print(f"   Used {result.total_tokens_used} tokens")

        if result.discovered_agents:
            console.print("\n[bold green]Discovered Agents:[/bold green]")
            for agent in result.discovered_agents[:3]:  # Show first 3
                console.print(f"   • {agent.name}: {agent.description[:50]}...")

        return True

    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        return False


@app.command
def setup(
    skip_check: bool = Parameter(
        False, "--skip-check", help="Skip requirements check"
    ),
    test: bool = Parameter(True, "--test/--no-test", help="Run test after setup"),
):
    """Set up QuickHooks Agent Analysis integration with Claude Code."""

    console.print(
        Panel.fit(
            "[bold blue]QuickHooks Agent Analysis - Claude Code Integration Setup[/bold blue]",
            border_style="blue",
        )
    )

    # Check requirements
    if not skip_check:
        console.print("\n[bold yellow]Checking requirements...[/bold yellow]")
        checks = check_requirements()
        display_requirements_check(checks)

        # Check for critical missing requirements
        critical_missing = []
        if not checks.get("groq_api_key"):
            critical_missing.append("GROQ_API_KEY environment variable")
        if not checks.get("quickhooks_installed"):
            critical_missing.append("QuickHooks package")
        if not checks.get("dependencies_installed"):
            critical_missing.append("Required dependencies")

        if critical_missing:
            console.print("\n[red]❌ Critical requirements missing:[/red]")
            for item in critical_missing:
                console.print(f"   • {item}")

            console.print(
                "\n[yellow]Please install missing requirements first:[/yellow]"
            )
            if "GROQ_API_KEY environment variable" in critical_missing:
                console.print("   export GROQ_API_KEY=your_groq_api_key_here")
            if "QuickHooks package" in critical_missing:
                console.print("   pip install quickhooks[agent-analysis]")
            if "Required dependencies" in critical_missing:
                console.print("   pip install chromadb sentence-transformers groq")

            sys.exit(1)

        if not Confirm.ask("\nProceed with setup?"):
            console.print("Setup cancelled.")
            sys.exit(0)

    # Setup directories
    setup_directories()

    # Copy hook script
    if not copy_hook_script():
        console.print("[red]❌ Failed to copy hook script[/red]")
        sys.exit(1)

    # Create settings
    if not create_settings_json():
        console.print("[red]❌ Failed to create settings[/red]")
        sys.exit(1)

    # Test setup
    if test:
        if test_setup():
            console.print("\n[bold green]✅ Setup completed successfully![/bold green]")
        else:
            console.print(
                "\n[yellow]⚠️  Setup completed but test failed. Check your configuration.[/yellow]"
            )
    else:
        console.print("\n[bold green]✅ Setup completed![/bold green]")

    # Final instructions
    console.print("\n[bold blue]Next Steps:[/bold blue]")
    console.print(
        "1. Copy the hook configuration from ~/.quickhooks/claude_code_settings.json"
    )
    console.print("2. Add it to your Claude Code settings.json file")
    console.print("3. Restart Claude Code")
    console.print("4. Test by submitting a prompt like 'Write a Python function'")

    console.print("\n[bold yellow]Files created:[/bold yellow]")
    console.print("   • Hook script: ~/.quickhooks/hooks/agent_analysis_hook.py")
    console.print("   • Settings: ~/.quickhooks/claude_code_settings.json")
    console.print("   • Sample agent: ~/.claude/agents/sample_coding_agent.py")


@app.command
def test():
    """Test the agent analysis setup."""
    console.print("Testing QuickHooks Agent Analysis setup...")

    if test_setup():
        console.print("[bold green]✅ Test passed![/bold green]")
    else:
        console.print("[red]❌ Test failed![/red]")
        sys.exit(1)


@app.command()
def uninstall():
    """Uninstall the QuickHooks Agent Analysis integration."""

    if not Confirm.ask(
        "Are you sure you want to uninstall the QuickHooks Agent Analysis integration?"
    ):
        console.print("Uninstall cancelled.")
        return

    console.print("Uninstalling QuickHooks Agent Analysis integration...")

    # Remove hook script
    hook_script = Path.home() / ".quickhooks" / "hooks" / "agent_analysis_hook.py"
    if hook_script.exists():
        hook_script.unlink()
        console.print(f"✅ Removed hook script: {hook_script}")

    # Remove settings
    settings_file = Path.home() / ".quickhooks" / "claude_code_settings.json"
    if settings_file.exists():
        settings_file.unlink()
        console.print(f"✅ Removed settings file: {settings_file}")

    # Remove database (optional)
    if Confirm.ask("Remove agent database? (This will require re-indexing agents)"):
        db_dir = Path.home() / ".quickhooks" / "agent_db"
        if db_dir.exists():
            shutil.rmtree(db_dir)
            console.print(f"✅ Removed database: {db_dir}")

    console.print("[bold green]✅ Uninstall completed![/bold green]")
    console.print(
        "Don't forget to remove the hook configuration from your Claude Code settings.json"
    )


if __name__ == "__main__":
    app()
