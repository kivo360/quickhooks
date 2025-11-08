"""Agent OS CLI commands for QuickHooks.

This module provides CLI commands for interacting with Agent OS
workflows and instructions through the QuickHooks interface.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from quickhooks import __version__
from ..agent_os import WorkflowManager, AgentOSExecutor, InstructionParser

console = Console()
app = typer.Typer(
    name="agent-os",
    help="Agent OS integration commands for QuickHooks",
    add_completion=False,
)


@app.command()
def version() -> None:
    """Show Agent OS integration version."""
    console.print(f"QuickHooks Agent OS Integration v{__version__}")


@app.command()
def list_instructions(
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category (core, meta)"
    ),
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """List available Agent OS instructions."""
    try:
        parser = InstructionParser(
            Path(agent_os_path) if agent_os_path else None
        )
        instructions = parser.list_available_instructions(category)

        if not instructions:
            console.print("[yellow]No instructions found[/yellow]")
            return

        table = Table(title=f"Agent OS Instructions{f' ({category})' if category else ''}")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Version", style="green")

        for instruction_file in instructions:
            instruction = parser.parse_instruction_file(instruction_file)
            table.add_row(
                instruction_file.stem,
                instruction.description[:80] + "..." if len(instruction.description) > 80 else instruction.description,
                instruction.version
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing instructions: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def execute_instruction(
    instruction_name: str = typer.Argument(..., help="Name of the instruction to execute"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Instruction category (core, meta)"
    ),
    context_file: Optional[str] = typer.Option(
        None, "--context", help="JSON file with execution context"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """Execute an Agent OS instruction."""
    try:
        # Load context if provided
        context = {}
        if context_file:
            context_path = Path(context_file)
            if context_path.exists():
                context = json.loads(context_path.read_text(encoding='utf-8'))
            else:
                console.print(f"[red]Context file not found: {context_file}[/red]")
                raise typer.Exit(code=1)

        # Execute instruction
        executor = AgentOSExecutor(
            Path(agent_os_path) if agent_os_path else None,
            verbose=verbose
        )

        result = asyncio.run(executor.execute_instruction(
            instruction_name,
            category,
            context
        ))

        if result.status.value == "success":
            console.print(f"[green]✓ Instruction '{instruction_name}' completed successfully[/green]")
            if result.output_data and result.output_data.data:
                console.print("\n[bold]Results:[/bold]")
                console.print(json.dumps(result.output_data.data, indent=2))
        else:
            console.print(f"[red]✗ Instruction '{instruction_name}' failed[/red]")
            if result.output_data and result.output_data.error:
                console.print(f"[red]Error: {result.output_data.error}[/red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Error executing instruction: {e}[/red]")
        import traceback
        console.print(f"[red]Full traceback: {traceback.format_exc()}[/red]")
        raise typer.Exit(code=1)


@app.command()
def list_workflows(
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """List available Agent OS workflows."""
    try:
        manager = WorkflowManager(
            Path(agent_os_path) if agent_os_path else None
        )
        workflows = manager.list_workflows()

        if not workflows:
            console.print("[yellow]No workflows found[/yellow]")
            console.print("[dim]Use 'quickhooks agent-os create-workflow' to create one[/dim]")
            return

        table = Table(title="Agent OS Workflows")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Steps", style="green")
        table.add_column("Has State", style="yellow")

        for workflow_name in workflows:
            workflow = manager.load_workflow(workflow_name)
            if workflow:
                has_state = manager.load_workflow_state(workflow_name) is not None
                table.add_row(
                    workflow.name,
                    workflow.description[:60] + "..." if len(workflow.description) > 60 else workflow.description,
                    str(len(workflow.steps)),
                    "Yes" if has_state else "No"
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing workflows: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def create_workflow(
    name: str = typer.Argument(..., help="Workflow name"),
    description: str = typer.Option(..., "--description", "-d", help="Workflow description"),
    instructions: str = typer.Option(
        ..., "--instructions", "-i", help="Comma-separated list of instruction names"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Default category for instructions (default: recursive search)"
    ),
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """Create a new Agent OS workflow."""
    try:
        from ..agent_os.workflow_manager import WorkflowStep

        manager = WorkflowManager(
            Path(agent_os_path) if agent_os_path else None
        )

        # Parse instructions
        instruction_list = [inst.strip() for inst in instructions.split(",")]

        # Create workflow steps
        steps = []
        for i, instruction in enumerate(instruction_list):
            step = WorkflowStep(
                instruction=instruction,
                category=category,
                depends_on=instruction_list[:i] if i > 0 else []
            )
            steps.append(step)

        # Create workflow
        workflow = manager.create_workflow(
            name=name,
            description=description,
            steps=steps
        )

        console.print(f"[green]✓ Workflow '{name}' created successfully[/green]")
        console.print(f"[dim]Instructions: {', '.join(instruction_list)}[/dim]")

    except Exception as e:
        console.print(f"[red]Error creating workflow: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def execute_workflow(
    workflow_name: str = typer.Argument(..., help="Name of the workflow to execute"),
    context_file: Optional[str] = typer.Option(
        None, "--context", help="JSON file with execution context"
    ),
    resume: bool = typer.Option(
        False, "--resume", "-r", help="Resume from saved state"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    save_state: bool = typer.Option(
        True, "--save-state/--no-save-state", help="Save execution state"
    ),
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """Execute an Agent OS workflow."""
    try:
        # Load context if provided
        context = {}
        if context_file:
            context_path = Path(context_file)
            if context_path.exists():
                context = json.loads(context_path.read_text(encoding='utf-8'))
            else:
                console.print(f"[red]Context file not found: {context_file}[/red]")
                raise typer.Exit(code=1)

        manager = WorkflowManager(
            Path(agent_os_path) if agent_os_path else None
        )

        # Load saved state if resuming
        saved_state = None
        if resume:
            saved_state = manager.load_workflow_state(workflow_name)
            if saved_state:
                console.print(f"[blue]Resuming workflow '{workflow_name}' from saved state[/blue]")
                console.print(f"[dim]Completed steps: {', '.join(saved_state.completed_steps)}[/dim]")
            else:
                console.print("[yellow]No saved state found, starting fresh[/yellow]")

        # Execute workflow
        final_state = asyncio.run(manager.execute_workflow(
            workflow_name,
            context,
            saved_state
        ))

        # Display results
        if final_state.status == "completed":
            console.print(f"[green]✓ Workflow '{workflow_name}' completed successfully[/green]")
            console.print(f"[dim]Steps completed: {len(final_state.completed_steps)}/{len(final_state.step_results)}[/dim]")
        elif final_state.status == "failed":
            console.print(f"[red]✗ Workflow '{workflow_name}' failed[/red]")
            if "error" in final_state.context:
                console.print(f"[red]Error: {final_state.context['error']}[/red]")
            console.print(f"[dim]Failed at step: {final_state.current_step}[/dim]")
        else:
            console.print(f"[yellow]Workflow '{workflow_name}' status: {final_state.status}[/yellow]")

        # Show step details
        if final_state.step_results and verbose:
            tree = Tree("Step Results")
            for step_name, result in final_state.step_results.items():
                status_icon = "✓" if hasattr(result, 'status') and result.status.value == "success" else "✗"
                step_branch = tree.add(f"{status_icon} {step_name}")
                if hasattr(result, 'output_data') and result.output_data and result.output_data.data:
                    step_branch.add(f"Output: {json.dumps(result.output_data.data, indent=2)[:200]}...")
            console.print(tree)

        # Save or clean up state
        if save_state and final_state.status in ["running", "pending"]:
            manager.save_workflow_state(final_state)
            console.print(f"[dim]State saved for resuming later[/dim]")
        elif final_state.status in ["completed", "failed"]:
            manager.delete_workflow_state(workflow_name)
            console.print(f"[dim]State cleaned up[/dim]")

    except Exception as e:
        console.print(f"[red]Error executing workflow: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def init_workflows(
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """Initialize predefined Agent OS workflows."""
    try:
        manager = WorkflowManager(
            Path(agent_os_path) if agent_os_path else None
        )

        manager.create_predefined_workflows()

        console.print("[green]✓ Predefined workflows initialized[/green]")

        # List created workflows
        workflows = manager.list_workflows()
        if workflows:
            console.print("\n[bold]Available workflows:[/bold]")
            for workflow_name in workflows:
                workflow = manager.load_workflow(workflow_name)
                if workflow:
                    console.print(f"• [cyan]{workflow_name}[/cyan]: {workflow.description}")

    except Exception as e:
        console.print(f"[red]Error initializing workflows: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def show_instruction(
    instruction_name: str = typer.Argument(..., help="Name of the instruction"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Instruction category (core, meta)"
    ),
    agent_os_path: Optional[str] = typer.Option(
        None, "--agent-os-path", "-p", help="Custom Agent OS installation path"
    )
) -> None:
    """Show details of an Agent OS instruction."""
    try:
        parser = InstructionParser(
            Path(agent_os_path) if agent_os_path else None
        )
        instruction = parser.load_instruction(instruction_name, category)

        if not instruction:
            console.print(f"[red]Instruction '{instruction_name}' not found[/red]")
            raise typer.Exit(code=1)

        console.print(f"[bold]Instruction:[/bold] {instruction_name}")
        console.print(f"[bold]Description:[/bold] {instruction.description}")
        console.print(f"[bold]Version:[/bold] {instruction.version}")

        if instruction.process_flow.steps:
            console.print(f"\n[bold]Steps ({len(instruction.process_flow.steps)}):[/bold]")
            for i, step in enumerate(instruction.process_flow.steps, 1):
                console.print(f"{i}. [cyan]{step['title']}[/cyan] ({step['subagent']})")
                if step.get('data_sources', {}).get('primary'):
                    console.print(f"   [dim]Primary: {step['data_sources']['primary']}[/dim]")

        if instruction.process_flow.pre_flight_check:
            console.print(f"\n[bold]Pre-flight check:[/bold]")
            console.print(f"[dim]{instruction.process_flow.pre_flight_check}[/dim]")

        if instruction.process_flow.post_flight_check:
            console.print(f"\n[bold]Post-flight check:[/bold]")
            console.print(f"[dim]{instruction.process_flow.post_flight_check}[/dim]")

    except Exception as e:
        console.print(f"[red]Error showing instruction: {e}[/red]")
        raise typer.Exit(code=1)