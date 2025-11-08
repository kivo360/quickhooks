#!/usr/bin/env python3
"""
Create new QuickHooks hooks using Jinja2 templates.

This script provides a convenient way to generate new hook classes
and their corresponding tests using the QuickHooks template system.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Add path to access quickhooks utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from quickhooks.utils.jinja_utils import CodeGenerator, TemplateRenderer

app = typer.Typer(help="Create new QuickHooks hooks using templates")
console = Console()


@app.command()
def hook(
    name: str = typer.Argument(..., help="Name of the hook (e.g., security_validator)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Hook description"),
    hook_type: str = typer.Option("validator", "--type", "-t", help="Hook type (validator, transformer, analyzer)"),
    base_class: str = typer.Option("BaseHook", "--base", "-b", help="Base class to inherit from"),
    output_dir: str = typer.Option("hooks", "--output", "-o", help="Output directory for hook files"),
    create_test: bool = typer.Option(True, "--test/--no-test", help="Create test file"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Create a new hook class with optional test file."""
    
    if interactive:
        name = Prompt.ask("Hook name", default=name)
        description = Prompt.ask("Hook description", default=description or f"A {hook_type} hook")
        hook_type = Prompt.ask("Hook type", default=hook_type, choices=["validator", "transformer", "analyzer"])
        base_class = Prompt.ask("Base class", default=base_class)
        output_dir = Prompt.ask("Output directory", default=output_dir)
        create_test = Confirm.ask("Create test file?", default=create_test)
    
    if not description:
        description = f"A {hook_type} hook for {name.replace('_', ' ')}"
    
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
    output_path = Path(output_dir)
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
        
        test_dir = Path("tests") / output_dir
        test_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = test_dir / f"test_{name}.py"
        with open(test_file, "w") as f:
            f.write(test_code)
        
        console.print(f"✅ Test created: {test_file}")
    
    # Display next steps
    console.print(Panel(
        f"""Next steps:
1. Edit {hook_file} to implement your hook logic
2. {"Update " + str(test_file) + " with specific tests" if create_test else "Create tests for your hook"}
3. Run tests: pytest {test_file if create_test else "tests/"}
4. Register hook in your hook registry""",
        title="Next Steps",
        style="bold blue"
    ))


@app.command()
def config(
    name: str = typer.Argument(..., help="Name of the config class"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Config description"),
    output_dir: str = typer.Option("config", "--output", "-o", help="Output directory"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """Create a new configuration class."""
    
    if interactive:
        name = Prompt.ask("Config class name", default=name)
        description = Prompt.ask("Config description", default=description or f"Configuration for {name}")
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
    
    # Generate config class
    generator = CodeGenerator()
    
    config_code = generator.generate_config_class(
        config_name=f"{name}Config",
        fields=fields
    )
    
    # Create output directory and file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    config_file = output_path / f"{name.lower()}_config.py"
    with open(config_file, "w") as f:
        f.write(config_code)
    
    console.print(f"✅ Config created: {config_file}")


@app.command()
def cli_command(
    name: str = typer.Argument(..., help="Name of the CLI command"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Command description"),
    output_dir: str = typer.Option("cli", "--output", "-o", help="Output directory"),
):
    """Create a new CLI command using templates."""
    
    if not description:
        description = f"CLI command for {name.replace('_', ' ')}"
    
    # Initialize template renderer
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    renderer = TemplateRenderer(template_dir=template_dir)
    
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


if __name__ == "__main__":
    app()