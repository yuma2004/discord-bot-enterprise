"""
Test configuration management system - TDD approach
"""
import os
import pytest
from unittest.mock import patch, mock_open
from typing import Dict, Any

from src.core.config import Config, ConfigError, ConfigValidator


class TestConfigValidator:
    """Test configuration validation."""
    
    def test_validator_validates_required_fields(self):
        """Test validator checks required configuration fields."""
        validator = ConfigValidator()
        
        # Missing required fields should raise error
        with pytest.raises(ConfigError) as exc_info:
            validator.validate({})
        
        assert "DISCORD_TOKEN" in str(exc_info.value)
    
    def test_validator_accepts_valid_config(self):
        """Test validator accepts valid configuration."""
        validator = ConfigValidator()
        
        valid_config = {
            "DISCORD_TOKEN": "test_token_123",
            "DISCORD_GUILD_ID": "123456789",
            "DATABASE_URL": "test.db",
            "ENVIRONMENT": "development"
        }
        
        # Should not raise exception
        validator.validate(valid_config)
    
    def test_validator_validates_environment_values(self):
        """Test validator checks valid environment values."""
        validator = ConfigValidator()
        
        config = {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_GUILD_ID": "123456789", 
            "DATABASE_URL": "test.db",
            "ENVIRONMENT": "invalid_env"
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validator.validate(config)
        
        assert "ENVIRONMENT" in str(exc_info.value)
        assert "invalid_env" in str(exc_info.value)
    
    def test_validator_validates_discord_guild_id(self):
        """Test validator checks Discord Guild ID format."""
        validator = ConfigValidator()
        
        config = {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_GUILD_ID": "invalid_id",
            "DATABASE_URL": "test.db", 
            "ENVIRONMENT": "development"
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validator.validate(config)
        
        assert "DISCORD_GUILD_ID" in str(exc_info.value)
    
    def test_validator_validates_timezone(self):
        """Test validator checks timezone format."""
        validator = ConfigValidator()
        
        config = {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_GUILD_ID": "123456789",
            "DATABASE_URL": "test.db",
            "ENVIRONMENT": "development",
            "TIMEZONE": "Invalid/Timezone"
        }
        
        with pytest.raises(ConfigError) as exc_info:
            validator.validate(config)
        
        assert "TIMEZONE" in str(exc_info.value)


class TestConfig:
    """Test main configuration class."""
    
    def test_config_loads_from_environment(self):
        """Test config loads values from environment variables."""
        env_vars = {
            "DISCORD_TOKEN": "env_token_123",
            "DISCORD_GUILD_ID": "987654321",
            "DATABASE_URL": "env_database.db",
            "ENVIRONMENT": "production"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            assert config.DISCORD_TOKEN == "env_token_123"
            assert config.DISCORD_GUILD_ID == 987654321
            assert config.DATABASE_URL == "env_database.db"
            assert config.ENVIRONMENT == "production"
    
    def test_config_uses_default_values(self):
        """Test config uses default values when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            
            assert config.ENVIRONMENT == "development"
            assert config.TIMEZONE == "Asia/Tokyo"
            assert config.LOG_LEVEL == "INFO"
            assert config.DAILY_REPORT_TIME == "17:00"
    
    def test_config_loads_from_env_file(self):
        """Test config can load from .env file."""
        env_content = """
DISCORD_TOKEN=file_token_456
DISCORD_GUILD_ID=111222333
DATABASE_URL=file_database.db
ENVIRONMENT=staging
"""
        
        with patch("builtins.open", mock_open(read_data=env_content)):
            with patch("os.path.exists", return_value=True):
                config = Config.from_env_file(".env")
                
                assert config.DISCORD_TOKEN == "file_token_456"
                assert config.DISCORD_GUILD_ID == 111222333
                assert config.DATABASE_URL == "file_database.db"
                assert config.ENVIRONMENT == "staging"
    
    def test_config_validation_on_init(self):
        """Test config validates on initialization."""
        # Missing required token should raise error
        with patch.dict(os.environ, {"DISCORD_TOKEN": ""}, clear=True):
            with pytest.raises(ConfigError):
                Config(validate=True)
    
    def test_config_environment_detection(self):
        """Test config environment detection methods."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = Config()
            assert config.is_development()
            assert not config.is_production()
            assert not config.is_testing()
        
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = Config()
            assert not config.is_development()
            assert config.is_production()
            assert not config.is_testing()
        
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            config = Config()
            assert not config.is_development()
            assert not config.is_production()
            assert config.is_testing()
    
    def test_config_database_type_detection(self):
        """Test config detects database type correctly."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            config = Config()
            assert config.get_database_type() == "sqlite"
        
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host/db"}):
            config = Config()
            assert config.get_database_type() == "postgresql"
        
        with patch.dict(os.environ, {"DATABASE_URL": "test.db"}):
            config = Config()
            assert config.get_database_type() == "sqlite"
    
    def test_config_to_dict(self):
        """Test config can be converted to dictionary."""
        env_vars = {
            "DISCORD_TOKEN": "test_token",
            "DISCORD_GUILD_ID": "123456789",
            "DATABASE_URL": "test.db",
            "ENVIRONMENT": "development"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            config_dict = config.to_dict()
            
            assert isinstance(config_dict, dict)
            assert "DISCORD_TOKEN" in config_dict
            assert "DISCORD_GUILD_ID" in config_dict
            assert "DATABASE_URL" in config_dict
            assert "ENVIRONMENT" in config_dict
    
    def test_config_to_dict_excludes_sensitive(self):
        """Test config dictionary excludes sensitive information."""
        env_vars = {
            "DISCORD_TOKEN": "secret_token_123",
            "DISCORD_GUILD_ID": "123456789",
            "DATABASE_URL": "postgresql://user:password@host/db",
            "ENVIRONMENT": "production"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            config_dict = config.to_dict(include_sensitive=False)
            
            # Sensitive fields should be masked
            assert config_dict["DISCORD_TOKEN"] == "***MASKED***"
            assert "password" not in config_dict["DATABASE_URL"]
    
    def test_config_update_values(self):
        """Test config can update values at runtime."""
        config = Config()
        original_log_level = config.LOG_LEVEL
        
        config.update({"LOG_LEVEL": "DEBUG"})
        assert config.LOG_LEVEL == "DEBUG"
        assert config.LOG_LEVEL != original_log_level
    
    def test_config_reload(self):
        """Test config can reload from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            config = Config()
            assert config.LOG_LEVEL == "INFO"
        
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            config.reload()
            assert config.LOG_LEVEL == "DEBUG"


class TestConfigIntegration:
    """Test configuration integration scenarios."""
    
    def test_config_with_complete_environment(self):
        """Test config with all environment variables set."""
        complete_env = {
            "DISCORD_TOKEN": "complete_token_123",
            "DISCORD_GUILD_ID": "123456789",
            "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
            "ENVIRONMENT": "production",
            "TIMEZONE": "Asia/Tokyo", 
            "LOG_LEVEL": "WARNING",
            "DAILY_REPORT_TIME": "18:00",
            "GOOGLE_CLIENT_ID": "google_client_id",
            "GOOGLE_CLIENT_SECRET": "google_secret"
        }
        
        with patch.dict(os.environ, complete_env):
            config = Config(validate=True)
            
            # All values should be loaded correctly
            assert config.DISCORD_TOKEN == "complete_token_123"
            assert config.DISCORD_GUILD_ID == 123456789
            assert config.ENVIRONMENT == "production"
            assert config.LOG_LEVEL == "WARNING"
            assert config.DAILY_REPORT_TIME == "18:00"
            assert config.is_production()
            assert config.get_database_type() == "postgresql"
    
    def test_config_error_reporting(self):
        """Test config provides clear error messages."""
        with patch.dict(os.environ, {}, clear=True):
            try:
                Config(validate=True)
                pytest.fail("Should have raised ConfigError")
            except ConfigError as e:
                error_msg = str(e)
                assert "DISCORD_TOKEN" in error_msg
                assert "required" in error_msg.lower()
    
    def test_config_partial_validation(self):
        """Test config can validate subset of fields."""
        config = Config(validate=False)
        
        # Should be able to validate individual aspects
        assert config._validate_timezone("Asia/Tokyo")
        assert not config._validate_timezone("Invalid/Timezone")
        
        assert config._validate_environment("development")
        assert not config._validate_environment("invalid_env")
        
        assert config._validate_time_format("17:00")
        assert not config._validate_time_format("25:00")