"""
Configuration management system - Clean TDD implementation
"""
import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging


class ConfigError(Exception):
    """Configuration error."""
    pass


class ConfigValidator:
    """Configuration validator."""
    
    REQUIRED_FIELDS = [
        "DISCORD_TOKEN",
        "DISCORD_GUILD_ID", 
        "DATABASE_URL"
    ]
    
    VALID_ENVIRONMENTS = ["development", "staging", "production", "test"]
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def validate(self, config: Dict[str, Any]) -> None:
        """Validate configuration dictionary."""
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if not config.get(field):
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate specific fields
        if config.get("ENVIRONMENT"):
            if config["ENVIRONMENT"] not in self.VALID_ENVIRONMENTS:
                errors.append(
                    f"ENVIRONMENT must be one of {self.VALID_ENVIRONMENTS}, "
                    f"got '{config['ENVIRONMENT']}'"
                )
        
        if config.get("DISCORD_GUILD_ID"):
            try:
                int(config["DISCORD_GUILD_ID"])
            except (ValueError, TypeError):
                errors.append("DISCORD_GUILD_ID must be a valid integer")
        
        if config.get("LOG_LEVEL"):
            if config["LOG_LEVEL"] not in self.VALID_LOG_LEVELS:
                errors.append(
                    f"LOG_LEVEL must be one of {self.VALID_LOG_LEVELS}, "
                    f"got '{config['LOG_LEVEL']}'"
                )
        
        if config.get("TIMEZONE"):
            if not self._is_valid_timezone(config["TIMEZONE"]):
                errors.append(f"Invalid TIMEZONE format: '{config['TIMEZONE']}'")
        
        if config.get("DAILY_REPORT_TIME"):
            if not self._is_valid_time_format(config["DAILY_REPORT_TIME"]):
                errors.append(f"Invalid DAILY_REPORT_TIME format: '{config['DAILY_REPORT_TIME']}'")
        
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def _is_valid_timezone(self, timezone: str) -> bool:
        """Check if timezone format is valid."""
        # Basic timezone format check (e.g., "Asia/Tokyo")
        return "/" in timezone and len(timezone.split("/")) >= 2
    
    def _is_valid_time_format(self, time_str: str) -> bool:
        """Check if time format is valid (HH:MM)."""
        pattern = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
        return re.match(pattern, time_str) is not None


class Config:
    """Main configuration class."""
    
    def __init__(self, validate: bool = False):
        """Initialize configuration."""
        self._load_from_environment()
        self._validator = ConfigValidator()
        
        if validate:
            self.validate()
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Core Discord settings
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
        self.DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
        
        # Database settings
        self.DATABASE_URL = os.getenv("DATABASE_URL", ":memory:")
        
        # Application settings
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.TIMEZONE = os.getenv("TIMEZONE", "Asia/Tokyo")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.DAILY_REPORT_TIME = os.getenv("DAILY_REPORT_TIME", "17:00")
        
        # Optional Google API settings
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")
        
        # Server settings
        self.HEALTH_CHECK_PORT = int(os.getenv("HEALTH_CHECK_PORT", "8000"))
        self.MEETING_REMINDER_MINUTES = int(os.getenv("MEETING_REMINDER_MINUTES", "15"))
    
    @classmethod
    def from_env_file(cls, env_file: str) -> 'Config':
        """Load configuration from .env file."""
        env_vars = {}
        
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Temporarily set environment variables
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            config = cls()
        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
        
        return config
    
    def validate(self) -> None:
        """Validate current configuration."""
        config_dict = self.to_dict(include_sensitive=True)
        self._validator.validate(config_dict)
    
    def to_dict(self, include_sensitive: bool = True) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = {
            "DISCORD_TOKEN": self.DISCORD_TOKEN,
            "DISCORD_GUILD_ID": self.DISCORD_GUILD_ID,
            "DATABASE_URL": self.DATABASE_URL,
            "ENVIRONMENT": self.ENVIRONMENT,
            "TIMEZONE": self.TIMEZONE,
            "LOG_LEVEL": self.LOG_LEVEL,
            "DAILY_REPORT_TIME": self.DAILY_REPORT_TIME,
            "GOOGLE_CLIENT_ID": self.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": self.GOOGLE_CLIENT_SECRET,
            "GOOGLE_CALENDAR_ID": self.GOOGLE_CALENDAR_ID,
            "HEALTH_CHECK_PORT": self.HEALTH_CHECK_PORT,
            "MEETING_REMINDER_MINUTES": self.MEETING_REMINDER_MINUTES
        }
        
        if not include_sensitive:
            # Mask sensitive information
            sensitive_fields = ["DISCORD_TOKEN", "GOOGLE_CLIENT_SECRET"]
            for field in sensitive_fields:
                if config_dict[field]:
                    config_dict[field] = "***MASKED***"
            
            # Mask password in database URL
            if "password" in config_dict["DATABASE_URL"]:
                config_dict["DATABASE_URL"] = re.sub(
                    r"://([^:]+):([^@]+)@",
                    r"://\1:***@",
                    config_dict["DATABASE_URL"]
                )
        
        return config_dict
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration values at runtime."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def reload(self) -> None:
        """Reload configuration from environment."""
        self._load_from_environment()
    
    # Environment detection methods
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT == "test"
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == "staging"
    
    def get_database_type(self) -> str:
        """Get database type from DATABASE_URL."""
        if "postgresql" in self.DATABASE_URL.lower():
            return "postgresql"
        elif "sqlite" in self.DATABASE_URL.lower():
            return "sqlite" 
        elif self.DATABASE_URL.endswith('.db') or self.DATABASE_URL == ":memory:":
            return "sqlite"
        else:
            return "unknown"
    
    def has_google_api_config(self) -> bool:
        """Check if Google API is configured."""
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)
    
    # Validation helper methods
    def _validate_timezone(self, timezone: str) -> bool:
        """Validate timezone format."""
        return self._validator._is_valid_timezone(timezone)
    
    def _validate_environment(self, environment: str) -> bool:
        """Validate environment value."""
        return environment in self._validator.VALID_ENVIRONMENTS
    
    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time format."""
        return self._validator._is_valid_time_format(time_str)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information summary."""
        return {
            "environment": self.ENVIRONMENT,
            "database_type": self.get_database_type(),
            "timezone": self.TIMEZONE,
            "log_level": self.LOG_LEVEL,
            "google_api_configured": self.has_google_api_config(),
            "health_check_enabled": self.is_production(),
            "guild_id": self.DISCORD_GUILD_ID,
            "health_check_port": self.HEALTH_CHECK_PORT
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config


def load_config_from_env(env_file: str = ".env") -> Config:
    """Load and set global configuration from environment file."""
    global _config
    _config = Config.from_env_file(env_file)
    return _config