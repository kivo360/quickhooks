#!/usr/bin/env -S uv run -s
# /// script
# requires-python = ">=3.12"
# ///
"""
Example Claude Code hook using PEP 723 inline script metadata.

This hook demonstrates the recommended approach for Claude Code hooks:
- Self-contained with inline dependencies (PEP 723)
- Directly executable: ./example_hook_pep723.py
- Dependencies are cached by UV for fast execution
- No separate virtual environment or pyproject.toml needed

Usage in Claude Code settings.json:
{
  "hooks": {
    "example-hook": {
      "command": ".claude/hooks/example_hook_pep723.py",
      "enabled": true
    }
  }
}

Note: This example has no dependencies to demonstrate minimal setup.
For hooks that need quickhooks, add it to dependencies array.
"""

import json
import sys
from typing import Any


def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process a Claude Code hook event.

    Args:
        event_data: Event data from Claude Code with standard fields:
            - session_id: Current session identifier
            - tool_name: Name of the tool being invoked
            - tool_input: Input parameters for the tool
            - hook_event_name: Name of the hook event
            - transcript_path: Path to conversation transcript
            - cwd: Current working directory

    Returns:
        Response dict with:
            - continue: Whether to continue tool execution (default: True)
            - suppressOutput: Whether to suppress tool output (default: False)
            - message: Optional message to display to user
    """
    try:
        # Extract standard Claude Code fields
        session_id = event_data.get("session_id", "unknown")
        tool_name = event_data.get("tool_name", "")
        event_data.get("tool_input", {})
        hook_event = event_data.get("hook_event_name", "")

        # Log event (to stderr to not interfere with JSON output)
        print(
            f"[QuickHooks Example] Processing {hook_event} for {tool_name}",
            file=sys.stderr,
        )
        print(f"[QuickHooks Example] Session: {session_id}", file=sys.stderr)

        # Example: Add metadata to the event
        response_message = f"Hook processed {tool_name} successfully"

        # Return standard Claude Code response
        return {"continue": True, "suppressOutput": False, "message": response_message}

    except Exception as e:
        # Log errors but don't block execution
        print(f"[QuickHooks Example] Error: {e!s}", file=sys.stderr)
        return {"continue": True, "suppressOutput": False}


def main() -> None:
    """Main entry point for the hook."""
    try:
        # Read JSON input from stdin (Claude Code standard)
        input_data = json.loads(sys.stdin.read())

        # Process the event
        response = process_hook_event(input_data)

        # Output JSON response to stdout
        print(json.dumps(response))

        # Exit with success
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"[QuickHooks Example] Invalid JSON input: {e}", file=sys.stderr)
        # Fail-safe: allow execution to continue
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)

    except Exception as e:
        print(f"[QuickHooks Example] Unexpected error: {e}", file=sys.stderr)
        # Fail-safe: allow execution to continue
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)


if __name__ == "__main__":
    main()
