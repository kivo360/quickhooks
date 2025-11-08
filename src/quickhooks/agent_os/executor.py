"""Agent OS instruction executor for QuickHooks.

This module executes Agent OS instructions and workflows within
the QuickHooks framework, leveraging existing hook infrastructure.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, TaskID

from .instruction_parser import AgentOSInstruction, InstructionParser
from ..models import HookInput, HookOutput, HookResult, HookStatus, HookError, ExecutionContext

console = Console()


class AgentOSExecutor:
    """Executes Agent OS instructions and workflows."""

    def __init__(
        self,
        agent_os_path: Optional[Path] = None,
        working_directory: Optional[Path] = None,
        verbose: bool = False,
    ):
        """
        Initialize the Agent OS executor.

        Args:
            agent_os_path: Path to Agent OS installation
            working_directory: Working directory for execution
            verbose: Enable verbose output
        """
        self.agent_os_path = agent_os_path or Path.home() / ".agent-os"
        self.working_directory = working_directory or Path.cwd()
        self.verbose = verbose
        self.parser = InstructionParser(self.agent_os_path)
        print(f"DEBUG: Executor initialized with agent_os_path: {self.agent_os_path}")
        print(f"DEBUG: Executor parser instructions_path: {self.parser.instructions_path}")

    def _create_hook_result(
        self,
        status: HookStatus,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        error: Optional[HookError] = None,
        hook_id: str = "agent-os-executor",
    ) -> HookResult:
        """Create a properly structured HookResult."""
        return HookResult(
            hook_id=hook_id,
            status=status,
            input_data=HookInput(event_type="agent_execution", data={}),
            output_data=HookOutput(
                status=status,
                data=data or {},
                message=message,
                error=error,
            ),
            execution_context=ExecutionContext(
                hook_id=hook_id,
                execution_id=f"exec-{hash(str(status))}",
                environment="development"
            )
        )

    async def execute_instruction(
        self,
        instruction_name: str,
        category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HookResult:
        """
        Execute an Agent OS instruction.

        Args:
            instruction_name: Name of the instruction to execute
            category: Optional category ('core', 'meta')
            context: Additional context for execution

        Returns:
            Hook execution result
        """
        try:
            # Load the instruction
            instruction: AgentOSInstruction | None = self.parser.load_instruction(
                instruction_name, category
            )
            if not instruction:
                return self._create_hook_result(
                    status=HookStatus.FAILED,
                    error=HookError(
                        code="INSTRUCTION_NOT_FOUND",
                        message=f"Instruction '{instruction_name}' not found"
                    )
                )

            if self.verbose:
                console.print(
                    f"[blue]Executing instruction:[/blue] {instruction.description}"
                )
                console.print(f"[dim]Version:[/dim] {instruction.version}")

            # Execute pre-flight check if present
            if instruction.process_flow.pre_flight_check:
                preflight_result = await self._execute_check(
                    instruction.process_flow.pre_flight_check, context
                )
                if preflight_result.status == HookStatus.FAILED:
                    return preflight_result

            # Execute process flow steps
            step_results = []
            with Progress() as progress:
                task = progress.add_task(
                    f"Executing {instruction_name}...",
                    total=len(instruction.process_flow.steps),
                )

                for step in instruction.process_flow.steps:
                    step_result = await self._execute_step(
                        step, context, progress, task
                    )
                    step_results.append(step_result)

                    if step_result.status == HookStatus.FAILED:
                        # Step failed, check if we should continue
                        if self.verbose:
                            console.print(f"[red]Step '{step['name']}' failed[/red]")
                        break

                    progress.advance(task)

            # Execute post-flight check if present
            if instruction.process_flow.post_flight_check:
                postflight_result = await self._execute_check(
                    instruction.process_flow.post_flight_check, context
                )
                if postflight_result.status == HookStatus.FAILED:
                    return postflight_result

            # Determine overall success
            overall_success = all(
                result.status == HookStatus.SUCCESS for result in step_results
            )

            return self._create_hook_result(
                status=HookStatus.SUCCESS if overall_success else HookStatus.FAILED,
                data={
                    "instruction": instruction_name,
                    "category": category,
                    "steps_completed": len(
                        [
                            r
                            for r in step_results
                            if r.status == HookStatus.SUCCESS
                        ]
                    ),
                    "total_steps": len(instruction.process_flow.steps),
                    "step_results": [
                        {
                            "name": step["name"],
                            "status": result.status,
                            "output": result.output_data.data
                            if result.output_data and result.output_data.data
                            else None,
                        }
                        for step, result in zip(
                            instruction.process_flow.steps, step_results
                        )
                    ],
                }
            )

        except Exception as e:
            if self.verbose:
                console.print(f"[red]Execution exception: {e}[/red]")
                console.print(f"[red]Exception type: {type(e)}[/red]")
                import traceback
                console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            return self._create_hook_result(
                status=HookStatus.FAILED,
                error=HookError(
                    code="EXECUTION_ERROR",
                    message=f"Execution failed: {str(e)}"
                )
            )

    async def _execute_step(
        self,
        step: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        progress: Progress,
        task: TaskID,
    ) -> HookResult:
        """
        Execute a single step from the process flow.

        Args:
            step: Step configuration
            context: Execution context
            progress: Progress bar instance
            task: Progress task ID

        Returns:
            Step execution result
        """
        try:
            step_name = step["name"]
            subagent = step["subagent"]

            if self.verbose:
                progress.update(task, description=f"Executing step: {step_name}")

            # Resolve the agent reference
            agent_result = await self._execute_agent(subagent, step, context)

            return agent_result

        except Exception as e:
            return self._create_hook_result(
                status=HookStatus.FAILED,
                error=HookError(
                    code="STEP_ERROR",
                    message=f"Step '{step['name']}' failed: {str(e)}"
                ),
                hook_id=f"step-{step['name']}"
            )

    async def _execute_agent(
        self,
        agent_name: str,
        step: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> HookResult:
        """
        Execute an Agent OS agent.

        Args:
            agent_name: Name of the agent to execute
            step: Step configuration
            context: Execution context

        Returns:
            Agent execution result
        """
        # For now, we'll implement basic agent execution
        # In a full implementation, this would integrate with Claude Code's agent system

        agent_content = step.get("content", "")

        # Mock execution for demonstration
        if self.verbose:
            console.print(f"[dim]Executing agent:[/dim] {agent_name}")

        # Simulate agent work
        await asyncio.sleep(0.1)

        return self._create_hook_result(
            status=HookStatus.SUCCESS,
            data={
                "agent": agent_name,
                "step": step["name"],
                "execution_time": 0.1,
                "mock_execution": True,
            },
            hook_id=f"agent-{agent_name}"
        )

    async def _execute_check(
        self,
        check_command: str,
        context: Optional[Dict[str, Any]],
    ) -> HookResult:
        """
        Execute a pre-flight or post-flight check.

        Args:
            check_command: Check command to execute
            context: Execution context

        Returns:
            Check execution result
        """
        try:
            # Handle EXECUTE commands
            if check_command.startswith("EXECUTE:"):
                command_ref = check_command.replace("EXECUTE:", "").strip()

                # Handle Agent OS command references
                if command_ref.startswith("@~/.agent-os/instructions/"):
                    instruction_path = self.agent_os_path / command_ref[1:]  # Remove @
                    if instruction_path.exists():
                        instruction: AgentOSInstruction = (
                            self.parser.parse_instruction_file(instruction_path)
                        )
                        # Execute the instruction recursively
                        return await self.execute_instruction(
                            instruction_path.stem, context=context
                        )

                # Handle other command types as needed
                if self.verbose:
                    console.print(f"[dim]Executing check:[/dim] {command_ref}")

            # Mock successful check for now
            return self._create_hook_result(
                status=HookStatus.SUCCESS,
                data={"check": check_command, "passed": True},
                hook_id="check-execution"
            )

        except Exception as e:
            return self._create_hook_result(
                status=HookStatus.FAILED,
                error=HookError(
                    code="CHECK_ERROR",
                    message=f"Check failed: {str(e)}"
                ),
                hook_id="check-execution"
            )

    async def execute_workflow(
        self,
        workflow_name: str,
        instructions: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> HookResult:
        """
        Execute a multi-instruction workflow.

        Args:
            workflow_name: Name of the workflow
            instructions: List of instruction names to execute
            context: Execution context

        Returns:
            Workflow execution result
        """
        workflow_results = []

        if self.verbose:
            console.print(f"[blue]Executing workflow:[/blue] {workflow_name}")
            console.print(f"[dim]Instructions:[/dim] {', '.join(instructions)}")

        for instruction in instructions:
            result = await self.execute_instruction(instruction, context=context)
            workflow_results.append({"instruction": instruction, "result": result})

            if result.status == HookStatus.FAILED:
                # Stop workflow on first failure
                break

        overall_success = all(
            r["result"].status == HookStatus.SUCCESS for r in workflow_results
        )

        return self._create_hook_result(
            status=HookStatus.SUCCESS if overall_success else HookStatus.FAILED,
            data={
                "workflow": workflow_name,
                "instructions_completed": len(
                    [
                        r
                        for r in workflow_results
                        if r["result"].status == HookStatus.SUCCESS
                    ]
                ),
                "total_instructions": len(instructions),
                "results": workflow_results,
            },
            hook_id=f"workflow-{workflow_name}"
        )

    def list_available_instructions(self, category: Optional[str] = None) -> List[str]:
        """
        List available Agent OS instructions.

        Args:
            category: Optional category filter

        Returns:
            List of instruction names
        """
        instruction_files = self.parser.list_available_instructions(category)
        return [f.stem for f in instruction_files]
