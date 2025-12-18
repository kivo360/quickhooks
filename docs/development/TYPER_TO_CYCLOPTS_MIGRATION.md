# Typer to Cyclopts Migration Guide

This document outlines the migration patterns for converting QuickHooks CLI from Typer to Cyclopts.

## Completed Migrations

1. ✅ `pyproject.toml` - Updated dependencies
2. ✅ `src/quickhooks/cli/main.py` - Main entry point migrated
3. ✅ `src/quickhooks/cli/features.py` - Features sub-app migrated

## Key Migration Patterns

### 1. Import Changes

**Before (Typer):**
```python
import typer
from typer import Argument, Option
```

**After (Cyclopts):**
```python
import cyclopts
from cyclopts import Parameter
from typing import Annotated
```

### 2. App Creation

**Before (Typer):**
```python
app = typer.Typer(
    name="app-name",
    help="Description",
    add_completion=False,
)
```

**After (Cyclopts):**
```python
app = cyclopts.App(
    name="app-name",
    help="Description",
)
```

### 3. Command Decorators

**Before (Typer):**
```python
@app.command()
def my_command():
    pass
```

**After (Cyclopts):**
```python
@app.command
def my_command():
    pass
```

### 4. Arguments and Options

**Before (Typer):**
```python
@app.command()
def my_command(
    arg: str = typer.Argument(..., help="Argument description"),
    opt: str = typer.Option("default", "--option", "-o", help="Option description"),
):
    pass
```

**After (Cyclopts):**
```python
@app.command
def my_command(
    arg: str,  # Positional arguments don't need Parameter
    opt: Annotated[str, Parameter("--option", "-o", help="Option description")] = "default",
):
    """Command description.
    
    Parameters
    ----------
    arg
        Argument description
    opt
        Option description (default: "default")
    """
    pass
```

### 5. Error Handling

**Before (Typer):**
```python
raise typer.Exit(code=1)
```

**After (Cyclopts):**
```python
import sys
sys.exit(1)
```

### 6. User Input

**Before (Typer):**
```python
value = typer.prompt("Enter value", hide_input=True)
confirm = typer.confirm("Continue?")
```

**After (Cyclopts):**
```python
from rich.prompt import Prompt, Confirm

value = Prompt.ask("Enter value", password=True)
confirm = Confirm.ask("Continue?")
```

### 7. Output

**Before (Typer):**
```python
typer.echo("Message")
typer.echo("Error", err=True)
```

**After (Cyclopts):**
```python
from rich.console import Console
console = Console()

console.print("Message")
console.print("Error", style="red")
```

### 8. Sub-Apps and Groups

**Before (Typer):**
```python
sub_app = typer.Typer()
app.add_typer(sub_app, name="subcommand")
```

**After (Cyclopts):**
```python
# Option 1: Create a group and register commands
group = app.group("subcommand")

@group.command
def sub_command():
    pass

# Option 2: Migrate sub-app to Cyclopts and register commands individually
sub_app = cyclopts.App()
# ... define commands ...

# In main app:
group = app.group("subcommand")
for cmd_name, cmd_func in get_sub_app_commands(sub_app):
    group.command(cmd_func, name=cmd_name)
```

## Remaining Migrations

### High Priority
1. `src/quickhooks/cli/create.py` - Create sub-app
2. `src/quickhooks/cli/install.py` - Install sub-app
3. `src/quickhooks/cli/settings.py` - Settings sub-app
4. `src/quickhooks/cli/smart.py` - Smart sub-app
5. `src/quickhooks/cli/deploy.py` - Deploy sub-app
6. `src/quickhooks/cli/global_hooks.py` - Global hooks sub-app
7. `src/quickhooks/cli/agent_os.py` - Agent OS sub-app
8. `src/quickhooks/agent_analysis/command.py` - Agent analysis sub-app

### Medium Priority
9. Scripts using Typer:
   - `scripts/setup_pep723_hooks.py`
   - `scripts/create-hook.py`
   - `scripts/deploy.py`
   - `scripts/validate-build.py`
   - `scripts/setup_claude_code_integration.py`
   - `scripts/agent-coordinator.py`

### Low Priority
10. Templates:
    - `templates/cli_command.py.j2` - Update to generate Cyclopts code

11. Tests:
    - `tests/conftest.py` - Update test utilities
    - All test files using `typer.testing.CliRunner`

## Migration Checklist for Each File

- [ ] Replace `import typer` with `import cyclopts`
- [ ] Replace `typer.Typer()` with `cyclopts.App()`
- [ ] Replace `@app.command()` with `@app.command`
- [ ] Convert `typer.Argument(...)` to positional parameters
- [ ] Convert `typer.Option(...)` to `Annotated[type, Parameter(...)]`
- [ ] Replace `typer.Exit(code=1)` with `sys.exit(1)`
- [ ] Replace `typer.prompt()` with `Prompt.ask()`
- [ ] Replace `typer.confirm()` with `Confirm.ask()`
- [ ] Replace `typer.echo()` with `console.print()`
- [ ] Update docstrings to use Parameters section format
- [ ] Test the migrated commands

## Testing

After migrating each sub-app:
1. Test basic command execution
2. Test help output (`--help`)
3. Test argument parsing
4. Test option flags
5. Test error handling
6. Run existing tests (may need updates)

## Notes

- Cyclopts automatically generates help from docstrings
- Use `Parameters` section in docstrings for help text
- Cyclopts supports more complex types (Unions, Literals) than Typer
- Sub-apps need to be registered as groups in the main app
- Consider using `app.default` for default commands instead of `@app.command`

