#!/usr/bin/env python3
"""
Agent OS integration demo for QuickHooks.

This script demonstrates how to use the Agent OS integration
to execute instructions and workflows programmatically.
"""

import asyncio
import json
from pathlib import Path

from quickhooks.agent_os import AgentOSExecutor, WorkflowManager
from quickhooks.agent_os.hooks import AgentOSHook
from quickhooks.models import HookInput


async def demo_instruction_execution():
    """Demonstrate executing a single Agent OS instruction."""
    print("=== Agent OS Instruction Execution Demo ===\n")

    # Initialize executor
    executor = AgentOSExecutor(verbose=True)

    # List available instructions
    instructions = executor.list_available_instructions("core")
    print(f"Available instructions: {instructions[:3]}...\n")  # Show first 3

    # Execute an instruction (if available)
    if "plan-product" in instructions:
        print("Executing 'plan-product' instruction...")

        context = {
            "project_type": "web application",
            "main_features": [
                "user authentication",
                "data visualization",
                "real-time updates",
            ],
            "target_users": "data analysts and business users",
            "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
        }

        result = await executor.execute_instruction(
            "plan-product", category="core", context=context
        )

        print(f"Status: {result.status.value}")
        if result.output and result.output.data:
            print("Results:")
            print(json.dumps(result.output.data, indent=2))
    else:
        print("'plan-product' instruction not found")

    print("\n" + "=" * 50 + "\n")


async def demo_workflow_execution():
    """Demonstrate executing an Agent OS workflow."""
    print("=== Agent OS Workflow Execution Demo ===\n")

    # Initialize workflow manager
    manager = WorkflowManager()

    # Initialize predefined workflows
    manager.create_predefined_workflows()

    # List available workflows
    workflows = manager.list_workflows()
    print(f"Available workflows: {workflows}\n")

    # Execute a workflow (if available)
    if "product-planning" in workflows:
        print("Executing 'product-planning' workflow...")

        context = {
            "project_idea": "AI-powered task management system",
            "key_features": [
                "Intelligent task prioritization",
                "Team collaboration tools",
                "Progress analytics dashboard",
            ],
            "target_users": "Software development teams",
            "tech_preferences": ["Python", "React", "PostgreSQL", "Docker"],
            "working_directory": str(Path.cwd()),
        }

        final_state = await manager.execute_workflow(
            "product-planning", context=context
        )

        print(f"Workflow Status: {final_state.status}")
        print(
            f"Completed Steps: {len(final_state.completed_steps)}/{len(final_state.step_results)}"
        )

        if final_state.step_results:
            print("\nStep Results:")
            for step_name, result in final_state.step_results.items():
                status_icon = (
                    "✓"
                    if hasattr(result, "status") and result.status.value == "succeeded"
                    else "✗"
                )
                print(f"  {status_icon} {step_name}")

        if final_state.context.get("error"):
            print(f"Error: {final_state.context['error']}")
    else:
        print("'product-planning' workflow not found")

    print("\n" + "=" * 50 + "\n")


async def demo_hook_integration():
    """Demonstrate using Agent OS hooks."""
    print("=== Agent OS Hook Integration Demo ===\n")

    # Test instruction hook
    print("Testing Agent OS instruction hook...")

    hook_input = HookInput(
        data={
            "prompt": "Create specifications for a user authentication system",
            "project_context": {
                "project_type": "web_api",
                "tech_stack": ["FastAPI", "PostgreSQL", "JWT"],
            },
        },
        context={"verbose": True, "working_directory": str(Path.cwd())},
    )

    # Create and execute instruction hook
    instruction_hook = AgentOSHook(instruction="create-spec", category="core")

    result = await instruction_hook.execute(hook_input)

    print(f"Hook Status: {result.status.value}")
    if result.output and result.output.data:
        print("Hook Results:")
        print(json.dumps(result.output.data, indent=2))

    print("\n" + "=" * 50 + "\n")


def demo_custom_workflow():
    """Demonstrate creating custom workflows."""
    print("=== Custom Workflow Creation Demo ===\n")

    manager = WorkflowManager()

    # Create custom workflow steps
    from quickhooks.agent_os.workflow_manager import WorkflowStep

    steps = [
        WorkflowStep(
            instruction="plan-product",
            category="core",
            description="Initial product planning and structure",
        ),
        WorkflowStep(
            instruction="create-spec",
            category="core",
            description="Create technical specifications",
            depends_on=["plan-product"],
        ),
        WorkflowStep(
            instruction="analyze-product",
            category="core",
            description="Analyze requirements and dependencies",
            depends_on=["create-spec"],
        ),
    ]

    # Create custom workflow
    workflow = manager.create_workflow(
        name="demo-workflow",
        description="Demo workflow for Agent OS integration",
        steps=steps,
        metadata={"tags": ["demo", "integration"], "estimated_time": "30-45 minutes"},
    )

    print(f"Created workflow: {workflow.name}")
    print(f"Description: {workflow.description}")
    print(f"Steps: {len(workflow.steps)}")

    for i, step in enumerate(workflow.steps, 1):
        deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
        print(f"  {i}. {step.instruction}{deps}")

    print("\n" + "=" * 50 + "\n")


async def main():
    """Run all demos."""
    print("QuickHooks Agent OS Integration Demo\n")
    print("This demo showcases the Agent OS integration capabilities.")
    print("Make sure you have Agent OS installed at ~/.agent-os\n")

    try:
        # Check if Agent OS is available
        agent_os_path = Path.home() / ".agent-os"
        if not agent_os_path.exists():
            print("⚠️  Agent OS not found at ~/.agent-os")
            print("Please install Agent OS first: https://buildermethods.com/agent-os")
            print("This demo will show the integration structure anyway.\n")

        # Run demos
        await demo_instruction_execution()
        await demo_workflow_execution()
        await demo_hook_integration()
        demo_custom_workflow()

        print("✅ All demos completed successfully!")
        print("\nTo try it yourself:")
        print("1. Install Agent OS: https://buildermethods.com/agent-os")
        print("2. Install QuickHooks with Agent OS: pip install quickhooks[agent_os]")
        print("3. Run: quickhooks agent-os list-instructions")
        print("4. Run: quickhooks agent-os execute-instruction plan-product")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("This is expected if Agent OS is not installed.")


if __name__ == "__main__":
    asyncio.run(main())
