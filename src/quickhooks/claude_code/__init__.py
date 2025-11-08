"""Claude Code settings management utilities."""

from quickhooks.claude_code.models import (
    ClaudeCodeSettings,
    HookCommand,
    HookMatcher,
    Permissions,
    StatusLine,
)
from quickhooks.claude_code.manager import SettingsManager

__all__ = [
    "ClaudeCodeSettings",
    "HookCommand",
    "HookMatcher",
    "Permissions",
    "StatusLine",
    "SettingsManager",
]
