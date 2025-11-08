"""Agent OS workflow manager for QuickHooks.

This module manages complex Agent OS workflows, coordinating
multiple instructions and handling workflow state.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .executor import AgentOSExecutor
from .instruction_parser import InstructionParser
from ..models import HookResult


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""

    instruction: str
    category: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    condition: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Represents a workflow definition."""

    name: str
    description: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """Represents the state of a workflow execution."""

    workflow_name: str
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    step_results: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed


class WorkflowManager:
    """Manages Agent OS workflows."""

    def __init__(
        self,
        agent_os_path: Optional[Path] = None,
        workflows_path: Optional[Path] = None,
        working_directory: Optional[Path] = None,
    ):
        """
        Initialize the workflow manager.

        Args:
            agent_os_path: Path to Agent OS installation
            workflows_path: Path to workflow definitions
            working_directory: Working directory for execution
        """
        self.agent_os_path = agent_os_path or Path.home() / ".agent-os"
        self.workflows_path = workflows_path or self.agent_os_path / "workflows"
        self.working_directory = working_directory or Path.cwd()
        self.executor: AgentOSExecutor = AgentOSExecutor(
            self.agent_os_path, self.working_directory
        )
        self.parser: InstructionParser = InstructionParser(self.agent_os_path)

        # Ensure workflows directory exists
        self.workflows_path.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Workflow manager initialized with paths:")
        print(f"DEBUG: agent_os_path: {self.agent_os_path}")
        print(f"DEBUG: workflows_path: {self.workflows_path}")
        print(f"DEBUG: working_directory: {self.working_directory}")
        print(f"DEBUG: workflows_path exists: {self.workflows_path.exists()}")

    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowDefinition:
        """
        Create a new workflow definition.

        Args:
            name: Workflow name
            description: Workflow description
            steps: List of workflow steps
            metadata: Optional metadata

        Returns:
            Created workflow definition
        """
        workflow = WorkflowDefinition(
            name=name, description=description, steps=steps, metadata=metadata or {}
        )

        # Save workflow definition
        workflow_file = self.workflows_path / f"{name}.json"
        try:
            workflow_file.write_text(workflow.model_dump_json(indent=2), encoding="utf-8")
            print(f"DEBUG: Saved workflow to {workflow_file}")
        except Exception as e:
            print(f"DEBUG: Failed to save workflow: {e}")
            print(f"DEBUG: Workflows path: {self.workflows_path}")
            print(f"DEBUG: Workflows path exists: {self.workflows_path.exists()}")

        return workflow

    def load_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """
        Load a workflow definition.

        Args:
            name: Workflow name

        Returns:
            Loaded workflow or None if not found
        """
        workflow_file = self.workflows_path / f"{name}.json"
        if not workflow_file.exists():
            return None

        try:
            content = workflow_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return WorkflowDefinition(**data)
        except (json.JSONDecodeError, Exception):
            return None

    def list_workflows(self) -> List[str]:
        """
        List available workflow names.

        Returns:
            List of workflow names
        """
        return [f.stem for f in self.workflows_path.glob("*.json")]

    async def execute_workflow(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        resume_state: Optional[WorkflowState] = None,
    ) -> WorkflowState:
        """
        Execute a workflow.

        Args:
            name: Workflow name
            context: Execution context
            resume_state: Optional state to resume from

        Returns:
            Final workflow state
        """
        workflow = self.load_workflow(name)
        if not workflow:
            state = WorkflowState(workflow_name=name, status="failed")
            state.context["error"] = f"Workflow '{name}' not found"
            return state

        # Initialize or resume state
        if resume_state:
            state = resume_state
        else:
            state = WorkflowState(workflow_name=name, context=context or {})

        state.status = "running"

        try:
            # Execute steps in order, respecting dependencies
            for step in workflow.steps:
                # Skip if already completed (when resuming)
                if step.instruction in state.completed_steps:
                    continue

                # Check dependencies
                if step.depends_on:
                    missing_deps = [
                        dep
                        for dep in step.depends_on
                        if dep not in state.completed_steps
                    ]
                    if missing_deps:
                        state.failed_steps.append(step.instruction)
                        state.context["error"] = f"Missing dependencies: {missing_deps}"
                        state.status = "failed"
                        return state

                # Check condition if present
                if step.condition:
                    if not self._evaluate_condition(step.condition, state.context):
                        # Skip step due to failed condition
                        continue

                # Execute the step
                state.current_step = step.instruction
                print(f"DEBUG: Executing step: {step.instruction}")
                print(f"DEBUG: Category: {step.category}")
                print(f"DEBUG: Parameters: {step.parameters}")
                print(f"DEBUG: Context: {state.context}")

                result: HookResult = await self.executor.execute_instruction(
                    step.instruction,
                    step.category,
                    {**state.context, **step.parameters},
                )

                print(f"DEBUG: Step result status: {result.status}")
                print(f"DEBUG: Step result status value: {result.status.value}")
                print(f"DEBUG: Step result: {result}")

                # Store result
                state.step_results[step.instruction] = result

                if result.status.value == "success":
                    print(f"DEBUG: Step {step.instruction} succeeded")
                    state.completed_steps.append(step.instruction)
                else:
                    print(f"DEBUG: Step {step.instruction} failed")
                    state.failed_steps.append(step.instruction)
                    if result.output_data and result.output_data.error:
                        print(f"DEBUG: Error from result: {result.output_data.error}")
                        state.context["last_error"] = result.output_data.error
                    break

            # Determine final status
            if len(state.failed_steps) == 0:
                state.status = "completed"
            else:
                state.status = "failed"

        except Exception as e:
            state.status = "failed"
            state.context["error"] = str(e)

        finally:
            state.current_step = None

        return state

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a step condition.

        Args:
            condition: Condition string to evaluate
            context: Context for evaluation

        Returns:
            True if condition passes
        """
        # Simple condition evaluation for now
        # In a full implementation, this would support more complex expressions

        # Handle context variable references
        if condition.startswith("context."):
            var_name = condition.replace("context.", "")
            return bool(context.get(var_name))

        # Handle simple boolean expressions
        if condition.lower() in ("true", "yes", "1"):
            return True
        elif condition.lower() in ("false", "no", "0"):
            return False

        # Default to True for unknown conditions
        return True

    def save_workflow_state(self, state: WorkflowState) -> None:
        """
        Save workflow state to file.

        Args:
            state: Workflow state to save
        """
        state_file = self.workflows_path / f".{state.workflow_name}_state.json"
        state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load_workflow_state(self, workflow_name: str) -> Optional[WorkflowState]:
        """
        Load workflow state from file.

        Args:
            workflow_name: Workflow name

        Returns:
            Loaded state or None if not found
        """
        state_file = self.workflows_path / f".{workflow_name}_state.json"
        if not state_file.exists():
            return None

        try:
            content = state_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return WorkflowState(**data)
        except (json.JSONDecodeError, Exception):
            return None

    def delete_workflow_state(self, workflow_name: str) -> None:
        """
        Delete workflow state file.

        Args:
            workflow_name: Workflow name
        """
        state_file = self.workflows_path / f".{workflow_name}_state.json"
        if state_file.exists():
            state_file.unlink()

    def create_predefined_workflows(self) -> None:
        """Create some predefined workflows for common use cases."""

        # Product planning workflow
        product_planning_steps = [
            WorkflowStep(
                instruction="plan-product",
                category=None,
            ),
            WorkflowStep(
                instruction="create-spec",
                category=None,
                depends_on=["plan-product"],
            ),
            WorkflowStep(
                instruction="analyze-product",
                category=None,
                depends_on=["create-spec"],
            ),
        ]

        self.create_workflow(
            name="product-planning",
            description="Complete product planning workflow from idea to specifications",
            steps=product_planning_steps,
            metadata={
                "tags": ["product", "planning", "specification"],
                "estimated_time": "30-60 minutes",
            },
        )

        # Feature development workflow
        feature_development_steps = [
            WorkflowStep(
                instruction="create-spec",
                category=None,
            ),
            WorkflowStep(
                instruction="execute-tasks",
                category=None,
                depends_on=["create-spec"],
            ),
            WorkflowStep(
                instruction="analyze-product",
                category=None,
                depends_on=["execute-tasks"],
            ),
        ]

        self.create_workflow(
            name="feature-development",
            description="End-to-end feature development workflow",
            steps=feature_development_steps,
            metadata={
                "tags": ["development", "feature", "implementation"],
                "estimated_time": "60-120 minutes",
            },
        )
