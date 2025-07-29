#!/usr/bin/env python3
"""
Context Portal Demo Script

Demonstrates the Context Portal Memory Management integration with Claude Code hooks.
This script shows how the Context Portal captures and retrieves project context.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add the hooks directory to the path so we can import the Context Portal modules
sys.path.append(str(Path(__file__).parent.parent / "hooks"))

from context_portal_memory import ContextPortalHook, ContextPortalMemoryManager


def demo_memory_manager():
    """Demonstrate the Context Portal Memory Manager functionality."""
    print("🧠 Context Portal Memory Manager Demo")
    print("=" * 50)

    # Create a temporary directory for the demo
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")

    try:
        # Initialize the memory manager
        manager = ContextPortalMemoryManager(temp_dir)
        print("✅ Memory manager initialized")

        # Store some sample decisions
        print("\n📋 Storing sample decisions...")
        decisions = [
            {
                "title": "Choose React for Frontend",
                "description": "Need a modern frontend framework",
                "decision": "Use React with TypeScript",
                "rationale": "Great ecosystem, TypeScript support, team familiarity",
                "alternatives": "Vue.js, Angular, Svelte",
                "tags": ["frontend", "architecture", "typescript"],
            },
            {
                "title": "Database Selection",
                "description": "Choose database for user data",
                "decision": "PostgreSQL with connection pooling",
                "rationale": "ACID compliance, JSON support, proven reliability",
                "alternatives": "MongoDB, MySQL, SQLite",
                "tags": ["database", "architecture", "backend"],
            },
            {
                "title": "Testing Strategy",
                "description": "Establish testing approach",
                "decision": "Jest + React Testing Library + Cypress",
                "rationale": "Unit tests with Jest, integration with Cypress",
                "alternatives": "Vitest, Playwright, TestCafe",
                "tags": ["testing", "quality", "frontend"],
            },
        ]

        for decision in decisions:
            manager.store_decision(**decision)
            print(f"  ✅ Stored: {decision['title']}")

        # Store some code patterns
        print("\n🔧 Storing code patterns...")
        patterns = [
            {
                "name": "Repository Pattern",
                "description": "Data access abstraction layer",
                "code_example": """
class UserRepository:
    def __init__(self, db_connection):
        self.db = db_connection

    def find_by_id(self, user_id):
        return self.db.query("SELECT * FROM users WHERE id = ?", [user_id])

    def save(self, user):
        return self.db.execute("INSERT INTO users ...", user.to_dict())
                """,
                "use_cases": "Database abstraction, testing, clean architecture",
                "category": "design_patterns",
            },
            {
                "name": "Error Boundary",
                "description": "React error handling component",
                "code_example": """
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Error caught by boundary:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return <h1>Something went wrong.</h1>;
        }
        return this.props.children;
    }
}
                """,
                "use_cases": "Error handling, user experience, debugging",
                "category": "react_patterns",
            },
        ]

        for pattern in patterns:
            manager.store_pattern(**pattern)
            print(f"  ✅ Stored: {pattern['name']}")

        # Store some context entries (simulating tool usage)
        print("\n🔧 Storing context entries...")
        context_entries = [
            {
                "tool_name": "Bash",
                "command": "npm install react react-dom",
                "context": "Setting up React project",
                "result": "Packages installed successfully",
                "session_id": "demo_session_1",
            },
            {
                "tool_name": "Edit",
                "command": "Create App.tsx component",
                "context": "Initial React component setup",
                "result": "Component created with TypeScript",
                "session_id": "demo_session_1",
            },
            {
                "tool_name": "Bash",
                "command": "npm test",
                "context": "Running unit tests",
                "result": "All tests passed",
                "session_id": "demo_session_1",
            },
        ]

        for entry in context_entries:
            manager.store_context_entry(**entry)
            print(f"  ✅ Stored: {entry['tool_name']} - {entry['command'][:30]}...")

        # Demonstrate search functionality
        print("\n🔍 Searching stored content...")

        # Search decisions
        react_decisions = manager.search_decisions("React")
        print(f"\n📋 Found {len(react_decisions)} React-related decisions:")
        for decision in react_decisions:
            print(f"  • {decision['title']}: {decision['decision']}")

        # Search patterns
        design_patterns = manager.search_patterns("", category="design_patterns")
        print(f"\n🔧 Found {len(design_patterns)} design patterns:")
        for pattern in design_patterns:
            print(f"  • {pattern['name']}: {pattern['description']}")

        # Search context
        npm_context = manager.search_context(query="npm")
        print(f"\n📈 Found {len(npm_context)} npm-related commands:")
        for context in npm_context:
            print(f"  • {context['tool_name']}: {context['command']}")

        # Search by tool
        bash_context = manager.search_context(tool_name="Bash")
        print(f"\n💻 Found {len(bash_context)} Bash commands:")
        for context in bash_context:
            print(f"  • {context['command']}")

        print("\n✅ Demo completed successfully!")
        print(f"📊 Database location: {manager.db_path}")

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print("🧹 Cleaned up temporary directory")


def demo_hook_integration():
    """Demonstrate the Context Portal Hook integration."""
    print("\n\n🪝 Context Portal Hook Integration Demo")
    print("=" * 50)

    # Create a temporary directory for the demo
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")

    try:
        # Create a hook instance
        os.chdir(temp_dir)  # Change to temp dir so the hook creates its database there
        hook = ContextPortalHook()
        print("✅ Context Portal hook initialized")

        # Simulate various tool usages
        print("\n🔧 Simulating Claude Code tool usage...")

        tool_scenarios = [
            {
                "name": "Bash Command",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "git init",
                    "description": "Initialize git repository",
                },
            },
            {
                "name": "File Creation",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "src/main.py",
                    "content": "print('Hello, World!')",
                },
            },
            {
                "name": "Decision Context",
                "tool_name": "Task",
                "tool_input": {
                    "description": "Decide on project architecture",
                    "prompt": "We need to choose between microservices and monolithic architecture for our new project",
                },
            },
            {
                "name": "Code Search",
                "tool_name": "Grep",
                "tool_input": {"pattern": "TODO", "path": "src/"},
            },
        ]

        for scenario in tool_scenarios:
            print(f"\n📝 Processing: {scenario['name']}")

            # Check if the hook should process this tool
            should_process = hook.should_process(
                scenario["tool_name"], scenario["tool_input"]
            )
            print(f"  Should process: {should_process}")

            if should_process:
                # Extract context information
                context_info = hook.extract_context_info(
                    scenario["tool_name"], scenario["tool_input"]
                )
                print(
                    f"  Context extracted: {context_info['tool']} at {context_info['timestamp'][:19]}"
                )

                # Check for decision context
                decision_context = hook.detect_decision_context(scenario["tool_input"])
                if decision_context:
                    print(f"  🎯 Decision detected: {decision_context['keyword']}")

                # Transform the tool input
                result = hook.transform(scenario["tool_name"], scenario["tool_input"])
                if result:
                    print("  ✨ Tool input enhanced with context")
                    if "_context_portal_history" in result:
                        print(
                            f"    Added {len(result['_context_portal_history'])} historical entries"
                        )
                else:
                    print("  📝 Context stored, no enhancement needed")

        # Demonstrate context retrieval
        print("\n🔍 Retrieving stored context...")

        # Search for stored context entries
        all_context = hook.memory_manager.search_context()
        print(f"Total context entries: {len(all_context)}")

        for entry in all_context[:5]:  # Show first 5 entries
            print(f"  • {entry['tool_name']}: {entry['command'][:50]}...")

        # Search for decisions
        decisions = hook.memory_manager.search_decisions("architecture")
        print(f"\nDecisions about architecture: {len(decisions)}")

        for decision in decisions:
            print(f"  • {decision['title']}")

        print("\n✅ Hook integration demo completed!")

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print("🧹 Cleaned up temporary directory")


def demo_json_hook_interface():
    """Demonstrate the JSON hook interface that Claude Code uses."""
    print("\n\n📡 JSON Hook Interface Demo")
    print("=" * 50)

    # Sample JSON inputs that Claude Code would send to the hook
    sample_inputs = [
        {
            "name": "Bash Command",
            "input": {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "npm run build",
                    "description": "Build the project",
                },
            },
        },
        {
            "name": "File Edit",
            "input": {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "src/config.py",
                    "old_string": "DEBUG = True",
                    "new_string": "DEBUG = False",
                },
            },
        },
        {
            "name": "Architecture Decision",
            "input": {
                "tool_name": "Task",
                "tool_input": {
                    "description": "Choose deployment strategy",
                    "prompt": "We need to decide between Docker containers and traditional server deployment",
                },
            },
        },
    ]

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary directory: {temp_dir}")

    try:
        hook_script = (
            Path(__file__).parent.parent / "hooks" / "context_portal_memory.py"
        )

        for scenario in sample_inputs:
            print(f"\n📝 Testing: {scenario['name']}")
            print(f"  Input: {json.dumps(scenario['input'], indent=2)}")

            # Run the hook script with the JSON input
            import subprocess

            process = subprocess.run(
                ["python", str(hook_script)],
                input=json.dumps(scenario["input"]),
                capture_output=True,
                text=True,
                cwd=temp_dir,
            )

            if process.returncode == 0:
                try:
                    output = json.loads(process.stdout)
                    print(f"  ✅ Output: {json.dumps(output, indent=2)}")

                    # Highlight key information
                    if output.get("modified"):
                        print("    🔧 Tool input was enhanced with context")
                    if output.get("message"):
                        print(f"    💬 Message: {output['message']}")

                except json.JSONDecodeError:
                    print(f"  ❌ Invalid JSON output: {process.stdout}")
            else:
                print(f"  ❌ Hook failed: {process.stderr}")

        print("\n✅ JSON interface demo completed!")

    finally:
        shutil.rmtree(temp_dir)
        print("🧹 Cleaned up temporary directory")


def main():
    """Run all demonstrations."""
    print("🚀 Context Portal Integration Demo")
    print("=" * 60)
    print("This demo shows how Context Portal integrates with Claude Code")
    print("to provide automatic project memory management.")
    print("=" * 60)

    try:
        # Run all demos
        demo_memory_manager()
        demo_hook_integration()
        demo_json_hook_interface()

        print("\n🎉 All demos completed successfully!")
        print("\nTo use Context Portal in your project:")
        print(
            "1. Copy hooks/context_portal_memory.py to your project's hooks/ directory"
        )
        print("2. Copy examples/config_with_context_portal.yaml to quickhooks.yaml")
        print("3. Make the hook executable: chmod +x hooks/context_portal_memory.py")
        print("4. Start using Claude Code - context will be captured automatically!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
