"""
Structured logging system - Clean TDD implementation
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json


class StructuredFormatter(logging.Formatter):
    """Structured log formatter with consistent format."""
    
    def __init__(self, include_extra: bool = True):
        """Initialize formatter."""
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured output."""
        # Basic log components
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        
        # Build base log line
        log_parts = [timestamp, level, logger_name, message]
        
        # Add extra fields if available and enabled
        if self.include_extra:
            extra_fields = self._get_extra_fields(record)
            if extra_fields:
                extra_str = " ".join(f"{k}={v}" for k, v in extra_fields.items())
                log_parts.append(extra_str)
        
        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_parts.append(f"exception={exc_text}")
        
        return " | ".join(log_parts)
    
    def _get_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from log record."""
        # Standard fields to exclude
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'message', 'exc_info',
            'exc_text', 'stack_info'
        }
        
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                # Convert value to string, handling special types
                if isinstance(value, (dict, list)):
                    extra_fields[key] = json.dumps(value)
                else:
                    extra_fields[key] = str(value)
        
        return extra_fields


class LoggerManager:
    """Manager for creating and configuring loggers."""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None, include_extra: bool = True):
        """Initialize logger manager."""
        self.log_level = self._parse_log_level(log_level)
        self.log_file = log_file
        self.include_extra = include_extra
        self.formatter = StructuredFormatter(include_extra=include_extra)
        self._configured_loggers = set()
    
    def _parse_log_level(self, level: str) -> int:
        """Parse log level string to logging constant."""
        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_mapping.get(level.upper(), logging.INFO)
    
    def get_logger(self, name: str, **context) -> logging.Logger:
        """Get or create a configured logger."""
        logger = logging.getLogger(name)
        
        # Only configure each logger once
        if name not in self._configured_loggers:
            self._configure_logger(logger)
            self._configured_loggers.add(name)
        
        # Add context attributes to logger
        for key, value in context.items():
            setattr(logger, key, value)
        
        return logger
    
    def _configure_logger(self, logger: logging.Logger) -> None:
        """Configure logger with handlers and formatters."""
        logger.setLevel(self.log_level)
        
        # Remove existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(self.formatter)
        logger.addHandler(console_handler)
        
        # Add file handler if specified
        if self.log_file:
            try:
                # Ensure directory exists
                log_path = Path(self.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
                file_handler.setLevel(self.log_level)
                file_handler.setFormatter(self.formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # If file handler fails, log to console
                logger.warning(f"Could not create file handler for {self.log_file}: {e}")
        
        # Prevent propagation to root logger
        logger.propagate = False
    
    @classmethod
    def from_config(cls, config: Any) -> 'LoggerManager':
        """Create logger manager from configuration object."""
        log_level = getattr(config, 'LOG_LEVEL', 'INFO')
        log_file = None
        
        # Determine log file based on environment
        environment = getattr(config, 'ENVIRONMENT', 'development')
        if environment == 'production':
            log_file = 'logs/bot.log'
        elif environment == 'development':
            log_file = 'logs/bot-dev.log'
        
        return cls(log_level=log_level, log_file=log_file)


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None


def get_logger(name: str, **context) -> logging.Logger:
    """Get a configured logger instance."""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    
    return _logger_manager.get_logger(name, **context)


def set_logger_manager(manager: LoggerManager) -> None:
    """Set global logger manager."""
    global _logger_manager
    _logger_manager = manager


def configure_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure global logging system."""
    global _logger_manager
    _logger_manager = LoggerManager(log_level=log_level, log_file=log_file)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding consistent context."""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        """Initialize adapter with context."""
        super().__init__(logger, context)
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with context."""
        # Add context to extra fields
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_contextual_logger(name: str, **context) -> LoggerAdapter:
    """Get logger with persistent context."""
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


# Convenience functions for common logging patterns
def log_user_action(logger: logging.Logger, user_id: int, action: str, **details) -> None:
    """Log user action with consistent format."""
    logger.info(f"User action: {action}", extra={
        "user_id": user_id,
        "action": action,
        **details
    })


def log_command_execution(logger: logging.Logger, command: str, user_id: int, guild_id: int, success: bool = True, **details) -> None:
    """Log Discord command execution."""
    level = logging.INFO if success else logging.WARNING
    message = f"Command {'executed' if success else 'failed'}: {command}"
    
    logger.log(level, message, extra={
        "command": command,
        "user_id": user_id,
        "guild_id": guild_id,
        "success": success,
        **details
    })


def log_database_operation(logger: logging.Logger, operation: str, table: str, success: bool = True, **details) -> None:
    """Log database operation."""
    level = logging.INFO if success else logging.ERROR
    message = f"Database {operation} on {table} {'succeeded' if success else 'failed'}"
    
    logger.log(level, message, extra={
        "operation": operation,
        "table": table,
        "success": success,
        **details
    })


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any]) -> None:
    """Log error with full context."""
    logger.error(f"Error occurred: {type(error).__name__}: {error}", extra={
        "error_type": type(error).__name__,
        "error_message": str(error),
        **context
    }, exc_info=True)


# Performance logging utilities
class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", extra={
            "operation": self.operation,
            "phase": "start",
            **self.context
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation}", extra={
                "operation": self.operation,
                "phase": "complete",
                "duration_seconds": round(duration, 3),
                **self.context
            })
        else:
            self.logger.error(f"Failed {self.operation}", extra={
                "operation": self.operation,
                "phase": "error",
                "duration_seconds": round(duration, 3),
                "error_type": exc_type.__name__,
                **self.context
            })


def time_operation(logger: logging.Logger, operation: str, **context) -> PerformanceTimer:
    """Create performance timer for operation."""
    return PerformanceTimer(logger, operation, **context)