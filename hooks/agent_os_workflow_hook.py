#!/usr/bin/env python3
"""
Claude Code hook for Agent OS workflow integration.

This hook integrates QuickHooks with Agent OS workflows, providing
seamless spec-driven agentic development within Claude Code.

Installation:
1. Add this hook to your Claude Code settings.json
2. Ensure Agent OS is installed at ~/.agent-os
3. Ensure QuickHooks is installed with Agent OS dependencies

Usage:
This hook can execute Agent OS instructions and workflows directly
from Claude Code prompts.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Add QuickHooks to path if needed
try:
    from quickhooks.agent_os.hooks import AgentOSHook, AgentOSPrePostHook
    from quickhooks.models import HookInput, HookOutput, HookResult, HookStatus
except ImportError:
    # Try to add QuickHooks to path
    quickhooks_path = Path.home() / ".quickhooks" / "src"
    if quickhooks_path.exists():
        sys.path.insert(0, str(quickhooks_path))
        from quickhooks.agent_os.hooks import AgentOSHook
        from quickhooks.models import HookInput
    else:
        print(
            "QuickHooks not found. Please install QuickHooks with Agent OS dependencies."
        )
        sys.exit(1)


class AgentOSWorkflowHook:
    """Hook that executes Agent OS workflows and instructions."""

    def __init__(self):
        """Initialize the Agent OS workflow hook."""
        self.enabled = (
            os.getenv("QUICKHOOKS_AGENT_OS_ENABLED", "true").lower() == "true"
        )
        self.agent_os_path = os.getenv("AGENT_OS_PATH", "~/.agent-os")
        self.default_category = os.getenv("QUICKHOOKS_AGENT_OS_CATEGORY", "core")
        self.verbose = (
            os.getenv("QUICKHOOKS_AGENT_OS_VERBOSE", "false").lower() == "true"
        )

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Run the Agent OS workflow hook.

        Args:
            input_data: Input data from Claude Code

        Returns:
            Hook execution results
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "message": "Agent OS hook is disabled",
                "output": None,
            }

        try:
            # Extract prompt and context
            prompt = input_data.get("prompt", "")
            context = input_data.get("context", {})

            # Detect Agent OS workflow/intent in the prompt
            agent_os_intent = self._detect_agent_os_intent(prompt)

            if not agent_os_intent:
                return {
                    "status": "skipped",
                    "message": "No Agent OS intent detected",
                    "output": None,
                }

            # Convert to HookInput format
            hook_input = HookInput(
                data=input_data,
                context={
                    **context,
                    "verbose": self.verbose,
                    "working_directory": Path.cwd(),
                    "agent_os_path": Path(self.agent_os_path).expanduser(),
                    "prompt": prompt,
                },
            )

            # Execute appropriate Agent OS action
            if agent_os_intent["type"] == "instruction":
                return self._execute_instruction(agent_os_intent, hook_input)
            if agent_os_intent["type"] == "workflow":
                return self._execute_workflow(agent_os_intent, hook_input)
            return {
                "status": "skipped",
                "message": f"Unknown Agent OS intent type: {agent_os_intent['type']}",
                "output": None,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Agent OS hook execution failed: {e!s}",
                "output": None,
            }

    def _detect_agent_os_intent(self, prompt: str) -> dict[str, Any]:
        """
        Detect Agent OS intent in the user's prompt.

        Args:
            prompt: User's prompt

        Returns:
            Detected intent information or None
        """
        prompt_lower = prompt.lower()

        # Check for explicit Agent OS instruction mentions
        agent_os_keywords = [
            "plan-product",
            "create-spec",
            "execute-task",
            "execute-tasks",
            "analyze-product",
            "agent os",
            "agent-os",
        ]

        for keyword in agent_os_keywords:
            if keyword in prompt_lower:
                return {
                    "type": "instruction",
                    "instruction": keyword,
                    "category": self._infer_category(prompt),
                    "confidence": 0.9,
                }

        # Check for workflow patterns
        workflow_patterns = [
            ("plan the product", "plan-product"),
            ("create specifications", "create-spec"),
            ("analyze the product", "analyze-product"),
            ("execute tasks", "execute-tasks"),
            ("product planning", "plan-product"),
            ("spec creation", "create-spec"),
        ]

        for pattern, instruction in workflow_patterns:
            if pattern in prompt_lower:
                return {
                    "type": "instruction",
                    "instruction": instruction,
                    "category": self._infer_category(prompt),
                    "confidence": 0.8,
                }

        # Check for multi-step workflows
        multi_step_indicators = [
            "plan and then create",
            "analyze then execute",
            "from idea to implementation",
            "end-to-end development",
        ]

        for indicator in multi_step_indicators:
            if indicator in prompt_lower:
                return {
                    "type": "workflow",
                    "workflow": self._infer_workflow(prompt),
                    "confidence": 0.7,
                }

        return None

    def _infer_category(self, prompt: str) -> str:
        """
        Infer the Agent OS instruction category from the prompt.

        Args:
            prompt: User's prompt

        Returns:
            Inferred category ('core' or 'meta')
        """
        prompt_lower = prompt.lower()

        # Core instructions are about product development
        core_keywords = [
            "plan",
            "create",
            "execute",
            "analyze",
            "spec",
            "product",
            "feature",
        ]

        # Meta instructions are about Agent OS itself
        meta_keywords = ["agent", "workflow", "instruction", "meta", "system"]

        core_score = sum(1 for keyword in core_keywords if keyword in prompt_lower)
        meta_score = sum(1 for keyword in meta_keywords if keyword in prompt_lower)

        return "meta" if meta_score > core_score else "core"

    def _infer_workflow(self, prompt: str) -> str:
        """
        Infer the appropriate workflow from the prompt.

        Args:
            prompt: User's prompt

        Returns:
            Inferred workflow name
        """
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["plan", "idea", "concept"]):
            return "product-planning"
        if any(word in prompt_lower for word in ["develop", "implement", "feature"]):
            return "feature-development"
        return "product-planning"  # Default workflow

    async def _execute_instruction(
        self, intent: dict[str, Any], hook_input: HookInput
    ) -> dict[str, Any]:
        """Execute an Agent OS instruction."""
        try:
            # Create Agent OS hook
            hook = AgentOSHook(
                instruction=intent["instruction"],
                category=intent["category"],
                agent_os_path=str(hook_input.context.get("agent_os_path")),
            )

            # Execute the hook
            result = await hook.execute(hook_input)

            return {
                "status": result.status.value,
                "message": f"Executed Agent OS instruction: {intent['instruction']}",
                "output": result.output.data if result.output else None,
                "agent_os_instruction": intent["instruction"],
                "agent_os_category": intent["category"],
                "confidence": intent["confidence"],
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to execute Agent OS instruction: {e!s}",
                "output": None,
                "agent_os_instruction": intent["instruction"],
            }

    async def _execute_workflow(
        self, intent: dict[str, Any], hook_input: HookInput
    ) -> dict[str, Any]:
        """Execute an Agent OS workflow."""
        try:
            # Create Agent OS hook for workflow
            hook = AgentOSHook(
                workflow=intent["workflow"],
                agent_os_path=str(hook_input.context.get("agent_os_path")),
            )

            # Execute the hook
            result = await hook.execute(hook_input)

            return {
                "status": result.status.value,
                "message": f"Executed Agent OS workflow: {intent['workflow']}",
                "output": result.output.data if result.output else None,
                "agent_os_workflow": intent["workflow"],
                "confidence": intent["confidence"],
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to execute Agent OS workflow: {e!s}",
                "output": None,
                "agent_os_workflow": intent["workflow"],
            }


# Hook entry point for Claude Code
def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Entry point for Claude Code hook execution."""
    import asyncio

    hook = AgentOSWorkflowHook()

    # If the hook method is async, run it in the event loop
    if hasattr(hook.run, "__await__"):
        return asyncio.run(hook.run(input_data))
    return hook.run(input_data)


# Example usage and testing
if __name__ == "__main__":
    # Test the hook with sample input
    test_input = {
        "prompt": "Plan the product for a new task management app",
        "context": {
            "project_type": "web application",
            "tech_stack": ["python", "fastapi", "react"],
        },
    }

    result = run(test_input)
    print("Hook execution result:")
    print(result)
