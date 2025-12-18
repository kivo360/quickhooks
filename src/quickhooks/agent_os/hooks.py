"""Agent OS hooks for QuickHooks.

This module provides hooks that integrate Agent OS workflows
into the QuickHooks framework.
"""

from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput, HookResult, HookStatus

from .executor import AgentOSExecutor
from .workflow_manager import WorkflowManager


class AgentOSHook(BaseHook):
    """
    Hook that executes Agent OS instructions and workflows.

    This hook bridges Agent OS capabilities with QuickHooks,
    allowing Agent OS instructions to be executed as hooks
    within the QuickHooks framework.
    """

    def __init__(
        self,
        instruction: str | None = None,
        workflow: str | None = None,
        category: str | None = None,
        agent_os_path: str | None = None,
        resume: bool = False,
        **kwargs,
    ):
        """
        Initialize the Agent OS hook.

        Args:
            instruction: Agent OS instruction to execute
            workflow: Agent OS workflow to execute
            category: Category for the instruction ('core', 'meta')
            agent_os_path: Custom path to Agent OS installation
            resume: Whether to resume a workflow from saved state
            **kwargs: Additional hook parameters
        """
        super().__init__(
            name="agent_os_hook",
            description="Executes Agent OS instructions and workflows",
            **kwargs,
        )

        self.instruction = instruction
        self.workflow = workflow
        self.category = category
        self.agent_os_path = agent_os_path
        self.resume = resume

        # Validate configuration
        if not instruction and not workflow:
            msg = "Either 'instruction' or 'workflow' must be provided"
            raise ValueError(msg)

        if instruction and workflow:
            msg = "Cannot specify both 'instruction' and 'workflow'"
            raise ValueError(msg)

    async def execute(self, hook_input: HookInput) -> HookResult:
        """
        Execute the Agent OS instruction or workflow.

        Args:
            hook_input: Hook input data

        Returns:
            Hook execution result
        """
        try:
            from pathlib import Path

            # Initialize executor or workflow manager
            agent_os_path = Path(self.agent_os_path) if self.agent_os_path else None
            working_dir = Path(hook_input.context.get("working_directory", "."))

            if self.instruction:
                # Execute single instruction
                executor = AgentOSExecutor(
                    agent_os_path=agent_os_path,
                    working_directory=working_dir,
                    verbose=hook_input.context.get("verbose", False),
                )

                result = await executor.execute_instruction(
                    self.instruction, self.category, hook_input.context
                )

                return HookResult(
                    status=result.status,
                    output=result.output_data,
                    metadata={
                        "instruction": self.instruction,
                        "category": self.category,
                        "execution_type": "instruction",
                    },
                )

            # Execute workflow
            workflow_manager = WorkflowManager(
                agent_os_path=agent_os_path, working_directory=working_dir
            )

            # Load saved state if resuming
            saved_state = None
            if self.resume:
                saved_state = workflow_manager.load_workflow_state(self.workflow)

            # Execute workflow
            final_state = await workflow_manager.execute_workflow(
                self.workflow, hook_input.context, saved_state
            )

            # Save state for potential resumption
            if final_state.status in ["running", "pending"]:
                workflow_manager.save_workflow_state(final_state)
            elif final_state.status in ["completed", "failed"]:
                # Clean up state on completion
                workflow_manager.delete_workflow_state(self.workflow)

            return HookResult(
                status=HookStatus.SUCCEEDED
                if final_state.status == "completed"
                else HookStatus.FAILED,
                output=HookOutput(
                    data={
                        "workflow": self.workflow,
                        "status": final_state.status,
                        "completed_steps": final_state.completed_steps,
                        "failed_steps": final_state.failed_steps,
                        "total_steps": len(final_state.step_results),
                        "step_results": final_state.step_results,
                        "context": final_state.context,
                    },
                    error=final_state.context.get("error")
                    if final_state.status == "failed"
                    else None,
                ),
                metadata={
                    "workflow": self.workflow,
                    "execution_type": "workflow",
                    "resumed": self.resume and saved_state is not None,
                },
            )

        except Exception as e:
            return HookResult(
                status=HookStatus.FAILED,
                output=HookOutput(error=f"Agent OS hook execution failed: {e!s}"),
                metadata={
                    "instruction": self.instruction,
                    "workflow": self.workflow,
                    "execution_type": "instruction" if self.instruction else "workflow",
                },
            )


class AgentOSPrePostHook(BaseHook):
    """
    Hook that executes Agent OS instructions before and after main execution.

    Useful for setup, validation, cleanup, and reporting tasks.
    """

    def __init__(
        self,
        pre_instruction: str | None = None,
        post_instruction: str | None = None,
        category: str | None = None,
        agent_os_path: str | None = None,
        **kwargs,
    ):
        """
        Initialize the pre/post hook.

        Args:
            pre_instruction: Instruction to execute before main execution
            post_instruction: Instruction to execute after main execution
            category: Category for instructions
            agent_os_path: Custom path to Agent OS installation
            **kwargs: Additional hook parameters
        """
        super().__init__(
            name="agent_os_prepost_hook",
            description="Executes Agent OS instructions before and after main execution",
            **kwargs,
        )

        self.pre_instruction = pre_instruction
        self.post_instruction = post_instruction
        self.category = category
        self.agent_os_path = agent_os_path

        # Store pre-execution results for post-execution use
        self._pre_result = None

    async def execute(self, hook_input: HookInput) -> HookResult:
        """
        Execute pre/post Agent OS instructions.

        Args:
            hook_input: Hook input data

        Returns:
            Hook execution result
        """
        try:
            from pathlib import Path

            agent_os_path = Path(self.agent_os_path) if self.agent_os_path else None
            working_dir = Path(hook_input.context.get("working_directory", "."))

            executor = AgentOSExecutor(
                agent_os_path=agent_os_path,
                working_directory=working_dir,
                verbose=hook_input.context.get("verbose", False),
            )

            # Execute pre-instruction if present
            if self.pre_instruction:
                self._pre_result = await executor.execute_instruction(
                    self.pre_instruction, self.category, hook_input.context
                )

                if self._pre_result.status == HookStatus.FAILED:
                    return HookResult(
                        status=HookStatus.FAILED,
                        output=HookOutput(
                            error=f"Pre-instruction failed: {self._pre_result.output_data.error if self._pre_result.output_data else 'Unknown error'}"
                        ),
                        metadata={
                            "pre_instruction": self.pre_instruction,
                            "execution_type": "pre_instruction_failed",
                        },
                    )

            # Return success for pre-execution (post-execution will be handled separately)
            return HookResult(
                status=HookStatus.SUCCEEDED,
                output=HookOutput(
                    data={
                        "pre_instruction_executed": bool(self.pre_instruction),
                        "post_instruction_pending": bool(self.post_instruction),
                        "pre_result": self._pre_result.output_data.data
                        if self._pre_result and self._pre_result.output_data
                        else None,
                    }
                ),
                metadata={
                    "pre_instruction": self.pre_instruction,
                    "post_instruction": self.post_instruction,
                    "execution_type": "pre_execution",
                },
            )

        except Exception as e:
            return HookResult(
                status=HookStatus.FAILED,
                output=HookOutput(error=f"Pre-execution failed: {e!s}"),
                metadata={
                    "pre_instruction": self.pre_instruction,
                    "execution_type": "pre_execution_error",
                },
            )

    async def execute_post(
        self, hook_input: HookInput, main_result: HookResult
    ) -> HookResult:
        """
        Execute post-instruction if main execution succeeded.

        Args:
            hook_input: Original hook input
            main_result: Result from main execution

        Returns:
            Post-execution result
        """
        if not self.post_instruction:
            return HookResult(
                status=HookStatus.SUCCEEDED,
                output=HookOutput(data={"post_instruction_skipped": True}),
            )

        # Only execute post-instruction if main execution succeeded
        if main_result.status != HookStatus.SUCCEEDED:
            return HookResult(
                status=HookStatus.SKIPPED,
                output=HookOutput(
                    data={
                        "post_instruction_skipped": True,
                        "reason": "main_execution_failed",
                    }
                ),
            )

        try:
            from pathlib import Path

            agent_os_path = Path(self.agent_os_path) if self.agent_os_path else None
            working_dir = Path(hook_input.context.get("working_directory", "."))

            executor = AgentOSExecutor(
                agent_os_path=agent_os_path,
                working_directory=working_dir,
                verbose=hook_input.context.get("verbose", False),
            )

            # Add pre-execution results to context for post-execution
            post_context = {
                **hook_input.context,
                "main_result": main_result.output_data.data
                if main_result.output_data
                else {},
                "pre_result": self._pre_result.output_data.data
                if self._pre_result and self._pre_result.output_data
                else {},
            }

            # Execute post-instruction
            post_result = await executor.execute_instruction(
                self.post_instruction, self.category, post_context
            )

            return HookResult(
                status=post_result.status,
                output=post_result.output_data,
                metadata={
                    "post_instruction": self.post_instruction,
                    "execution_type": "post_execution",
                },
            )

        except Exception as e:
            return HookResult(
                status=HookStatus.FAILED,
                output=HookOutput(error=f"Post-execution failed: {e!s}"),
                metadata={
                    "post_instruction": self.post_instruction,
                    "execution_type": "post_execution_error",
                },
            )
