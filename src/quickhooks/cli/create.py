"""CLI commands for creating hooks, configs, and other components using templates."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from quickhooks.utils.jinja_utils import CodeGenerator, TemplateRenderer
from quickhooks.config import get_global_hooks_dir

create_app = typer.Typer(help="Create hooks, configs, and CLI commands using templates")
console = Console()


@create_app.command()
def hook(
    name: str = typer.Argument(..., help="Name of the hook (e.g., security_validator)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Hook description"),
    hook_type: str = typer.Option("validator", "--type", "-t", help="Hook type (validator, transformer, analyzer)"),
    base_class: str = typer.Option("BaseHook", "--base", "-b", help="Base class to inherit from"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for hook files"),
    create_test: bool = typer.Option(True, "--test/--no-test", help="Create test file"),
    global_hook: bool = typer.Option(False, "--global", "-g", help="Create hook in global directory"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Create a new hook class with optional test file."""
    
    if interactive:
        name = Prompt.ask("Hook name", default=name)
        description = Prompt.ask("Hook description", default=description or f"A {hook_type} hook")
        hook_type = Prompt.ask("Hook type", default=hook_type, choices=["validator", "transformer", "analyzer"])
        base_class = Prompt.ask("Base class", default=base_class)
        global_hook = Confirm.ask("Create as global hook?", default=global_hook)
        if not global_hook and not output_dir:
            output_dir = Prompt.ask("Output directory", default="hooks")
        create_test = Confirm.ask("Create test file?", default=create_test)
    
    if not description:
        description = f"A {hook_type} hook for {name.replace('_', ' ')}"
    
    # Determine output directory
    if global_hook:
        output_path = get_global_hooks_dir()
        console.print(f"📍 Using global hooks directory: {output_path}")
    else:
        output_path = Path(output_dir or "hooks")
    
    # Initialize code generator
    generator = CodeGenerator()
    
    # Generate hook class
    console.print(Panel(f"Creating hook: {name}", style="bold green"))
    
    hook_code = generator.generate_hook_class(
        hook_name=name,
        description=description,
        base_class=base_class
    )
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Write hook file
    hook_file = output_path / f"{name}.py"
    with open(hook_file, "w") as f:
        f.write(hook_code)
    
    console.print(f"✅ Hook created: {hook_file}")
    
    # Create test file if requested
    if create_test:
        test_code = generator.generate_test_class(
            test_subject=name,
            test_type="unit"
        )
        
        if global_hook:
            test_dir = get_global_hooks_dir() / "tests"
        else:
            test_dir = Path("tests") / (output_dir or "hooks")
        
        test_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = test_dir / f"test_{name}.py"
        with open(test_file, "w") as f:
            f.write(test_code)
        
        console.print(f"✅ Test created: {test_file}")
    
    # Update global registry if it's a global hook
    if global_hook:
        _register_global_hook(name, hook_file)
    
    # Display next steps
    next_steps = f"""Next steps:
1. Edit {hook_file} to implement your hook logic
2. {"Update " + str(test_file) + " with specific tests" if create_test else "Create tests for your hook"}
3. Run tests: pytest {test_file if create_test else "tests/"}"""
    
    if global_hook:
        next_steps += f"\n4. Hook is globally available - reference it from any project"
    else:
        next_steps += f"\n4. Register hook in your project's hook registry"
    
    console.print(Panel(next_steps, title="Next Steps", style="bold blue"))


@create_app.command()
def config(
    name: str = typer.Argument(..., help="Name of the config class"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Config description"),
    output_dir: str = typer.Option("config", "--output", "-o", help="Output directory"),
    global_config: bool = typer.Option(False, "--global", "-g", help="Create config in global directory"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Create a new configuration class."""
    
    if interactive:
        name = Prompt.ask("Config class name", default=name)
        description = Prompt.ask("Config description", default=description or f"Configuration for {name}")
        global_config = Confirm.ask("Create as global config?", default=global_config)
        if not global_config:
            output_dir = Prompt.ask("Output directory", default=output_dir)
    
    if not description:
        description = f"Configuration for {name}"
    
    # Interactive field definition
    fields = {}
    if interactive:
        console.print("Define configuration fields (press Enter with empty name to finish):")
        while True:
            field_name = Prompt.ask("Field name", default="")
            if not field_name:
                break
            
            field_type = Prompt.ask("Field type", default="str")
            field_default = Prompt.ask("Default value (or press Enter for no default)", default="")
            field_desc = Prompt.ask("Field description", default="")
            
            fields[field_name] = {
                "type": field_type,
                "description": field_desc
            }
            if field_default:
                fields[field_name]["default"] = field_default
    else:
        # Default example fields
        fields = {
            "enabled": {
                "type": "bool",
                "default": True,
                "description": "Whether this feature is enabled"
            },
            "max_items": {
                "type": "int", 
                "default": 100,
                "description": "Maximum number of items to process"
            }
        }
    
    # Determine output directory
    if global_config:
        output_path = get_global_hooks_dir() / "config"
    else:
        output_path = Path(output_dir)
    
    # Generate config class
    generator = CodeGenerator()
    
    config_code = generator.generate_config_class(
        config_name=f"{name}Config",
        fields=fields
    )
    
    # Create output directory and file
    output_path.mkdir(parents=True, exist_ok=True)
    
    config_file = output_path / f"{name.lower()}_config.py"
    with open(config_file, "w") as f:
        f.write(config_code)
    
    console.print(f"✅ Config created: {config_file}")


@create_app.command()
def cli_command(
    name: str = typer.Argument(..., help="Name of the CLI command"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Command description"),
    output_dir: str = typer.Option("cli", "--output", "-o", help="Output directory"),
):
    """Create a new CLI command using templates."""
    
    if not description:
        description = f"CLI command for {name.replace('_', ' ')}"
    
    # Initialize template renderer
    template_dir = Path(__file__).parent.parent.parent.parent / "templates"
    renderer = TemplateRenderer(template_dir=str(template_dir))
    
    # Example parameters for demo
    parameters = [
        {
            "name": "input_file",
            "type": "str",
            "typer_type": "Argument",
            "description": "Input file path"
        },
        {
            "name": "output_dir", 
            "type": "Optional[str]",
            "typer_type": "Option",
            "default": None,
            "description": "Output directory"
        }
    ]
    
    cli_code = renderer.render(
        "cli_command.py.j2",
        command_name=name,
        description=description,
        main_command=name.replace("-", "_"),
        parameters=parameters,
        type_imports=["Optional"]
    )
    
    # Create output directory and file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cli_file = output_path / f"{name.replace('-', '_')}.py"
    with open(cli_file, "w") as f:
        f.write(cli_code)
    
    console.print(f"✅ CLI command created: {cli_file}")


@create_app.command()
def list_global():
    """List all globally available hooks."""
    global_dir = get_global_hooks_dir()
    
    if not global_dir.exists():
        console.print("No global hooks directory found.", style="yellow")
        console.print(f"Run 'quickhooks create hook --global' to create your first global hook.")
        return
    
    hook_files = list(global_dir.glob("*.py"))
    if not hook_files:
        console.print("No global hooks found.", style="yellow")
        return
    
    console.print(f"📁 Global hooks directory: {global_dir}")
    console.print("🔧 Available global hooks:")
    
    for hook_file in hook_files:
        if hook_file.name.startswith("__"):
            continue
        console.print(f"  • {hook_file.stem}")
    
    console.print(f"\n💡 Use these hooks in any project by importing from the global directory")


def _register_global_hook(hook_name: str, hook_file: Path) -> None:
    """Register a hook in the global registry."""
    global_dir = get_global_hooks_dir()
    registry_file = global_dir / "__init__.py"
    
    # Create __init__.py if it doesn't exist
    if not registry_file.exists():
        with open(registry_file, "w") as f:
            f.write('"""Global hooks registry."""\n\n')
    
    # Add hook to registry (simple append for now)
    with open(registry_file, "a") as f:
        f.write(f"# {hook_name} - {hook_file.name}\n")
    
    console.print(f"📝 Registered global hook: {hook_name}")


if __name__ == "__main__":
    create_app()