"""JSON Schema validation for Claude Code settings."""

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import ValidationError, validate

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class ClaudeSettingsValidator:
    """Validates Claude Code settings against the official JSON schema."""

    def __init__(self):
        """Initialize the validator with the Claude Code schema."""
        schema_path = Path(__file__).parent / "claude_settings_schema.json"
        with open(schema_path) as f:
            self.schema = json.load(f)

    def validate_settings(self, settings: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate Claude Code settings against the official schema.

        Args:
            settings: Settings dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not JSONSCHEMA_AVAILABLE:
            return True, ["Warning: jsonschema not available, skipping validation"]

        errors = []
        try:
            validate(instance=settings, schema=self.schema)
            return True, []
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            if e.path:
                errors.append(f"  At path: {' -> '.join(str(p) for p in e.path)}")
            return False, errors
        except Exception as e:
            return False, [f"Validation failed: {str(e)}"]

    def validate_hook_configuration(
        self, hooks_config: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate just the hooks configuration section.

        Args:
            hooks_config: Hooks configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Create a minimal settings object with just the hooks section
        test_settings = {"hooks": hooks_config}
        return self.validate_settings(test_settings)

    def create_valid_hook_config(
        self,
        hook_type: str,
        matcher: str | None,
        command: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a valid hook configuration following the schema.

        Args:
            hook_type: Type of hook (PreToolUse, PostToolUse, etc.)
            matcher: Optional matcher pattern
            command: Command to execute
            timeout: Optional timeout in seconds

        Returns:
            Valid hook configuration dictionary
        """
        if hook_type not in [
            "PreToolUse",
            "PostToolUse",
            "Notification",
            "UserPromptSubmit",
            "Stop",
            "SubagentStop",
            "PreCompact",
        ]:
            raise ValueError(f"Invalid hook type: {hook_type}")

        hook_command = {"type": "command", "command": command}

        if timeout is not None:
            if timeout <= 0:
                raise ValueError("Timeout must be greater than 0")
            hook_command["timeout"] = timeout

        hook_matcher = {"hooks": [hook_command]}

        if matcher is not None:
            hook_matcher["matcher"] = matcher

        return {hook_type: [hook_matcher]}

    def get_valid_tools_for_matcher(self) -> list[str]:
        """
        Get list of valid tools that can be used in matchers.
        Note: Matchers for hooks can include additional tools beyond permissions.

        Returns:
            List of valid tool names for hook matchers
        """
        # These are the tools that can be used in hook matchers
        # (broader than permission rules which are more restrictive)
        return [
            "Agent",
            "Bash",
            "Edit",
            "Glob",
            "Grep",
            "LS",
            "MultiEdit",
            "NotebookEdit",
            "NotebookRead",
            "Read",
            "Task",
            "TodoRead",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Write",
        ]

    def suggest_matcher_pattern(self, tools: list[str]) -> str:
        """
        Create a regex matcher pattern for multiple tools.

        Args:
            tools: List of tool names to match

        Returns:
            Regex pattern string
        """
        valid_tools = self.get_valid_tools_for_matcher()
        invalid_tools = [tool for tool in tools if tool not in valid_tools]

        if invalid_tools:
            raise ValueError(f"Invalid tools for matcher: {invalid_tools}")

        if len(tools) == 1:
            return tools[0]
        elif len(tools) == len(valid_tools):
            return "*"  # Match all tools
        else:
            return "|".join(tools)


def validate_claude_settings_file(file_path: Path) -> tuple[bool, list[str]]:
    """
    Validate a Claude Code settings file.

    Args:
        file_path: Path to the settings.json file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not file_path.exists():
        return False, [f"Settings file not found: {file_path}"]

    try:
        with open(file_path) as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Error reading file: {e}"]

    validator = ClaudeSettingsValidator()
    return validator.validate_settings(settings)


# Convenience function for quick validation
def is_valid_claude_settings(settings: dict[str, Any]) -> bool:
    """Quick check if settings are valid."""
    validator = ClaudeSettingsValidator()
    is_valid, _ = validator.validate_settings(settings)
    return is_valid
