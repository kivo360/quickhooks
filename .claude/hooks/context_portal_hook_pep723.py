#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#   "quickhooks>=0.1.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Context Portal hook for Claude Code using PEP 723 inline dependencies.

This hook provides persistent memory and context management across sessions:
- Stores important context from conversations
- Retrieves relevant context for new prompts
- Maintains conversation continuity
- Tracks project-specific knowledge

Configuration via environment variables:
- QUICKHOOKS_CONTEXT_PORTAL_ENABLED (default: "true"): Enable/disable hook
- QUICKHOOKS_CONTEXT_DB_PATH (default: "~/.quickhooks/context_db"): Database path
- QUICKHOOKS_VERBOSE (default: "false"): Verbose logging

Usage in Claude Code settings.json:
{
  "hooks": {
    "user-prompt-submit": {
      "command": "uv run -s /path/to/.claude/hooks/context_portal_hook_pep723.py",
      "enabled": true
    }
  },
  "environment": {
    "QUICKHOOKS_CONTEXT_PORTAL_ENABLED": "true",
    "QUICKHOOKS_VERBOSE": "false"
  }
}
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


class ContextPortalHook:
    """Hook that provides persistent context and memory management."""

    def __init__(self):
        """Initialize the context portal hook."""
        self.enabled = (
            os.getenv("QUICKHOOKS_CONTEXT_PORTAL_ENABLED", "true").lower() == "true"
        )
        self.verbose = os.getenv("QUICKHOOKS_VERBOSE", "false").lower() == "true"

        # Set up context database path
        db_path = os.getenv("QUICKHOOKS_CONTEXT_DB_PATH", "~/.quickhooks/context_db")
        self.db_path = Path(db_path).expanduser()
        self.db_path.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            print(f"[QuickHooks Context Portal] Initialized with db at {self.db_path}", file=sys.stderr)

    def store_context(self, session_id: str, prompt: str, context: str = "") -> None:
        """
        Store context for a session.

        Args:
            session_id: Session identifier
            prompt: User prompt
            context: Additional context
        """
        if not self.enabled:
            return

        try:
            # Create a simple context file for the session
            context_file = self.db_path / f"{session_id}_context.json"

            # Load existing context if available
            if context_file.exists():
                with open(context_file, 'r') as f:
                    existing_context = json.load(f)
            else:
                existing_context = {"prompts": [], "metadata": {}}

            # Add new prompt to context
            existing_context["prompts"].append({
                "prompt": prompt,
                "context": context,
                "timestamp": str(Path(context_file).stat().st_mtime if context_file.exists() else 0)
            })

            # Save updated context
            with open(context_file, 'w') as f:
                json.dump(existing_context, f, indent=2)

            if self.verbose:
                print(f"[QuickHooks Context Portal] Stored context for session {session_id}", file=sys.stderr)

        except Exception as e:
            print(f"[QuickHooks Context Portal] Error storing context: {e}", file=sys.stderr)

    def retrieve_context(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve context for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session context
        """
        if not self.enabled:
            return {}

        try:
            context_file = self.db_path / f"{session_id}_context.json"

            if context_file.exists():
                with open(context_file, 'r') as f:
                    context_data = json.load(f)

                if self.verbose:
                    print(f"[QuickHooks Context Portal] Retrieved {len(context_data.get('prompts', []))} prompts for session {session_id}", file=sys.stderr)

                return context_data

            return {}

        except Exception as e:
            print(f"[QuickHooks Context Portal] Error retrieving context: {e}", file=sys.stderr)
            return {}


# Global hook instance
_hook_instance = None


def get_hook_instance() -> ContextPortalHook:
    """Get or create the global hook instance."""
    global _hook_instance
    if _hook_instance is None:
        _hook_instance = ContextPortalHook()
    return _hook_instance


def process_hook_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process user prompt submit event.

    Args:
        event_data: Event data from Claude Code

    Returns:
        Response dictionary
    """
    hook = get_hook_instance()

    # Extract event data
    session_id = event_data.get("session_id", "unknown")
    prompt = event_data.get("prompt", "")
    context = event_data.get("context", "")

    # Retrieve existing context
    existing_context = hook.retrieve_context(session_id)

    # Store new context
    hook.store_context(session_id, prompt, context)

    # Build response
    response = {
        "continue": True,
        "suppressOutput": False,
    }

    if existing_context and existing_context.get("prompts"):
        num_prompts = len(existing_context["prompts"])
        if hook.verbose:
            response["message"] = f"Retrieved {num_prompts} previous prompts from context"

    return response


def main() -> None:
    """Main entry point for the hook."""
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Process the event
        response = process_hook_event(input_data)

        # Output JSON response
        print(json.dumps(response))

        sys.exit(0)

    except Exception as e:
        print(f"[QuickHooks Context Portal] Error: {e}", file=sys.stderr)
        # Fail-safe: allow execution to continue
        print(json.dumps({"continue": True, "suppressOutput": False}))
        sys.exit(0)


if __name__ == "__main__":
    main()
