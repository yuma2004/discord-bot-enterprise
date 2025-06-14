"""
Enterprise Discord Bot - Main Application
Clean TDD Architecture v3.0.0
"""
import asyncio
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import load_config_from_env, ConfigError
from src.core.logging import configure_logging, get_logger
from src.core.database import set_database_manager, DatabaseManager, get_database_manager, is_postgresql_url
from src.core.error_handling import set_error_handler, ErrorHandler
from src.core.health_check import start_health_server, stop_health_server
from src.bot.core import get_bot_manager


class Application:
    """Main application controller."""
    
    def __init__(self):
        self.logger = None
        self.bot_manager = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize application components."""
        try:
            # Load configuration
            config = load_config_from_env()
            
            # Configure logging
            log_file = "logs/bot.log" if config.is_production() else None
            configure_logging(config.LOG_LEVEL, log_file)
            self.logger = get_logger(__name__)
            
            self.logger.info("=== Discord Bot Enterprise v3.0.0 Starting ===")
            self.logger.info(f"Environment: {config.ENVIRONMENT}")
            self.logger.info(f"Database: {config.get_database_type()}")
            
            # Initialize database (auto-detects PostgreSQL vs SQLite)
            db_manager = get_database_manager(config.DATABASE_URL)
            set_database_manager(db_manager)
            
            # Initialize error handling
            error_handler = ErrorHandler(self.logger)
            set_error_handler(error_handler)
            
            # Create bot manager
            self.bot_manager = get_bot_manager()
            
            # Start health check server for production
            if config.is_production():
                start_health_server(config.HEALTH_CHECK_PORT)
                self.logger.info(f"Health check server started on port {config.HEALTH_CHECK_PORT}")
            
            self.logger.info("Application initialized successfully")
            
        except ConfigError as e:
            print(f"Configuration Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Initialization Error: {e}")
            sys.exit(1)
    
    async def start(self):
        """Start the application."""
        try:
            await self.initialize()
            
            # Create and start bot
            bot = await self.bot_manager.create_bot()
            
            self.logger.info("Starting Discord bot...")
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Start bot and wait for shutdown
            bot_task = asyncio.create_task(self.bot_manager.start_bot())
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())
            
            # Wait for either bot to complete or shutdown signal
            done, pending = await asyncio.wait(
                [bot_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if bot task failed
            if bot_task in done:
                try:
                    await bot_task
                except Exception as e:
                    self.logger.error(f"Bot task failed: {e}")
                    raise
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown application gracefully."""
        if self.logger:
            self.logger.info("Shutting down application...")
        
        if self.bot_manager:
            try:
                await self.bot_manager.stop_bot()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error stopping bot: {e}")
        
        # Stop health check server
        try:
            stop_health_server()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error stopping health server: {e}")
        
        if self.logger:
            self.logger.info("Application shutdown complete")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if self.logger:
                self.logger.info(f"Received signal {signum}")
            self.shutdown_event.set()
        
        # Only set up signal handlers on Unix-like systems
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)


async def main():
    """Main entry point."""
    app = Application()
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)