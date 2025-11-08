#!/usr/bin/env python3
"""
SessionEnd Hook Example for Claude Code

This hook runs when a Claude Code session ends.
It demonstrates how to perform cleanup, save session state,
log session metrics, and archive important information.

Key Features:
- Runs at session termination
- Logged to debug only (use --debug flag to see output)
- Perfect for cleanup and final operations
- Can save session metadata and metrics

Usage:
Add to .claude/settings.json:
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.quickhooks/hooks/session_end_example.py"
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


def save_session_metadata(session_id: str, cwd: str, transcript_path: str) -> dict:
    """
    Save session metadata for analytics and history.

    Args:
        session_id: Unique session identifier
        cwd: Current working directory
        transcript_path: Path to session transcript

    Returns:
        Dictionary with session metadata
    """
    metadata = {
        "session_id": session_id,
        "ended_at": datetime.now().isoformat(),
        "working_directory": cwd,
        "transcript_path": transcript_path,
    }

    # Create sessions directory
    sessions_dir = Path.home() / ".quickhooks" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    metadata_file = sessions_dir / f"{session_id}.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def calculate_session_metrics(transcript_path: str) -> dict:
    """
    Calculate session metrics from the transcript.

    Args:
        transcript_path: Path to session transcript

    Returns:
        Dictionary with session metrics
    """
    metrics = {
        "transcript_exists": False,
        "file_size": 0,
    }

    try:
        transcript = Path(transcript_path)
        if transcript.exists():
            metrics["transcript_exists"] = True
            metrics["file_size"] = transcript.stat().st_size
            metrics["file_size_mb"] = round(metrics["file_size"] / (1024 * 1024), 2)
    except Exception:
        pass

    return metrics


def cleanup_temp_files(cwd: str):
    """
    Clean up temporary files created during the session.

    Args:
        cwd: Current working directory
    """
    # Add any cleanup logic here
    # For example, removing temporary files, clearing caches, etc.
    pass


def archive_session_logs(session_id: str):
    """
    Archive session logs for future reference.

    Args:
        session_id: Unique session identifier
    """
    logs_dir = Path.home() / ".quickhooks" / "logs"
    if logs_dir.exists():
        # Archive logic here
        pass


def main():
    """Main hook execution."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        session_id = input_data.get("session_id", "unknown")
        cwd = input_data.get("cwd", os.getcwd())
        transcript_path = input_data.get("transcript_path", "")

        # Save session metadata
        metadata = save_session_metadata(session_id, cwd, transcript_path)

        # Calculate metrics
        metrics = calculate_session_metrics(transcript_path)

        # Perform cleanup
        cleanup_temp_files(cwd)

        # Archive logs
        archive_session_logs(session_id)

        # Create response (logged to debug only)
        response = {
            "continue": True,
        }

        # Output response to stdout
        print(json.dumps(response))

        # Log session end info to stderr (visible with --debug)
        print("=" * 60, file=sys.stderr)
        print("[SessionEnd Hook] Session Ended", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Session ID: {session_id}", file=sys.stderr)
        print(f"Working Directory: {cwd}", file=sys.stderr)
        print(f"Transcript: {transcript_path}", file=sys.stderr)

        if metrics["transcript_exists"]:
            print(f"Transcript Size: {metrics['file_size_mb']} MB", file=sys.stderr)

        print(f"Metadata saved to: ~/.quickhooks/sessions/{session_id}.json", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # Error handling
        error_response = {
            "continue": True,  # Don't block session end on errors
        }
        print(json.dumps(error_response))
        print(f"[SessionEnd Hook] Error: {str(e)}", file=sys.stderr)
        sys.exit(0)  # Exit successfully even on errors


if __name__ == "__main__":
    main()
