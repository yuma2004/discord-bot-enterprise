"""
Test error handling framework - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import Any, Dict

from src.core.error_handling import (
    BotError, UserError, SystemError, ConfigurationError,
    ErrorHandler, ErrorContext, ErrorRecovery, get_error_handler
)


class TestBotErrors:
    """Test custom bot exception classes."""
    
    def test_bot_error_base_class(self):
        """Test BotError base exception class."""
        error = BotError("Test error", error_code="TEST_001")
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"
        assert error.user_message is None
        assert error.context == {}
    
    def test_user_error_for_user_facing_messages(self):
        """Test UserError for user-facing error messages."""
        error = UserError(
            "User did something wrong",
            user_message="Please check your input and try again.",
            error_code="USER_001"
        )
        
        assert error.user_message == "Please check your input and try again."
        assert error.error_code == "USER_001"
        assert error.is_user_error()
    
    def test_system_error_for_internal_errors(self):
        """Test SystemError for internal system errors."""
        error = SystemError(
            "Database connection failed",
            error_code="SYS_001",
            context={"database_url": "test.db"}
        )
        
        assert error.error_code == "SYS_001"
        assert error.context["database_url"] == "test.db"
        assert not error.is_user_error()
    
    def test_configuration_error_for_config_issues(self):
        """Test ConfigurationError for configuration problems."""
        error = ConfigurationError(
            "Missing required configuration",
            error_code="CFG_001",
            config_field="DISCORD_TOKEN"
        )
        
        assert error.error_code == "CFG_001"
        assert error.config_field == "DISCORD_TOKEN"


class TestErrorContext:
    """Test error context management."""
    
    def test_error_context_captures_information(self):
        """Test error context captures relevant information."""
        context = ErrorContext(
            user_id=123456,
            guild_id=789012,
            command="test_command",
            channel_id=456789
        )
        
        assert context.user_id == 123456
        assert context.guild_id == 789012
        assert context.command == "test_command"
        assert context.channel_id == 456789
    
    def test_error_context_to_dict(self):
        """Test error context can be converted to dictionary."""
        context = ErrorContext(
            user_id=123456,
            guild_id=789012,
            command="test_command"
        )
        
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert context_dict["user_id"] == 123456
        assert context_dict["guild_id"] == 789012
        assert context_dict["command"] == "test_command"
    
    def test_error_context_from_discord_ctx(self):
        """Test creating error context from Discord context."""
        mock_ctx = MagicMock()
        mock_ctx.author.id = 123456
        mock_ctx.guild.id = 789012
        mock_ctx.channel.id = 456789
        mock_ctx.command.name = "test_command"
        
        context = ErrorContext.from_discord_context(mock_ctx)
        
        assert context.user_id == 123456
        assert context.guild_id == 789012
        assert context.channel_id == 456789
        assert context.command == "test_command"


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_recovery_strategy_registration(self):
        """Test registering recovery strategies."""
        recovery = ErrorRecovery()
        
        def test_strategy(error, context):
            return "recovered"
        
        recovery.register_strategy("TEST_001", test_strategy)
        
        assert "TEST_001" in recovery.strategies
        assert recovery.strategies["TEST_001"] == test_strategy
    
    def test_recovery_strategy_execution(self):
        """Test executing recovery strategy."""
        recovery = ErrorRecovery()
        
        def test_strategy(error, context):
            return f"Recovered from {error.error_code}"
        
        recovery.register_strategy("TEST_001", test_strategy)
        
        error = BotError("Test error", error_code="TEST_001")
        context = ErrorContext(user_id=123456)
        
        result = recovery.attempt_recovery(error, context)
        assert result == "Recovered from TEST_001"
    
    def test_recovery_strategy_not_found(self):
        """Test behavior when recovery strategy not found."""
        recovery = ErrorRecovery()
        
        error = BotError("Test error", error_code="UNKNOWN")
        context = ErrorContext(user_id=123456)
        
        result = recovery.attempt_recovery(error, context)
        assert result is None
    
    def test_recovery_strategy_failure(self):
        """Test handling recovery strategy failure."""
        recovery = ErrorRecovery()
        
        def failing_strategy(error, context):
            raise Exception("Recovery failed")
        
        recovery.register_strategy("TEST_001", failing_strategy)
        
        error = BotError("Test error", error_code="TEST_001")
        context = ErrorContext(user_id=123456)
        
        # Should handle recovery failure gracefully
        result = recovery.attempt_recovery(error, context)
        assert result is None


class TestErrorHandler:
    """Test main error handler."""
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock()
    
    @pytest.fixture
    def error_handler(self, mock_logger):
        """Create error handler for testing."""
        return ErrorHandler(logger=mock_logger)
    
    def test_error_handler_initialization(self, mock_logger):
        """Test error handler initialization."""
        handler = ErrorHandler(logger=mock_logger)
        
        assert handler.logger == mock_logger
        assert isinstance(handler.recovery, ErrorRecovery)
    
    def test_handle_user_error(self, error_handler, mock_logger):
        """Test handling user errors."""
        error = UserError(
            "User error occurred",
            user_message="Please try again.",
            error_code="USER_001"
        )
        context = ErrorContext(user_id=123456)
        
        result = error_handler.handle_error(error, context)
        
        assert result.user_message == "Please try again."
        assert result.should_notify_user is True
        assert result.should_log is True
        mock_logger.warning.assert_called_once()
    
    def test_handle_system_error(self, error_handler, mock_logger):
        """Test handling system errors."""
        error = SystemError(
            "System error occurred",
            error_code="SYS_001"
        )
        context = ErrorContext(user_id=123456)
        
        result = error_handler.handle_error(error, context)
        
        assert "internal error" in result.user_message.lower()
        assert result.should_notify_user is True
        assert result.should_log is True
        mock_logger.error.assert_called_once()
    
    def test_handle_configuration_error(self, error_handler, mock_logger):
        """Test handling configuration errors."""
        error = ConfigurationError(
            "Config error occurred",
            error_code="CFG_001"
        )
        context = ErrorContext(user_id=123456)
        
        result = error_handler.handle_error(error, context)
        
        assert "configuration" in result.user_message.lower()
        assert result.should_notify_user is False  # Don't bother users with config issues
        assert result.should_log is True
        mock_logger.critical.assert_called_once()
    
    def test_handle_unknown_error(self, error_handler, mock_logger):
        """Test handling unknown/unexpected errors."""
        error = ValueError("Unexpected error")
        context = ErrorContext(user_id=123456)
        
        result = error_handler.handle_error(error, context)
        
        assert "unexpected error" in result.user_message.lower()
        assert result.should_notify_user is True
        assert result.should_log is True
        mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_error_async(self, error_handler, mock_logger):
        """Test handling errors in async context."""
        error = UserError("Async user error", user_message="Async message")
        context = ErrorContext(user_id=123456)
        
        result = await error_handler.handle_error_async(error, context)
        
        assert result.user_message == "Async message"
        assert result.should_notify_user is True
    
    def test_error_handler_with_recovery(self, error_handler, mock_logger):
        """Test error handler with recovery strategy."""
        # Register recovery strategy
        def recovery_strategy(error, context):
            return "Successfully recovered"
        
        error_handler.recovery.register_strategy("USER_001", recovery_strategy)
        
        error = UserError(
            "Recoverable error",
            error_code="USER_001"
        )
        context = ErrorContext(user_id=123456)
        
        result = error_handler.handle_error(error, context)
        
        assert result.recovery_result == "Successfully recovered"
        assert result.recovered is True
    
    def test_error_handler_rate_limiting(self, error_handler, mock_logger):
        """Test error handler rate limiting to prevent spam."""
        error = UserError("Repeated error", error_code="USER_001")
        context = ErrorContext(user_id=123456)
        
        # First error should be handled normally
        result1 = error_handler.handle_error(error, context)
        assert result1.should_notify_user is True
        
        # Rapid subsequent errors should be rate limited
        for _ in range(10):
            result = error_handler.handle_error(error, context)
        
        # Should have rate limited after multiple rapid errors
        assert mock_logger.warning.call_count > 0


class TestErrorHandlerIntegration:
    """Test error handler integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_discord_command_error_handling(self):
        """Test error handling in Discord command context."""
        mock_ctx = MagicMock()
        mock_ctx.author.id = 123456
        mock_ctx.guild.id = 789012
        mock_ctx.channel.id = 456789
        mock_ctx.command.name = "test_command"
        mock_ctx.send = AsyncMock()
        
        handler = ErrorHandler()
        
        # Simulate command error
        error = UserError(
            "Command failed",
            user_message="The command could not be completed. Please try again.",
            error_code="CMD_001"
        )
        
        await handler.handle_discord_error(error, mock_ctx)
        
        # Should send error message to user
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[0][0]
        assert "could not be completed" in call_args
    
    def test_error_metrics_collection(self):
        """Test error metrics are collected for monitoring."""
        handler = ErrorHandler()
        
        # Generate various errors
        errors = [
            UserError("User error 1", error_code="USER_001"),
            UserError("User error 2", error_code="USER_001"),
            SystemError("System error 1", error_code="SYS_001"),
            ConfigurationError("Config error", error_code="CFG_001")
        ]
        
        for error in errors:
            context = ErrorContext(user_id=123456)
            handler.handle_error(error, context)
        
        metrics = handler.get_error_metrics()
        
        assert metrics["USER_001"] == 2
        assert metrics["SYS_001"] == 1
        assert metrics["CFG_001"] == 1
        assert metrics["total"] == 4
    
    def test_error_context_enrichment(self):
        """Test error context is enriched with additional information."""
        handler = ErrorHandler()
        
        error = SystemError("Test error", error_code="SYS_001")
        context = ErrorContext(user_id=123456, guild_id=789012)
        
        result = handler.handle_error(error, context)
        
        # Context should be enriched with timestamp, error ID, etc.
        assert result.context["user_id"] == 123456
        assert result.context["guild_id"] == 789012
        assert "timestamp" in result.context
        assert "error_id" in result.context


class TestGlobalErrorHandler:
    """Test global error handler functions."""
    
    def test_get_error_handler_returns_singleton(self):
        """Test get_error_handler returns singleton instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2
    
    def test_error_handler_configuration(self):
        """Test error handler can be configured globally."""
        mock_logger = MagicMock()
        
        handler = ErrorHandler(logger=mock_logger)
        
        # Test configuration is applied
        assert handler.logger == mock_logger