#!/usr/bin/env python3
"""
Context Portal Memory Hook - Official Claude Code Format
Follows the official Claude Code hooks specification from docs.anthropic.com

This hook captures context from Claude Code tool usage and enhances future
tool calls with relevant historical information from the project database.
"""

import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class ContextPortalMemoryManager:
    """Manages project memory using Context Portal database backend."""

    def __init__(self, project_root: str | None = None):
        """Initialize the Context Portal memory manager."""
        self.project_root = project_root or os.getcwd()
        self.db_path = Path(self.project_root) / ".context-portal" / "project.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize the Context Portal database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    context TEXT,
                    decision TEXT,
                    rationale TEXT,
                    alternatives TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    hash TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    context TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    hash TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    code_example TEXT,
                    use_cases TEXT,
                    category TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hash TEXT UNIQUE
                );

                CREATE TABLE IF NOT EXISTS context_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT,
                    command TEXT,
                    context TEXT,
                    result TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    hash TEXT UNIQUE
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_tags ON decisions(tags);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);
                CREATE INDEX IF NOT EXISTS idx_context_tool ON context_entries(tool_name);
            """)

    def _generate_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def store_decision(
        self,
        title: str,
        description: str = "",
        decision: str = "",
        rationale: str = "",
        alternatives: str = "",
        tags: list[str] = None,
    ) -> bool:
        """Store a project decision in the context portal."""
        tags_str = ",".join(tags or [])
        content_hash = self._generate_hash(f"{title}{description}{decision}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions
                    (title, description, decision, rationale, alternatives, tags, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        title,
                        description,
                        decision,
                        rationale,
                        alternatives,
                        tags_str,
                        content_hash,
                    ),
                )
            return True
        except Exception:
            return False

    def store_context_entry(
        self,
        tool_name: str,
        command: str,
        context: str = "",
        result: str = "",
        session_id: str = "",
    ) -> bool:
        """Store a context entry from tool usage."""
        content_hash = self._generate_hash(f"{tool_name}{command}{context}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO context_entries
                    (tool_name, command, context, result, session_id, hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (tool_name, command, context, result, session_id, content_hash),
                )
            return True
        except Exception:
            return False

    def search_context(
        self, tool_name: str = "", query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search context entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if tool_name:
                    cursor = conn.execute(
                        """
                        SELECT * FROM context_entries
                        WHERE tool_name = ? AND (command LIKE ? OR context LIKE ?)
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """,
                        (tool_name, f"%{query}%", f"%{query}%", limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM context_entries
                        WHERE command LIKE ? OR context LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """,
                        (f"%{query}%", f"%{query}%", limit),
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []


class ContextPortalHook:
    """Official Claude Code hook for Context Portal memory management."""

    def __init__(self):
        """Initialize the Context Portal hook."""
        self.memory_manager = ContextPortalMemoryManager()
        self.session_id = str(int(time.time()))

        # Tools that should trigger context storage
        self.context_tools = {
            "Bash",
            "Edit",
            "Write",
            "Read",
            "Grep",
            "Glob",
            "Task",
            "WebFetch",
            "WebSearch",
        }

        # Keywords that indicate important decisions or patterns
        self.decision_keywords = [
            "decide",
            "choose",
            "implement",
            "architecture",
            "design",
            "pattern",
            "approach",
            "solution",
            "fix",
            "refactor",
        ]

    def should_process(self, tool_name: str) -> bool:
        """Determine if this tool usage should be processed."""
        return tool_name in self.context_tools

    def extract_context_info(
        self, tool_name: str, tool_input: dict[str, Any], session_id: str
    ) -> dict[str, str]:
        """Extract relevant context information from tool input."""
        context_info = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "session": session_id,
        }

        # Extract tool-specific context
        if tool_name == "Bash":
            context_info["command"] = tool_input.get("command", "")
            context_info["description"] = tool_input.get("description", "")
        elif tool_name in ["Edit", "Write"]:
            context_info["file_path"] = tool_input.get("file_path", "")
            context_info["operation"] = "write" if tool_name == "Write" else "edit"
        elif tool_name == "Read":
            context_info["file_path"] = tool_input.get("file_path", "")
            context_info["operation"] = "read"
        elif tool_name in ["Grep", "Glob"]:
            context_info["pattern"] = tool_input.get("pattern", "")
            context_info["path"] = tool_input.get("path", "")
        elif tool_name == "Task":
            context_info["description"] = tool_input.get("description", "")
            context_info["subagent_type"] = tool_input.get("subagent_type", "")
        elif tool_name in ["WebFetch", "WebSearch"]:
            context_info["url_or_query"] = tool_input.get("url", "") or tool_input.get(
                "query", ""
            )

        return context_info

    def detect_decision_context(
        self, tool_input: dict[str, Any]
    ) -> dict[str, str] | None:
        """Detect if tool usage represents an important decision."""
        text_content = " ".join(str(v) for v in tool_input.values()).lower()

        for keyword in self.decision_keywords:
            if keyword in text_content:
                return {
                    "type": "decision",
                    "keyword": keyword,
                    "context": text_content[:500],  # First 500 chars
                }

        return None

    def enhance_with_context(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Enhance tool input with relevant context from memory."""
        # Search for relevant context
        if tool_name == "Bash" and "command" in tool_input:
            command = tool_input["command"]
            relevant_context = self.memory_manager.search_context(
                tool_name="Bash", query=command, limit=3
            )
        elif "file_path" in tool_input:
            file_path = tool_input["file_path"]
            relevant_context = self.memory_manager.search_context(
                query=file_path, limit=3
            )
        else:
            return None

        # Add context as metadata if found
        if relevant_context:
            enhanced_input = tool_input.copy()
            enhanced_input["_context_portal_history"] = relevant_context[
                :2
            ]  # Limit to avoid bloat
            return enhanced_input

        return None

    def process_tool_usage(
        self, tool_name: str, tool_input: dict[str, Any], session_id: str
    ) -> dict[str, Any] | None:
        """Process tool usage and return enhanced input if applicable."""
        if not self.should_process(tool_name):
            return None

        # Store context entry
        context_info = self.extract_context_info(tool_name, tool_input, session_id)
        self.memory_manager.store_context_entry(
            tool_name=tool_name,
            command=str(tool_input),
            context=json.dumps(context_info),
            session_id=session_id,
        )

        # Check for decision context
        decision_context = self.detect_decision_context(tool_input)
        if decision_context:
            self.memory_manager.store_decision(
                title=f"Tool Decision: {tool_name}",
                description=decision_context["context"],
                decision=str(tool_input),
                tags=[decision_context["keyword"], tool_name.lower()],
            )

        # Enhance input with relevant context
        enhanced_input = self.enhance_with_context(tool_name, tool_input)
        return enhanced_input


def main():
    """Main hook entry point following official Claude Code format."""
    try:
        # Read JSON input from stdin (official format)
        input_data = json.loads(sys.stdin.read())

        # Extract standard fields from official Claude Code format
        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        input_data.get("hook_event_name", "")

        # Debug info to stderr (not shown to user normally)
        print(
            f"Context Portal: Processing {tool_name} in session {session_id}",
            file=sys.stderr,
        )

        # Process with Context Portal hook
        hook = ContextPortalHook()
        enhanced_input = hook.process_tool_usage(tool_name, tool_input, session_id)

        if enhanced_input:
            # Tool input was enhanced with context - provide feedback
            print(
                f"Context Portal: Enhanced {tool_name} with {len(enhanced_input.get('_context_portal_history', []))} context entries",
                file=sys.stderr,
            )

            # Use official Claude Code response format
            # Note: We can't directly modify tool_input in PreToolUse,
            # but we can provide information via stderr that Claude can see
            response = {"continue": True, "suppressOutput": False}
            print(json.dumps(response))
        else:
            # No enhancement - allow tool to proceed normally
            # No JSON response needed (exit code 0 is sufficient)
            pass

    except Exception as e:
        # Always fail-safe - log error but don't block execution
        print(f"Context Portal hook error: {str(e)}", file=sys.stderr)
        # Exit code 0 allows tool to proceed
        sys.exit(0)


if __name__ == "__main__":
    main()
