#!/usr/bin/env python3
"""
SessionStart Hook Example for Claude Code

This hook runs when a Claude Code session starts or resumes.
It demonstrates how to inject initial context, load configurations,
and set up the environment for the session.

Key Features:
- Runs at session initialization
- Has exclusive access to CLAUDE_ENV_FILE environment variable
- Output is added as context for Claude
- Can detect session source (new/resume/restore)

Usage:
Add to .claude/settings.json:
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.quickhooks/hooks/session_start_example.py"
          }
        ]
      }
    ]
  }
}

Author: QuickHooks Framework
Version: 1.0.0
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_project_context(cwd: str) -> dict:
    """
    Load project-specific context from configuration files.

    Args:
        cwd: Current working directory

    Returns:
        Dictionary with project context
    """
    context = {
        "project_name": Path(cwd).name,
        "working_directory": cwd,
        "timestamp": datetime.now().isoformat(),
    }

    # Check for common project files
    cwd_path = Path(cwd)

    # Check for package.json
    package_json = cwd_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                data = json.load(f)
                context["project_type"] = "Node.js"
                context["project_name"] = data.get("name", context["project_name"])
                context["version"] = data.get("version", "unknown")
        except Exception:
            pass

    # Check for pyproject.toml
    pyproject = cwd_path / "pyproject.toml"
    if pyproject.exists():
        context["project_type"] = "Python"
        context["has_pyproject"] = True

    # Check for README
    readme_files = list(cwd_path.glob("README*"))
    if readme_files:
        context["has_readme"] = True
        context["readme_path"] = str(readme_files[0])

    return context


def get_session_info(source: str) -> str:
    """
    Get human-readable session information.

    Args:
        source: Session source (new/resume/restore)

    Returns:
        Formatted session info string
    """
    source_messages = {
        "new": "Starting a new Claude Code session",
        "resume": "Resuming an existing session",
        "restore": "Restoring a previous session",
    }
    return source_messages.get(source, f"Session started (source: {source})")


def main():
    """Main hook execution."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        session_id = input_data.get("session_id", "unknown")
        cwd = input_data.get("cwd", os.getcwd())
        source = input_data.get("source", "unknown")

        # Load project context
        project_context = load_project_context(cwd)

        # Build context message for Claude
        context_parts = [
            f"# Session Started: {get_session_info(source)}",
            f"Session ID: {session_id}",
            f"Project: {project_context['project_name']}",
            f"Directory: {cwd}",
            "",
        ]

        # Add project-specific information
        if "project_type" in project_context:
            context_parts.append(f"Project Type: {project_context['project_type']}")

        if "version" in project_context:
            context_parts.append(f"Version: {project_context['version']}")

        if "has_readme" in project_context:
            context_parts.append(f"README available at: {project_context['readme_path']}")

        # Check for CLAUDE_ENV_FILE (exclusive to SessionStart)
        env_file = os.getenv("CLAUDE_ENV_FILE")
        if env_file:
            context_parts.append(f"Environment file: {env_file}")

        context_parts.extend([
            "",
            "You can now start working on this project. Feel free to ask about the project structure or any specific files.",
        ])

        context_message = "\n".join(context_parts)

        # Create response
        response = {
            "continue": True,
            "additionalContext": context_message,
        }

        # Output response to stdout (will be added as Claude context)
        print(json.dumps(response))

        # Log to stderr for debugging (visible with --debug)
        print(f"[SessionStart Hook] Loaded context for {project_context['project_name']}", file=sys.stderr)
        print(f"[SessionStart Hook] Session source: {source}", file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # Error handling - exit with code 2 for blocking
        error_response = {
            "continue": False,
            "stopReason": f"SessionStart hook error: {str(e)}",
        }
        print(json.dumps(error_response))
        print(f"[SessionStart Hook] Error: {str(e)}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
