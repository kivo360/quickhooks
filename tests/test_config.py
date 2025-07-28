"""Tests for configuration schema using Pydantic Settings.

This module tests the configuration loading and validation using Pydantic Settings.
Following TDD principles - tests are written first.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from quickhooks.config import (
    QuickHooksConfig,
    DatabaseConfig,
    LoggingConfig,
    HookConfig,
    DevelopmentConfig,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig model."""

    def test_database_config_defaults(self):
        """Test DatabaseConfig with default values."""
        db_config = DatabaseConfig()
        
        assert db_config.url == "sqlite:///./quickhooks.db"
        assert db_config.echo is False
        assert db_config.pool_size == 5
        assert db_config.max_overflow == 10

    def test_database_config_from_env(self):
        """Test DatabaseConfig loading from environment variables."""
        with patch.dict(os.environ, {
            'QUICKHOOKS_DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'QUICKHOOKS_DATABASE_ECHO': 'true',
            'QUICKHOOKS_DATABASE_POOL_SIZE': '20',
            'QUICKHOOKS_DATABASE_MAX_OVERFLOW': '30'
        }):
            db_config = DatabaseConfig()
            
            assert db_config.url == 'postgresql://user:pass@localhost:5432/test_db'
            assert db_config.echo is True
            assert db_config.pool_size == 20
            assert db_config.max_overflow == 30

    def test_database_config_validation(self):
        """Test DatabaseConfig validation."""
        # Test invalid pool_size
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(pool_size=-1)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)

        # Test invalid max_overflow
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(max_overflow=-1)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        logging_config = LoggingConfig()
        
        assert logging_config.level == "INFO"
        assert logging_config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert logging_config.file_path is None
        assert logging_config.max_bytes == 10485760  # 10MB
        assert logging_config.backup_count == 5

    def test_logging_config_from_env(self):
        """Test LoggingConfig loading from environment variables."""
        with patch.dict(os.environ, {
            'QUICKHOOKS_LOGGING_LEVEL': 'DEBUG',
            'QUICKHOOKS_LOGGING_FORMAT': '%(levelname)s: %(message)s',
            'QUICKHOOKS_LOGGING_FILE_PATH': '/var/log/quickhooks.log',
            'QUICKHOOKS_LOGGING_MAX_BYTES': '5242880',  # 5MB
            'QUICKHOOKS_LOGGING_BACKUP_COUNT': '3'
        }):
            logging_config = LoggingConfig()
            
            assert logging_config.level == 'DEBUG'
            assert logging_config.format == '%(levelname)s: %(message)s'
            assert logging_config.file_path == '/var/log/quickhooks.log'
            assert logging_config.max_bytes == 5242880
            assert logging_config.backup_count == 3

    def test_logging_level_validation(self):
        """Test LoggingConfig level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Test invalid level
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(level="INVALID")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "enum" for error in errors)

    def test_logging_config_validation(self):
        """Test LoggingConfig validation constraints."""
        # Test invalid max_bytes
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(max_bytes=0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)

        # Test invalid backup_count
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(backup_count=-1)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)


class TestHookConfig:
    """Tests for HookConfig model."""

    def test_hook_config_defaults(self):
        """Test HookConfig with default values."""
        hook_config = HookConfig()
        
        assert hook_config.hooks_directory == "./hooks"
        assert hook_config.auto_discovery is True
        assert hook_config.default_timeout == 300.0
        assert hook_config.max_concurrent_hooks == 10
        assert hook_config.retry_attempts == 3
        assert hook_config.retry_delay == 1.0

    def test_hook_config_from_env(self):
        """Test HookConfig loading from environment variables."""
        with patch.dict(os.environ, {
            'QUICKHOOKS_HOOKS_DIRECTORY': '/custom/hooks/path',
            'QUICKHOOKS_AUTO_DISCOVERY': 'false',
            'QUICKHOOKS_DEFAULT_TIMEOUT': '600.0',
            'QUICKHOOKS_MAX_CONCURRENT_HOOKS': '20',
            'QUICKHOOKS_RETRY_ATTEMPTS': '5',
            'QUICKHOOKS_RETRY_DELAY': '2.5'
        }):
            hook_config = HookConfig()
            
            assert hook_config.hooks_directory == '/custom/hooks/path'
            assert hook_config.auto_discovery is False
            assert hook_config.default_timeout == 600.0
            assert hook_config.max_concurrent_hooks == 20
            assert hook_config.retry_attempts == 5
            assert hook_config.retry_delay == 2.5

    def test_hook_config_validation(self):
        """Test HookConfig validation constraints."""
        # Test invalid default_timeout
        with pytest.raises(ValidationError) as exc_info:
            HookConfig(default_timeout=0.0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)

        # Test invalid max_concurrent_hooks
        with pytest.raises(ValidationError) as exc_info:
            HookConfig(max_concurrent_hooks=0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)

        # Test invalid retry_attempts
        with pytest.raises(ValidationError) as exc_info:
            HookConfig(retry_attempts=-1)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)

        # Test invalid retry_delay
        with pytest.raises(ValidationError) as exc_info:
            HookConfig(retry_delay=-1.0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than_equal" for error in errors)


class TestDevelopmentConfig:
    """Tests for DevelopmentConfig model."""

    def test_development_config_defaults(self):
        """Test DevelopmentConfig with default values."""
        dev_config = DevelopmentConfig()
        
        assert dev_config.debug is False
        assert dev_config.hot_reload is True
        assert dev_config.watch_directories == ["./hooks", "./src"]
        assert dev_config.reload_delay == 1.0
        assert dev_config.enable_testing is True

    def test_development_config_from_env(self):
        """Test DevelopmentConfig loading from environment variables."""
        with patch.dict(os.environ, {
            'QUICKHOOKS_DEBUG': 'true',
            'QUICKHOOKS_HOT_RELOAD': 'false',
            'QUICKHOOKS_WATCH_DIRECTORIES': '["./custom", "./paths"]',
            'QUICKHOOKS_RELOAD_DELAY': '0.5',
            'QUICKHOOKS_ENABLE_TESTING': 'false'
        }):
            dev_config = DevelopmentConfig()
            
            assert dev_config.debug is True
            assert dev_config.hot_reload is False
            assert dev_config.watch_directories == ["./custom", "./paths"]
            assert dev_config.reload_delay == 0.5
            assert dev_config.enable_testing is False

    def test_development_config_validation(self):
        """Test DevelopmentConfig validation constraints."""
        # Test invalid reload_delay
        with pytest.raises(ValidationError) as exc_info:
            DevelopmentConfig(reload_delay=0.0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)


class TestQuickHooksConfig:
    """Tests for the main QuickHooksConfig settings."""

    def test_quickhooks_config_defaults(self):
        """Test QuickHooksConfig with default values."""
        config = QuickHooksConfig()
        
        assert config.app_name == "QuickHooks"
        assert config.version == "0.1.0"
        assert config.environment == "development"
        assert config.secret_key is not None
        assert len(config.secret_key) >= 32
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.hooks, HookConfig)
        assert isinstance(config.development, DevelopmentConfig)

    def test_quickhooks_config_from_env(self):
        """Test QuickHooksConfig loading from environment variables."""
        with patch.dict(os.environ, {
            'QUICKHOOKS_APP_NAME': 'CustomHooks',
            'QUICKHOOKS_VERSION': '1.0.0',
            'QUICKHOOKS_ENVIRONMENT': 'production',
            'QUICKHOOKS_SECRET_KEY': 'custom-secret-key-for-testing-12345678',
            'QUICKHOOKS_DATABASE_URL': 'postgresql://user:pass@localhost:5432/prod_db',
            'QUICKHOOKS_LOGGING_LEVEL': 'WARNING',
            'QUICKHOOKS_HOOKS_DIRECTORY': '/prod/hooks',
            'QUICKHOOKS_DEBUG': 'false'
        }):
            config = QuickHooksConfig()
            
            assert config.app_name == 'CustomHooks'
            assert config.version == '1.0.0'
            assert config.environment == 'production'
            assert config.secret_key == 'custom-secret-key-for-testing-12345678'
            assert config.database.url == 'postgresql://user:pass@localhost:5432/prod_db'
            assert config.logging.level == 'WARNING'
            assert config.hooks.hooks_directory == '/prod/hooks'
            assert config.development.debug is False

    def test_quickhooks_config_environment_validation(self):
        """Test QuickHooksConfig environment validation."""
        valid_environments = ["development", "testing", "staging", "production"]
        
        for env in valid_environments:
            with patch.dict(os.environ, {'QUICKHOOKS_ENVIRONMENT': env}):
                config = QuickHooksConfig()
                assert config.environment == env

        # Test invalid environment
        with patch.dict(os.environ, {'QUICKHOOKS_ENVIRONMENT': 'invalid'}):
            with pytest.raises(ValidationError) as exc_info:
                QuickHooksConfig()
            
            errors = exc_info.value.errors()
            assert any(error["type"] == "enum" for error in errors)

    def test_quickhooks_config_secret_key_validation(self):
        """Test QuickHooksConfig secret key validation."""
        # Test short secret key
        with patch.dict(os.environ, {'QUICKHOOKS_SECRET_KEY': 'short'}):
            with pytest.raises(ValidationError) as exc_info:
                QuickHooksConfig()
            
            errors = exc_info.value.errors()
            assert any(error["type"] == "string_too_short" for error in errors)

    def test_quickhooks_config_nested_validation(self):
        """Test that nested config validation works properly."""
        # Test invalid nested database config
        with patch.dict(os.environ, {'QUICKHOOKS_DATABASE_POOL_SIZE': '-1'}):
            with pytest.raises(ValidationError) as exc_info:
                QuickHooksConfig()
            
            errors = exc_info.value.errors()
            # Should have an error for the nested database pool_size field
            assert any("database" in error.get("loc", []) for error in errors)

    def test_config_model_dump(self):
        """Test configuration serialization."""
        config = QuickHooksConfig()
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert "app_name" in config_dict
        assert "database" in config_dict
        assert "logging" in config_dict
        assert "hooks" in config_dict
        assert "development" in config_dict
        
        # Check nested structure
        assert isinstance(config_dict["database"], dict)
        assert "url" in config_dict["database"]

    def test_config_json_serialization(self):
        """Test configuration JSON serialization."""
        config = QuickHooksConfig()
        json_str = config.model_dump_json()
        
        assert isinstance(json_str, str)
        
        # Should be able to recreate from JSON
        recreated = QuickHooksConfig.model_validate_json(json_str)
        assert recreated.app_name == config.app_name
        assert recreated.database.url == config.database.url


class TestConfigurationFile:
    """Tests for loading configuration from files."""

    def test_config_from_env_file(self):
        """Test loading configuration from .env file."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("QUICKHOOKS_APP_NAME=FileConfig\n")
            f.write("QUICKHOOKS_LOGGING_LEVEL=DEBUG\n")
            f.write("QUICKHOOKS_DATABASE_URL=sqlite:///./test_from_file.db\n")
            env_file_path = f.name

        try:
            # Load config with the env file
            config = QuickHooksConfig(_env_file=env_file_path)
            
            assert config.app_name == "FileConfig"
            assert config.logging.level == "DEBUG"
            assert config.database.url == "sqlite:///./test_from_file.db"
            
        finally:
            # Clean up
            Path(env_file_path).unlink()

    def test_config_priority_env_over_file(self):
        """Test that environment variables take priority over file settings."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("QUICKHOOKS_APP_NAME=FileConfig\n")
            f.write("QUICKHOOKS_LOGGING_LEVEL=DEBUG\n")
            env_file_path = f.name

        try:
            # Set environment variable that conflicts with file
            with patch.dict(os.environ, {'QUICKHOOKS_APP_NAME': 'EnvConfig'}):
                config = QuickHooksConfig(_env_file=env_file_path)
                
                # Environment should take priority
                assert config.app_name == "EnvConfig"
                # File setting should still be used where no env var exists
                assert config.logging.level == "DEBUG"
                
        finally:
            # Clean up
            Path(env_file_path).unlink()


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_config_with_real_environment(self):
        """Test configuration with realistic environment setup."""
        env_vars = {
            'QUICKHOOKS_ENVIRONMENT': 'production',
            'QUICKHOOKS_DATABASE_URL': 'postgresql://quickhooks:password@db:5432/quickhooks_prod',
            'QUICKHOOKS_LOGGING_LEVEL': 'WARNING',
            'QUICKHOOKS_LOGGING_FILE_PATH': '/var/log/quickhooks/app.log',
            'QUICKHOOKS_HOOKS_DIRECTORY': '/app/hooks',
            'QUICKHOOKS_AUTO_DISCOVERY': 'true',
            'QUICKHOOKS_MAX_CONCURRENT_HOOKS': '50',
            'QUICKHOOKS_DEBUG': 'false',
            'QUICKHOOKS_HOT_RELOAD': 'false',
            'QUICKHOOKS_SECRET_KEY': 'super-secret-production-key-32-chars-min'
        }
        
        with patch.dict(os.environ, env_vars):
            config = QuickHooksConfig()
            
            # Verify production configuration
            assert config.environment == 'production'
            assert config.database.url.startswith('postgresql://')
            assert config.logging.level == 'WARNING'
            assert config.logging.file_path == '/var/log/quickhooks/app.log'
            assert config.hooks.hooks_directory == '/app/hooks'
            assert config.hooks.auto_discovery is True
            assert config.hooks.max_concurrent_hooks == 50
            assert config.development.debug is False
            assert config.development.hot_reload is False

    def test_config_development_mode(self):
        """Test configuration optimized for development."""
        env_vars = {
            'QUICKHOOKS_ENVIRONMENT': 'development',
            'QUICKHOOKS_DEBUG': 'true',
            'QUICKHOOKS_LOGGING_LEVEL': 'DEBUG',
            'QUICKHOOKS_HOT_RELOAD': 'true',
            'QUICKHOOKS_WATCH_DIRECTORIES': '["./hooks", "./src", "./tests"]',
            'QUICKHOOKS_RELOAD_DELAY': '0.5'
        }
        
        with patch.dict(os.environ, env_vars):
            config = QuickHooksConfig()
            
            # Verify development configuration
            assert config.environment == 'development'
            assert config.development.debug is True
            assert config.logging.level == 'DEBUG'
            assert config.development.hot_reload is True
            assert "./tests" in config.development.watch_directories
            assert config.development.reload_delay == 0.5

    def test_config_validation_comprehensive(self):
        """Test comprehensive configuration validation."""
        # This should create a valid configuration with all constraints satisfied
        config = QuickHooksConfig()
        
        # Verify all constraints are met
        assert len(config.secret_key) >= 32
        assert config.database.pool_size > 0
        assert config.database.max_overflow >= 0
        assert config.logging.max_bytes > 0
        assert config.logging.backup_count >= 0
        assert config.hooks.default_timeout > 0
        assert config.hooks.max_concurrent_hooks > 0
        assert config.hooks.retry_attempts >= 0
        assert config.hooks.retry_delay >= 0
        assert config.development.reload_delay > 0
        
        # Verify enum validations
        assert config.environment in ["development", "testing", "staging", "production"]
        assert config.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]