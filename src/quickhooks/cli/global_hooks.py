"""CLI commands for managing global hooks."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from quickhooks.config import get_global_hooks_dir

global_app = typer.Typer(help="Manage global hooks")
console = Console()


@global_app.command()
def setup():
    """Setup global hooks environment for easy importing."""
    global_dir = get_global_hooks_dir()
    global_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py in global hooks directory
    init_file = global_dir / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w") as f:
            f.write('"""Global hooks registry."""\n\n')
            f.write('import sys\n')
            f.write('from pathlib import Path\n\n')
            f.write('# Add global hooks directory to Python path\n')
            f.write('global_hooks_dir = Path(__file__).parent\n')
            f.write('if str(global_hooks_dir) not in sys.path:\n')
            f.write('    sys.path.insert(0, str(global_hooks_dir))\n\n')
    
    console.print(f"✅ Global hooks directory set up: {global_dir}")
    console.print("\n💡 To use global hooks in any project:")
    console.print("1. Add to PYTHONPATH: export PYTHONPATH=$PYTHONPATH:~/.quickhooks")
    console.print("2. Or use: quickhooks global add-to-path")


@global_app.command()
def add_to_path():
    """Add global hooks to current Python path for this session."""
    global_dir = get_global_hooks_dir()
    
    if not global_dir.exists():
        console.print("❌ Global hooks directory doesn't exist. Run 'quickhooks global setup' first.", style="red")
        return
    
    # Add to current Python path
    global_parent = str(global_dir.parent)
    if global_parent not in sys.path:
        sys.path.insert(0, global_parent)
        console.print(f"✅ Added {global_parent} to Python path")
    else:
        console.print("✅ Global hooks already in Python path")
    
    # Show how to make it permanent
    console.print("\n💡 To make this permanent, add to your shell profile:")
    console.print(f"export PYTHONPATH=$PYTHONPATH:{global_parent}")


@global_app.command()
def import_hook(
    hook_name: str = typer.Argument(..., help="Name of the global hook to import"),
    project_dir: Optional[Path] = typer.Option(None, "--project", "-p", help="Project directory (defaults to current)")
):
    """Create a local import for a global hook."""
    if project_dir is None:
        project_dir = Path.cwd()
    
    global_dir = get_global_hooks_dir()
    global_hook = global_dir / f"{hook_name}.py"
    
    if not global_hook.exists():
        console.print(f"❌ Global hook '{hook_name}' not found", style="red")
        return
    
    # Create hooks directory in project
    project_hooks_dir = project_dir / "hooks"
    project_hooks_dir.mkdir(exist_ok=True)
    
    # Create symlink or import file
    import_file = project_hooks_dir / f"{hook_name}_global.py"
    
    import_content = f'''"""Import wrapper for global hook: {hook_name}"""

import sys
from pathlib import Path

# Add global hooks to path
global_hooks_path = Path.home() / ".quickhooks"
if str(global_hooks_path) not in sys.path:
    sys.path.insert(0, str(global_hooks_path))

# Import the global hook
from hooks.{hook_name} import *
'''
    
    with open(import_file, "w") as f:
        f.write(import_content)
    
    console.print(f"✅ Created import wrapper: {import_file}")
    console.print(f"💡 You can now import this hook in your project as: from hooks.{hook_name}_global import {hook_name.title().replace('_', '')}Hook")


@global_app.command()
def info():
    """Show information about global hooks setup."""
    global_dir = get_global_hooks_dir()
    
    console.print(Panel(f"""
🏠 Global hooks directory: {global_dir}
📁 Exists: {'✅' if global_dir.exists() else '❌'}
🐍 Python path: {'✅' if str(global_dir.parent) in sys.path else '❌'}

Environment Variables:
• QUICKHOOKS_GLOBAL_DIR: {os.getenv('QUICKHOOKS_GLOBAL_DIR', 'Not set')}
• PYTHONPATH includes global hooks: {'✅' if any(str(global_dir.parent) in p for p in os.getenv('PYTHONPATH', '').split(':')) else '❌'}
""", title="Global Hooks Info"))


if __name__ == "__main__":
    global_app()