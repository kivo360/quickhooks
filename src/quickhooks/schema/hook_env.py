"""Environment variable management for Claude Code hooks using Pydantic Settings.

This module provides Pydantic Settings models for all environment variables
that Claude Code injects into hook execution environments. All fields are
optional/nullable since different hook types receive different variables.

Usage:
    from quickhooks.schema.hook_env import ClaudeCodeHookEnv

    # Load environment variables
    env = ClaudeCodeHookEnv()

    # Access variables with proper typing
    if env.claude_env_file:
        print(f"Environment file: {env.claude_env_file}")
"""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClaudeCodeHookEnv(BaseSettings):
    """Environment variables available in Claude Code hooks.

    All fields are optional since different hook types receive different
    environment variables. Use this model to safely access environment
    variables with proper typing and validation.

    Environment Variables by Hook Type:

    SessionStart (only):
        - claude_env_file: File path to persist env vars for the session

    All Hooks:
        - GROQ_API_KEY: API key for Groq (if using agent analysis)
        - QUICKHOOKS_*: Custom QuickHooks configuration variables
        - Any custom variables set in .claude/settings.json env section

    Example:
        >>> env = ClaudeCodeHookEnv()
        >>> if env.is_session_start:
        >>>     print(f"Session start with env file: {env.claude_env_file}")
    """

    model_config = SettingsConfigDict(
        # Don't fail if variables are missing
        extra="allow",
        # Case-insensitive environment variable names
        case_sensitive=False,
        # Don't validate assignment (performance)
        validate_assignment=False,
        # Allow arbitrary types
        arbitrary_types_allowed=True,
    )

    # Claude Code specific environment variables
    claude_env_file: Path | None = Field(
        default=None,
        description="Path to environment file (SessionStart hooks only)",
        validation_alias="CLAUDE_ENV_FILE",
    )

    # QuickHooks configuration variables
    quickhooks_agent_analysis_enabled: bool | None = Field(
        default=None,
        description="Enable agent analysis feature",
        validation_alias="QUICKHOOKS_AGENT_ANALYSIS_ENABLED",
    )

    quickhooks_agent_model: str | None = Field(
        default=None,
        description="Groq model for agent analysis",
        validation_alias="QUICKHOOKS_AGENT_MODEL",
    )

    quickhooks_confidence_threshold: float | None = Field(
        default=None,
        description="Confidence threshold for agent recommendations",
        validation_alias="QUICKHOOKS_CONFIDENCE_THRESHOLD",
    )

    quickhooks_min_similarity: float | None = Field(
        default=None,
        description="Minimum similarity for agent discovery",
        validation_alias="QUICKHOOKS_MIN_SIMILARITY",
    )

    quickhooks_verbose: bool | None = Field(
        default=None,
        description="Enable verbose logging",
        validation_alias="QUICKHOOKS_VERBOSE",
    )

    # API keys
    groq_api_key: str | None = Field(
        default=None,
        description="Groq API key for agent analysis",
        validation_alias="GROQ_API_KEY",
    )

    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
        validation_alias="ANTHROPIC_API_KEY",
    )

    # Common environment variables
    home: Path | None = Field(
        default=None,
        description="User home directory",
        validation_alias="HOME",
    )

    path: str | None = Field(
        default=None,
        description="System PATH variable",
        validation_alias="PATH",
    )

    shell: str | None = Field(
        default=None,
        description="Current shell",
        validation_alias="SHELL",
    )

    user: str | None = Field(
        default=None,
        description="Current user",
        validation_alias="USER",
    )

    @field_validator("claude_env_file", mode="before")
    @classmethod
    def validate_claude_env_file(cls, v: str | Path | None) -> Path | None:
        """Convert string path to Path object."""
        if v is None or v == "":
            return None
        return Path(v) if isinstance(v, str) else v

    @field_validator("home", mode="before")
    @classmethod
    def validate_home(cls, v: str | Path | None) -> Path | None:
        """Convert string path to Path object."""
        if v is None or v == "":
            return None
        return Path(v) if isinstance(v, str) else v

    @property
    def is_session_start(self) -> bool:
        """Check if this is a SessionStart hook (has CLAUDE_ENV_FILE)."""
        return self.claude_env_file is not None

    @property
    def has_groq_api_key(self) -> bool:
        """Check if Groq API key is available."""
        return self.groq_api_key is not None and len(self.groq_api_key) > 0

    @property
    def agent_analysis_enabled(self) -> bool:
        """Check if agent analysis is enabled."""
        if self.quickhooks_agent_analysis_enabled is None:
            return True  # Default to enabled
        return self.quickhooks_agent_analysis_enabled

    def get_agent_model(self) -> str:
        """Get the agent model to use, with default."""
        return self.quickhooks_agent_model or "qwen/qwen3-32b"

    def get_confidence_threshold(self) -> float:
        """Get the confidence threshold, with default."""
        return self.quickhooks_confidence_threshold or 0.7

    def get_min_similarity(self) -> float:
        """Get the minimum similarity, with default."""
        return self.quickhooks_min_similarity or 0.3

    def is_verbose(self) -> bool:
        """Check if verbose logging is enabled."""
        return self.quickhooks_verbose or False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    def write_env_file(self, exports: dict[str, str]) -> bool:
        """
        Write environment variables to CLAUDE_ENV_FILE.

        Only works in SessionStart hooks where CLAUDE_ENV_FILE is available.

        Args:
            exports: Dictionary of environment variables to export

        Returns:
            True if successful, False if CLAUDE_ENV_FILE not available

        Example:
            >>> env = ClaudeCodeHookEnv()
            >>> env.write_env_file({
            ...     "NODE_ENV": "production",
            ...     "API_KEY": "secret123"
            ... })
        """
        if not self.claude_env_file:
            return False

        try:
            with open(self.claude_env_file, "a") as f:
                for key, value in exports.items():
                    # Properly escape values with quotes
                    escaped_value = value.replace('"', '\\"')
                    f.write(f'export {key}="{escaped_value}"\n')
            return True
        except Exception:
            return False

    def read_env_file(self) -> dict[str, str]:
        """
        Read environment variables from CLAUDE_ENV_FILE.

        Only works in SessionStart hooks where CLAUDE_ENV_FILE is available.

        Returns:
            Dictionary of environment variables

        Example:
            >>> env = ClaudeCodeHookEnv()
            >>> vars = env.read_env_file()
        """
        if not self.claude_env_file or not self.claude_env_file.exists():
            return {}

        env_vars = {}
        try:
            with open(self.claude_env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        # Parse: export KEY="value" or export KEY=value
                        parts = line[7:].split("=", 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"').strip("'")
                            env_vars[key] = value
        except Exception:
            pass

        return env_vars


class QuickHooksSettings(BaseSettings):
    """QuickHooks-specific settings separate from Claude Code env vars.

    Use this for application configuration that's independent of
    hook execution environment.
    """

    model_config = SettingsConfigDict(
        env_prefix="QUICKHOOKS_",
        case_sensitive=False,
        extra="allow",
    )

    # Agent Analysis settings
    agent_analysis_enabled: bool = Field(
        default=True,
        description="Enable agent analysis feature",
    )

    agent_model: str = Field(
        default="qwen/qwen3-32b",
        description="Groq model for agent analysis",
    )

    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for agent recommendations",
    )

    min_similarity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for agent discovery",
    )

    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )

    # Paths
    hooks_directory: Path = Field(
        default_factory=lambda: Path.home() / ".quickhooks" / "hooks",
        description="Directory containing hook scripts",
    )

    sessions_directory: Path = Field(
        default_factory=lambda: Path.home() / ".quickhooks" / "sessions",
        description="Directory for session metadata",
    )

    agent_db_path: Path = Field(
        default_factory=lambda: Path.home() / ".quickhooks" / "agent_db",
        description="Path to agent discovery database",
    )


def load_hook_env() -> ClaudeCodeHookEnv:
    """
    Load Claude Code hook environment variables.

    Returns:
        ClaudeCodeHookEnv instance with all available environment variables

    Example:
        >>> env = load_hook_env()
        >>> if env.is_session_start:
        >>>     env.write_env_file({"MY_VAR": "value"})
    """
    return ClaudeCodeHookEnv()


def load_quickhooks_settings() -> QuickHooksSettings:
    """
    Load QuickHooks application settings.

    Returns:
        QuickHooksSettings instance with configuration

    Example:
        >>> settings = load_quickhooks_settings()
        >>> print(f"Agent model: {settings.agent_model}")
    """
    return QuickHooksSettings()
