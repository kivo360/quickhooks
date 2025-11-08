"""Configuration schema for QuickHooks using Pydantic Settings.

This module defines the configuration structure for the QuickHooks framework
using Pydantic Settings for environment variable and file-based configuration.
"""

import os
import secrets
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Valid deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Valid logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """Database configuration settings.

    Configures database connection and pool settings for QuickHooks.
    """

    model_config = SettingsConfigDict(
        env_prefix="QUICKHOOKS_DATABASE_", case_sensitive=False
    )

    url: str = Field(
        default="sqlite:///./quickhooks.db", description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=5, gt=0, description="Size of the connection pool")
    max_overflow: int = Field(
        default=10,
        ge=0,
        description="Maximum number of connections that can overflow the pool",
    )


class LoggingConfig(BaseSettings):
    """Logging configuration settings.

    Configures logging level, format, and file rotation for QuickHooks.
    """

    model_config = SettingsConfigDict(
        env_prefix="QUICKHOOKS_LOGGING_", case_sensitive=False
    )

    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file_path: str | None = Field(
        default=None, description="Path to log file (if None, logs to stdout)"
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        gt=0,
        description="Maximum log file size in bytes before rotation",
    )
    backup_count: int = Field(
        default=5, ge=0, description="Number of backup log files to keep"
    )


class HookConfig(BaseSettings):
    """Hook execution configuration settings.

    Configures hook discovery, execution limits, and retry behavior.
    """

    model_config = SettingsConfigDict(env_prefix="QUICKHOOKS_", case_sensitive=False)

    hooks_directory: str = Field(
        default="./hooks", description="Directory containing hook implementations"
    )
    auto_discovery: bool = Field(
        default=True, description="Automatically discover hooks in the hooks directory"
    )
    default_timeout: float = Field(
        default=300.0,  # 5 minutes
        gt=0.0,
        description="Default timeout for hook execution in seconds",
    )
    max_concurrent_hooks: int = Field(
        default=10,
        gt=0,
        description="Maximum number of hooks that can execute concurrently",
    )
    retry_attempts: int = Field(
        default=3, ge=0, description="Number of retry attempts for failed hooks"
    )
    retry_delay: float = Field(
        default=1.0, ge=0.0, description="Delay between retry attempts in seconds"
    )


class DevelopmentConfig(BaseSettings):
    """Development and debugging configuration settings.

    Configures development features like hot reload, debugging, and testing.
    """

    model_config = SettingsConfigDict(env_prefix="QUICKHOOKS_", case_sensitive=False)

    debug: bool = Field(default=False, description="Enable debug mode")
    hot_reload: bool = Field(
        default=True, description="Enable hot reload during development"
    )
    watch_directories: list[str] = Field(
        default_factory=lambda: ["./hooks", "./src"],
        description="Directories to watch for changes during development",
    )
    reload_delay: float = Field(
        default=1.0,
        gt=0.0,
        description="Delay before reloading after file changes in seconds",
    )
    enable_testing: bool = Field(
        default=True, description="Enable testing features and endpoints"
    )


class AIConfig(BaseSettings):
    """AI and agent configuration settings.

    Configures AI provider, models, and agent behavior for QuickHooks.
    """

    model_config = SettingsConfigDict(
        env_prefix="FIREWORKS_", case_sensitive=False
    )

    api_key: str | None = Field(
        default=None, description="Fireworks AI API key"
    )
    llm: str = Field(
        default="accounts/fireworks/models/glm-4p6",
        description="Fireworks LLM model for text generation and tool calls",
    )
    vlm: str = Field(
        default="accounts/fireworks/models/qwen3-vl-235b-a22b-instruct",
        description="Fireworks VLM model for vision tasks",
    )
    base_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        description="Fireworks API base URL",
    )
    enable_tool_calls: bool = Field(
        default=True, description="Enable tool calls by default for structured outputs"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for model responses"
    )
    max_retries: int = Field(
        default=3, ge=0, description="Maximum retries for failed API calls"
    )


class QuickHooksConfig(BaseSettings):
    """Main configuration class for QuickHooks framework.

    This class aggregates all configuration sections and handles loading
    from environment variables and configuration files.
    """

    model_config = SettingsConfigDict(
        env_prefix="QUICKHOOKS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="QuickHooks", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Deployment environment"
    )
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        min_length=32,
        description="Secret key for cryptographic operations",
    )

    # Configuration sections
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    hooks: HookConfig = Field(
        default_factory=HookConfig, description="Hook execution configuration"
    )
    development: DevelopmentConfig = Field(
        default_factory=DevelopmentConfig,
        description="Development and debugging configuration",
    )
    ai: AIConfig = Field(
        default_factory=AIConfig, description="AI and agent configuration"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key meets security requirements."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.database.url

    def get_log_level(self) -> str:
        """Get the logging level as a string."""
        return self.logging.level.value

    def get_hooks_directory(self) -> str:
        """Get the hooks directory path."""
        return self.hooks.hooks_directory

    def should_enable_debug(self) -> bool:
        """Determine if debug mode should be enabled."""
        return self.development.debug or self.is_development

    def should_enable_hot_reload(self) -> bool:
        """Determine if hot reload should be enabled."""
        return self.development.hot_reload and not self.is_production

    def get_watch_directories(self) -> list[str]:
        """Get directories to watch for changes."""
        return self.development.watch_directories.copy()

    def model_post_init(self, __context) -> None:
        """Post-initialization hook for additional validation."""
        # Ensure hot reload is disabled in production
        if self.is_production and self.development.hot_reload:
            self.development.hot_reload = False

        # Ensure debug is disabled in production unless explicitly set
        if self.is_production and not hasattr(self, "_debug_explicitly_set"):
            self.development.debug = False


# Global configuration instance
_config: QuickHooksConfig | None = None


def get_config() -> QuickHooksConfig:
    """Get the global configuration instance.

    Returns:
        QuickHooksConfig: The global configuration instance
    """
    global _config
    if _config is None:
        _config = QuickHooksConfig()
    return _config


def set_config(config: QuickHooksConfig) -> None:
    """Set the global configuration instance.

    Args:
        config: The configuration instance to set globally
    """
    global _config
    _config = config


def reload_config() -> QuickHooksConfig:
    """Reload the global configuration from environment and files.

    Returns:
        QuickHooksConfig: The newly loaded configuration instance
    """
    global _config
    _config = QuickHooksConfig()
    return _config


def get_global_hooks_dir() -> Path:
    """Get the global hooks directory path.
    
    Returns:
        Path: Path to the global hooks directory
    """
    # Check environment variable first
    env_dir = os.getenv("QUICKHOOKS_GLOBAL_DIR")
    if env_dir:
        return Path(env_dir)
    
    # Default to user's home directory
    home_dir = Path.home()
    return home_dir / ".quickhooks" / "hooks"


def get_global_config_dir() -> Path:
    """Get the global configuration directory path.
    
    Returns:
        Path: Path to the global configuration directory
    """
    # Check environment variable first
    env_dir = os.getenv("QUICKHOOKS_GLOBAL_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    
    # Default to user's home directory
    home_dir = Path.home()
    return home_dir / ".quickhooks" / "config"
