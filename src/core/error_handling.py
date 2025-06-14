"""
Error handling framework - Clean TDD implementation
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from collections import defaultdict

from src.core.logging import get_logger


class BotError(Exception):
    """Base exception for all bot errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, user_message: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.user_message = user_message
        self.context = context or {}
        self.timestamp = datetime.now()
        self.error_id = str(uuid.uuid4())[:8]
    
    def is_user_error(self) -> bool:
        """Check if this is a user-facing error."""
        return isinstance(self, UserError)


class UserError(BotError):
    """Error caused by user action - should be shown to user."""
    
    def __init__(self, message: str, user_message: str, error_code: Optional[str] = None, **kwargs):
        super().__init__(message, error_code, user_message, **kwargs)


class SystemError(BotError):
    """Internal system error - should be logged but not shown to user."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, **kwargs):
        super().__init__(message, error_code, **kwargs)


class ConfigurationError(BotError):
    """Configuration-related error."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, config_field: Optional[str] = None, **kwargs):
        super().__init__(message, error_code, **kwargs)
        self.config_field = config_field


@dataclass
class ErrorContext:
    """Context information for error handling."""
    user_id: Optional[int] = None
    guild_id: Optional[int] = None
    channel_id: Optional[int] = None
    command: Optional[str] = None
    message_id: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result
    
    @classmethod
    def from_discord_context(cls, ctx: Any) -> 'ErrorContext':
        """Create error context from Discord command context."""
        return cls(
            user_id=getattr(ctx.author, 'id', None),
            guild_id=getattr(ctx.guild, 'id', None),
            channel_id=getattr(ctx.channel, 'id', None),
            command=getattr(ctx.command, 'name', None) if hasattr(ctx, 'command') else None,
            message_id=getattr(ctx.message, 'id', None) if hasattr(ctx, 'message') else None
        )


@dataclass
class ErrorResult:
    """Result of error handling."""
    user_message: str
    should_notify_user: bool
    should_log: bool
    log_level: str
    context: Dict[str, Any]
    recovered: bool = False
    recovery_result: Optional[Any] = None
    error_id: Optional[str] = None


class ErrorRecovery:
    """Error recovery mechanism."""
    
    def __init__(self):
        self.strategies: Dict[str, Callable] = {}
    
    def register_strategy(self, error_code: str, strategy: Callable) -> None:
        """Register recovery strategy for error code."""
        self.strategies[error_code] = strategy
    
    def attempt_recovery(self, error: BotError, context: ErrorContext) -> Optional[Any]:
        """Attempt to recover from error using registered strategy."""
        if error.error_code and error.error_code in self.strategies:
            try:
                strategy = self.strategies[error.error_code]
                return strategy(error, context)
            except Exception as e:
                # Recovery strategy failed - log but don't propagate
                logger = get_logger(__name__)
                logger.warning(f"Recovery strategy failed for {error.error_code}: {e}")
        
        return None


class ErrorHandler:
    """Main error handling coordinator."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger(__name__)
        self.recovery = ErrorRecovery()
        self.error_counts = defaultdict(int)
        self.user_error_timestamps = defaultdict(list)
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max = 5  # max errors per window
    
    def handle_error(self, error: Union[Exception, BotError], context: ErrorContext) -> ErrorResult:
        """Handle error and return appropriate response."""
        # Convert regular exceptions to BotError
        if not isinstance(error, BotError):
            error = SystemError(
                f"Unexpected error: {type(error).__name__}: {error}",
                error_code="UNEXPECTED"
            )
        
        # Enrich context
        enriched_context = self._enrich_context(error, context)
        
        # Check rate limiting
        if self._is_rate_limited(error, context):
            return self._create_rate_limited_result(error, enriched_context)
        
        # Attempt recovery
        recovery_result = self.recovery.attempt_recovery(error, context)
        recovered = recovery_result is not None
        
        # Determine response based on error type
        if isinstance(error, UserError):
            result = self._handle_user_error(error, enriched_context, recovery_result)
        elif isinstance(error, SystemError):
            result = self._handle_system_error(error, enriched_context, recovery_result)
        elif isinstance(error, ConfigurationError):
            result = self._handle_configuration_error(error, enriched_context, recovery_result)
        else:
            result = self._handle_unknown_error(error, enriched_context, recovery_result)
        
        result.recovered = recovered
        result.recovery_result = recovery_result
        result.error_id = error.error_id
        
        # Log the error
        if result.should_log:
            self._log_error(error, result)
        
        # Update metrics
        self._update_metrics(error)
        
        return result
    
    async def handle_error_async(self, error: Union[Exception, BotError], context: ErrorContext) -> ErrorResult:
        """Handle error asynchronously."""
        # For now, just call synchronous version
        # Could be extended for async recovery strategies
        return self.handle_error(error, context)
    
    async def handle_discord_error(self, error: Union[Exception, BotError], ctx: Any) -> None:
        """Handle error in Discord command context."""
        context = ErrorContext.from_discord_context(ctx)
        result = await self.handle_error_async(error, context)
        
        if result.should_notify_user and hasattr(ctx, 'send'):
            try:
                await ctx.send(result.user_message)
            except Exception as e:
                self.logger.error(f"Failed to send error message to user: {e}")
    
    def _enrich_context(self, error: BotError, context: ErrorContext) -> Dict[str, Any]:
        """Enrich error context with additional information."""
        enriched = context.to_dict()
        enriched.update({
            "timestamp": datetime.now().isoformat(),
            "error_id": error.error_id,
            "error_type": type(error).__name__,
            "error_code": error.error_code
        })
        enriched.update(error.context)
        return enriched
    
    def _is_rate_limited(self, error: BotError, context: ErrorContext) -> bool:
        """Check if error should be rate limited."""
        if not context.user_id:
            return False
        
        now = time.time()
        user_timestamps = self.user_error_timestamps[context.user_id]
        
        # Remove old timestamps
        user_timestamps[:] = [ts for ts in user_timestamps if now - ts < self.rate_limit_window]
        
        # Check if user has exceeded rate limit
        if len(user_timestamps) >= self.rate_limit_max:
            return True
        
        # Add current timestamp
        user_timestamps.append(now)
        return False
    
    def _create_rate_limited_result(self, error: BotError, context: Dict[str, Any]) -> ErrorResult:
        """Create result for rate-limited errors."""
        return ErrorResult(
            user_message="You're encountering errors too frequently. Please wait a moment before trying again.",
            should_notify_user=True,
            should_log=True,
            log_level="warning",
            context=context
        )
    
    def _handle_user_error(self, error: UserError, context: Dict[str, Any], recovery_result: Optional[Any]) -> ErrorResult:
        """Handle user errors."""
        return ErrorResult(
            user_message=error.user_message or "There was an issue with your request. Please try again.",
            should_notify_user=True,
            should_log=True,
            log_level="warning",
            context=context
        )
    
    def _handle_system_error(self, error: SystemError, context: Dict[str, Any], recovery_result: Optional[Any]) -> ErrorResult:
        """Handle system errors."""
        user_message = "An internal error occurred. Please try again later."
        if recovery_result:
            user_message = "An error occurred, but it has been automatically resolved. Please try your request again."
        
        return ErrorResult(
            user_message=user_message,
            should_notify_user=True,
            should_log=True,
            log_level="error",
            context=context
        )
    
    def _handle_configuration_error(self, error: ConfigurationError, context: Dict[str, Any], recovery_result: Optional[Any]) -> ErrorResult:
        """Handle configuration errors."""
        return ErrorResult(
            user_message="The bot is experiencing configuration issues. An administrator has been notified.",
            should_notify_user=False,  # Don't bother users with config issues
            should_log=True,
            log_level="critical",
            context=context
        )
    
    def _handle_unknown_error(self, error: BotError, context: Dict[str, Any], recovery_result: Optional[Any]) -> ErrorResult:
        """Handle unknown/unexpected errors."""
        return ErrorResult(
            user_message="An unexpected error occurred. Please try again later.",
            should_notify_user=True,
            should_log=True,
            log_level="error",
            context=context
        )
    
    def _log_error(self, error: BotError, result: ErrorResult) -> None:
        """Log error with appropriate level."""
        log_level = getattr(self.logger, result.log_level)
        
        log_level(
            f"Error handled: {type(error).__name__}: {error}",
            extra={
                "error_id": error.error_id,
                "error_code": error.error_code,
                "recovered": result.recovered,
                **result.context
            },
            exc_info=True if result.log_level == "error" else False
        )
    
    def _update_metrics(self, error: BotError) -> None:
        """Update error metrics."""
        self.error_counts["total"] += 1
        if error.error_code:
            self.error_counts[error.error_code] += 1
        self.error_counts[type(error).__name__] += 1
    
    def get_error_metrics(self) -> Dict[str, int]:
        """Get error metrics for monitoring."""
        return dict(self.error_counts)
    
    def clear_metrics(self) -> None:
        """Clear error metrics."""
        self.error_counts.clear()
        self.user_error_timestamps.clear()


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def set_error_handler(handler: ErrorHandler) -> None:
    """Set global error handler instance."""
    global _error_handler
    _error_handler = handler


# Convenience functions for common error scenarios
def handle_user_input_error(message: str, user_message: str, **context) -> UserError:
    """Create user input error."""
    return UserError(
        message=message,
        user_message=user_message,
        error_code="USER_INPUT",
        context=context
    )


def handle_permission_error(user_id: int, required_permission: str, **context) -> UserError:
    """Create permission error."""
    return UserError(
        message=f"User {user_id} lacks permission: {required_permission}",
        user_message=f"You don't have permission to use this command. Required: {required_permission}",
        error_code="PERMISSION_DENIED",
        context={"user_id": user_id, "required_permission": required_permission, **context}
    )


def handle_database_error(operation: str, table: str, original_error: Exception, **context) -> SystemError:
    """Create database error."""
    return SystemError(
        message=f"Database {operation} failed on {table}: {original_error}",
        error_code="DATABASE_ERROR",
        context={"operation": operation, "table": table, "original_error": str(original_error), **context}
    )


def handle_api_error(service: str, endpoint: str, status_code: int, **context) -> SystemError:
    """Create API error."""
    return SystemError(
        message=f"API call failed to {service} {endpoint}: HTTP {status_code}",
        error_code="API_ERROR",
        context={"service": service, "endpoint": endpoint, "status_code": status_code, **context}
    )


# Decorator for automatic error handling
def handle_errors(error_handler: Optional[ErrorHandler] = None):
    """Decorator for automatic error handling in functions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handler = error_handler or get_error_handler()
                context = ErrorContext()
                
                # Try to extract context from args
                for arg in args:
                    if hasattr(arg, 'author') and hasattr(arg.author, 'id'):
                        context = ErrorContext.from_discord_context(arg)
                        break
                
                result = await handler.handle_error_async(e, context)
                
                # If there's a Discord context, send error message
                for arg in args:
                    if hasattr(arg, 'send'):
                        if result.should_notify_user:
                            await arg.send(result.user_message)
                        break
                
                return None
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = error_handler or get_error_handler()
                context = ErrorContext()
                
                result = handler.handle_error(e, context)
                return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator