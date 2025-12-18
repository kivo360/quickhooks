#!/usr/bin/env python3
"""Example hook for testing the CLI."""

import json
import sys

from quickhooks.hooks.base import BaseHook
from quickhooks.models import HookInput, HookOutput


class ExampleHook(BaseHook):
    """Example hook that echoes input data back as output."""

    async def execute(self, input_data: HookInput) -> HookOutput:
        """Execute the hook by echoing the input data.

        Args:
            input_data: The input data for the hook

        Returns:
            The output data from the hook
        """
        # Simply return the input data as output
        return HookOutput(
            success=True,
            data=input_data.data,
            metadata={
                "message": "Input data echoed successfully",
                "input_type": type(input_data.data).__name__,
            },
        )

    async def validate_input(self, input_data: HookInput) -> bool:
        """Validate the input data.

        Args:
            input_data: The input data to validate

        Returns:
            True if the input is valid, False otherwise
        """
        # Accept any input for this example
        return True


def main():
    """Main hook entry point following official Claude Code format."""
    try:
        # Read JSON input from stdin (official format)
        input_data = json.loads(sys.stdin.read())

        # Extract standard fields from official Claude Code format
        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        input_data.get("tool_input", {})
        input_data.get("hook_event_name", "")
        input_data.get("transcript_path", "")
        input_data.get("cwd", "")

        # Example hook logic - just log what we received
        print(
            f"Example hook: Processing {tool_name} in session {session_id}",
            file=sys.stderr,
        )

        # Use official Claude Code response format
        response = {"continue": True, "suppressOutput": False}
        print(json.dumps(response))

    except Exception as e:
        # Always fail-safe - log error but don't block execution
        print(f"Example hook error: {e!s}", file=sys.stderr)
        # Exit code 0 allows tool to proceed
        sys.exit(0)


if __name__ == "__main__":
    main()
