"""Claude Code settings management utilities."""

from quickhooks.claude_code.manager import SettingsManager
from quickhooks.claude_code.models import (
    ClaudeCodeSettings,
    HookCommand,
    HookEventName,
    HookMatcher,
    Permissions,
    StatusLine,
)

__all__ = [
    "ClaudeCodeSettings",
    "HookCommand",
    "HookEventName",
    "HookMatcher",
    "Permissions",
    "SettingsManager",
    "StatusLine",
]
