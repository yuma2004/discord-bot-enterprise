"""
Test logging system - TDD approach
"""
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.core.logging import LoggerManager, StructuredFormatter, get_logger


class TestStructuredFormatter:
    """Test structured log formatter."""
    
    def test_formatter_formats_basic_message(self):
        """Test formatter formats basic log message."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "INFO" in formatted
        assert "test_logger" in formatted
    
    def test_formatter_includes_timestamp(self):
        """Test formatter includes timestamp."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py", 
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        # Should include timestamp in ISO format
        assert len(formatted.split("|")) >= 4  # timestamp|level|name|message
    
    def test_formatter_handles_extra_fields(self):
        """Test formatter handles extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.user_id = 123456
        record.command = "test_command"
        
        formatted = formatter.format(record)
        assert "user_id=123456" in formatted
        assert "command=test_command" in formatted
    
    def test_formatter_handles_exceptions(self):
        """Test formatter handles exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=True
            )
        
        formatted = formatter.format(record)
        assert "Error occurred" in formatted
        assert "ValueError" in formatted
        assert "Test exception" in formatted


class TestLoggerManager:
    """Test logger manager."""
    
    def test_manager_creates_logger(self):
        """Test manager creates logger instances."""
        manager = LoggerManager()
        logger = manager.get_logger("test_logger")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
    
    def test_manager_configures_logger_level(self):
        """Test manager configures logger level."""
        manager = LoggerManager(log_level="DEBUG")
        logger = manager.get_logger("test_logger")
        
        assert logger.level == logging.DEBUG
    
    def test_manager_adds_console_handler(self):
        """Test manager adds console handler."""
        manager = LoggerManager()
        logger = manager.get_logger("test_logger")
        
        # Should have at least one handler
        assert len(logger.handlers) > 0
        
        # Should have console handler
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0
    
    def test_manager_adds_file_handler(self):
        """Test manager adds file handler when log file specified."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            manager = LoggerManager(log_file=temp_path)
            logger = manager.get_logger("test_logger")
            
            # Should have file handler
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_manager_prevents_duplicate_handlers(self):
        """Test manager prevents duplicate handlers."""
        manager = LoggerManager()
        
        # Get same logger multiple times
        logger1 = manager.get_logger("test_logger")
        logger2 = manager.get_logger("test_logger")
        
        assert logger1 is logger2
        # Should not have duplicate handlers
        handler_count = len(logger1.handlers)
        
        # Getting logger again shouldn't add more handlers
        logger3 = manager.get_logger("test_logger")
        assert len(logger3.handlers) == handler_count
    
    def test_manager_uses_structured_formatter(self):
        """Test manager uses structured formatter."""
        manager = LoggerManager()
        logger = manager.get_logger("test_logger")
        
        # Check that handlers use StructuredFormatter
        for handler in logger.handlers:
            assert isinstance(handler.formatter, StructuredFormatter)
    
    def test_manager_handles_invalid_log_level(self):
        """Test manager handles invalid log level."""
        manager = LoggerManager(log_level="INVALID")
        logger = manager.get_logger("test_logger")
        
        # Should default to INFO level
        assert logger.level == logging.INFO
    
    def test_manager_configures_from_config(self):
        """Test manager configures from config object."""
        mock_config = MagicMock()
        mock_config.LOG_LEVEL = "WARNING"
        mock_config.ENVIRONMENT = "production"
        
        manager = LoggerManager.from_config(mock_config)
        logger = manager.get_logger("test_logger")
        
        assert logger.level == logging.WARNING


class TestGlobalLoggerFunction:
    """Test global logger function."""
    
    def test_get_logger_returns_configured_logger(self):
        """Test get_logger returns properly configured logger."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert len(logger.handlers) > 0
    
    def test_get_logger_with_context(self):
        """Test get_logger with context information."""
        logger = get_logger("test_module", user_id=123456, guild_id=789012)
        
        # Logger should have context information
        assert hasattr(logger, 'user_id')
        assert hasattr(logger, 'guild_id')
        assert logger.user_id == 123456
        assert logger.guild_id == 789012
    
    def test_get_logger_caches_instances(self):
        """Test get_logger caches logger instances."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2


class TestLoggingIntegration:
    """Test logging system integration."""
    
    def test_logging_to_file(self):
        """Test logging messages to file."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".log", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            manager = LoggerManager(log_file=temp_path)
            logger = manager.get_logger("test_logger")
            
            # Log some messages
            logger.info("Test info message")
            logger.warning("Test warning message") 
            logger.error("Test error message")
            
            # Force flush
            for handler in logger.handlers:
                handler.flush()
            
            # Check file contents
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "Test info message" in content
                assert "Test warning message" in content
                assert "Test error message" in content
                assert "INFO" in content
                assert "WARNING" in content
                assert "ERROR" in content
                
        finally:
            os.unlink(temp_path)
    
    def test_logging_with_context(self):
        """Test logging with context information."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".log", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            manager = LoggerManager(log_file=temp_path)
            logger = manager.get_logger("test_logger")
            
            # Log with extra context
            logger.info("User action", extra={
                "user_id": 123456,
                "action": "login",
                "guild_id": 789012
            })
            
            # Force flush
            for handler in logger.handlers:
                handler.flush()
            
            # Check context in log
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "user_id=123456" in content
                assert "action=login" in content
                assert "guild_id=789012" in content
                
        finally:
            os.unlink(temp_path)
    
    def test_logging_different_levels(self):
        """Test logging at different levels."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".log", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Set to WARNING level
            manager = LoggerManager(log_level="WARNING", log_file=temp_path)
            logger = manager.get_logger("test_logger")
            
            # Log at different levels
            logger.debug("Debug message")  # Should not appear
            logger.info("Info message")    # Should not appear
            logger.warning("Warning message")  # Should appear
            logger.error("Error message")      # Should appear
            
            # Force flush
            for handler in logger.handlers:
                handler.flush()
            
            # Check only WARNING and ERROR appear
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "Debug message" not in content
                assert "Info message" not in content
                assert "Warning message" in content
                assert "Error message" in content
                
        finally:
            os.unlink(temp_path)
    
    def test_logging_performance(self):
        """Test logging performance with many messages."""
        manager = LoggerManager()
        logger = manager.get_logger("perf_test")
        
        # Should handle many log messages efficiently
        import time
        start_time = time.time()
        
        for i in range(1000):
            logger.info(f"Performance test message {i}", extra={"iteration": i})
        
        elapsed = time.time() - start_time
        # Should complete quickly (less than 1 second for 1000 messages)
        assert elapsed < 1.0