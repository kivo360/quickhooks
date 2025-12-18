"""Settings manager for Claude Code settings.json manipulation.

This module provides utilities for safely reading, updating, and validating
Claude Code settings.json files.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from quickhooks.claude_code.models import (
    ClaudeCodeSettings,
    HookCommand,
    HookEventName,
    HookMatcher,
    Permissions,
)


class SettingsManager:
    """Manage Claude Code settings.json files with type safety and validation.

    This class provides a high-level interface for reading, updating, and
    validating Claude Code settings files using Pydantic models.

    Example:
        >>> manager = SettingsManager(".claude/settings.json")
        >>> settings = manager.load()
        >>> manager.add_hook(
        ...     HookEventName.USER_PROMPT_SUBMIT,
        ...     HookCommand(
        ...         type="command",
        ...         command=".claude/hooks/my_hook.py",
        ...     ),
        ... )
        >>> manager.save()
    """

    def __init__(self, settings_path: str | Path):
        """Initialize the settings manager.

        Args:
            settings_path: Path to the settings.json file
        """
        self.settings_path = Path(settings_path)
        self.settings: ClaudeCodeSettings | None = None
        self._raw_data: dict[str, Any] = {}

    def load(self, create_if_missing: bool = False) -> ClaudeCodeSettings:
        """Load settings from file.

        Args:
            create_if_missing: Create a new settings file if it doesn't exist

        Returns:
            Loaded and validated settings

        Raises:
            FileNotFoundError: If file doesn't exist and create_if_missing=False
            ValidationError: If settings file is invalid
        """
        if not self.settings_path.exists():
            if create_if_missing:
                self.settings = ClaudeCodeSettings()
                self._raw_data = {}
                return self.settings
            msg = f"Settings file not found: {self.settings_path}"
            raise FileNotFoundError(msg)

        with open(self.settings_path) as f:
            self._raw_data = json.load(f)

        try:
            self.settings = ClaudeCodeSettings.model_validate(self._raw_data)
            return self.settings
        except ValidationError as e:
            msg = f"Invalid settings file at {self.settings_path}: {e}"
            raise ValidationError(msg) from e

    def save(self, indent: int = 2) -> None:
        """Save current settings to file.

        Args:
            indent: Number of spaces for JSON indentation

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        # Ensure parent directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Merge with any extra fields from original file
        output_data = self.settings.model_dump()

        # Preserve any additional fields that aren't in the model
        for key, value in self._raw_data.items():
            if key not in output_data:
                output_data[key] = value

        with open(self.settings_path, "w") as f:
            json.dump(output_data, f, indent=indent)

    def validate_schema(self, schema_path: str | Path | None = None) -> bool:
        """Validate settings against JSON schema.

        Args:
            schema_path: Path to schema file (defaults to .claude/settings_schema.json)

        Returns:
            True if valid

        Raises:
            ValidationError: If settings don't match schema
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if schema_path is None:
            schema_path = self.settings_path.parent / "settings_schema.json"

        schema_path = Path(schema_path)
        if not schema_path.exists():
            msg = f"Schema file not found: {schema_path}"
            raise FileNotFoundError(msg)

        with open(schema_path) as f:
            schema = json.load(f)

        # Use jsonschema for validation
        try:
            import jsonschema

            jsonschema.validate(self.settings.model_dump(), schema)
            return True
        except ImportError:
            # Fallback to Pydantic validation only
            return True
        except jsonschema.ValidationError as e:
            msg = f"Schema validation failed: {e}"
            raise ValidationError(msg) from e

    # Hook Management Methods

    def add_hook(
        self,
        event: HookEventName | str,
        command: HookCommand,
        matcher: str | None = None,
    ) -> None:
        """Add a hook to the settings.

        Args:
            event: Hook event name (e.g., HookEventName.USER_PROMPT_SUBMIT)
            command: Hook command configuration
            matcher: Optional pattern to match tool names

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        # Convert string to enum if needed
        if isinstance(event, str):
            event = HookEventName(event)

        # Initialize hooks dict if needed
        if self.settings.hooks is None:
            self.settings.hooks = {}

        event_name = event.value

        # Find existing matcher or create new one
        if event_name not in self.settings.hooks:
            self.settings.hooks[event_name] = []

        # Look for existing matcher with same pattern
        existing_matcher = None
        for hook_matcher in self.settings.hooks[event_name]:
            if hook_matcher.matcher == matcher:
                existing_matcher = hook_matcher
                break

        if existing_matcher:
            # Add to existing matcher
            existing_matcher.hooks.append(command)
        else:
            # Create new matcher
            new_matcher = HookMatcher(matcher=matcher, hooks=[command])
            self.settings.hooks[event_name].append(new_matcher)

    def remove_hook(
        self,
        event: HookEventName | str,
        command_pattern: str,
        matcher: str | None = None,
    ) -> bool:
        """Remove hooks matching a pattern.

        Args:
            event: Hook event name
            command_pattern: Pattern to match command strings
            matcher: Optional pattern to match tool names

        Returns:
            True if any hooks were removed

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if self.settings.hooks is None:
            return False

        # Convert string to enum if needed
        if isinstance(event, str):
            event = HookEventName(event)

        event_name = event.value

        if event_name not in self.settings.hooks:
            return False

        removed = False

        # Find matching matchers
        for hook_matcher in self.settings.hooks[event_name][:]:
            if matcher is None or hook_matcher.matcher == matcher:
                # Remove matching commands
                original_len = len(hook_matcher.hooks)
                hook_matcher.hooks = [
                    cmd
                    for cmd in hook_matcher.hooks
                    if command_pattern not in cmd.command
                ]

                if len(hook_matcher.hooks) < original_len:
                    removed = True

                # Remove empty matchers
                if not hook_matcher.hooks:
                    self.settings.hooks[event_name].remove(hook_matcher)

        # Remove empty event arrays
        if not self.settings.hooks[event_name]:
            del self.settings.hooks[event_name]

        return removed

    def list_hooks(
        self, event: HookEventName | str | None = None
    ) -> dict[str, list[HookMatcher]]:
        """List all hooks or hooks for a specific event.

        Args:
            event: Optional event to filter by

        Returns:
            Dictionary of hook event names to matchers

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if self.settings.hooks is None:
            return {}

        if event is None:
            return self.settings.hooks.copy()

        # Convert string to enum if needed
        if isinstance(event, str):
            event = HookEventName(event)

        event_name = event.value

        if event_name in self.settings.hooks:
            return {event_name: self.settings.hooks[event_name]}

        return {}

    # Environment Variable Methods

    def set_env(self, key: str, value: str) -> None:
        """Set an environment variable.

        Args:
            key: Environment variable name (must match ^[A-Z_][A-Z0-9_]*$)
            value: Environment variable value

        Raises:
            ValueError: If no settings are loaded or key is invalid
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        import re

        if not re.match(r"^[A-Z_][A-Z0-9_]*$", key):
            msg = f"Invalid environment variable name '{key}'. Must match ^[A-Z_][A-Z0-9_]*$"
            raise ValueError(msg)

        if self.settings.env is None:
            self.settings.env = {}

        self.settings.env[key] = value

    def get_env(self, key: str, default: str | None = None) -> str | None:
        """Get an environment variable value.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if self.settings.env is None:
            return default

        return self.settings.env.get(key, default)

    def remove_env(self, key: str) -> bool:
        """Remove an environment variable.

        Args:
            key: Environment variable name

        Returns:
            True if variable was removed

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if self.settings.env is None:
            return False

        if key in self.settings.env:
            del self.settings.env[key]
            return True

        return False

    def list_env(self) -> dict[str, str]:
        """List all environment variables.

        Returns:
            Dictionary of environment variables

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        return (self.settings.env or {}).copy()

    # Permission Methods

    def add_permission(
        self, permission_type: str, rule: str, mode: str | None = None
    ) -> None:
        """Add a permission rule.

        Args:
            permission_type: "allow", "ask", or "deny"
            rule: Permission rule (e.g., "Bash(git add:*)")
            mode: Optional default mode to set

        Raises:
            ValueError: If no settings are loaded or invalid permission type
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if permission_type not in {"allow", "ask", "deny"}:
            msg = f"Invalid permission type '{permission_type}'. Must be 'allow', 'ask', or 'deny'"
            raise ValueError(msg)

        if self.settings.permissions is None:
            self.settings.permissions = Permissions()

        rules_list = getattr(self.settings.permissions, permission_type)
        if rules_list is None:
            rules_list = []
            setattr(self.settings.permissions, permission_type, rules_list)

        if rule not in rules_list:
            rules_list.append(rule)

        if mode is not None:
            from quickhooks.claude_code.models import PermissionMode

            self.settings.permissions.default_mode = PermissionMode(mode)

    def remove_permission(self, permission_type: str, rule: str) -> bool:
        """Remove a permission rule.

        Args:
            permission_type: "allow", "ask", or "deny"
            rule: Permission rule to remove

        Returns:
            True if rule was removed

        Raises:
            ValueError: If no settings are loaded or invalid permission type
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        if permission_type not in {"allow", "ask", "deny"}:
            msg = f"Invalid permission type '{permission_type}'. Must be 'allow', 'ask', or 'deny'"
            raise ValueError(msg)

        if self.settings.permissions is None:
            return False

        rules_list = getattr(self.settings.permissions, permission_type)
        if rules_list is None:
            return False

        if rule in rules_list:
            rules_list.remove(rule)
            return True

        return False

    # Utility Methods

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary.

        Returns:
            Settings as dictionary

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        return self.settings.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Convert settings to JSON string.

        Args:
            indent: Number of spaces for indentation

        Returns:
            Settings as JSON string

        Raises:
            ValueError: If no settings are loaded
        """
        if self.settings is None:
            msg = "No settings loaded. Call load() first."
            raise ValueError(msg)

        return json.dumps(self.settings.model_dump(), indent=indent)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], settings_path: str | Path
    ) -> "SettingsManager":
        """Create a SettingsManager from a dictionary.

        Args:
            data: Settings data
            settings_path: Path where settings will be saved

        Returns:
            New SettingsManager instance
        """
        manager = cls(settings_path)
        manager.settings = ClaudeCodeSettings.model_validate(data)
        manager._raw_data = data
        return manager

    @classmethod
    def from_json(cls, json_str: str, settings_path: str | Path) -> "SettingsManager":
        """Create a SettingsManager from a JSON string.

        Args:
            json_str: JSON settings string
            settings_path: Path where settings will be saved

        Returns:
            New SettingsManager instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data, settings_path)
