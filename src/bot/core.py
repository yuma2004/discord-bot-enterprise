"""
Discord bot core framework - Clean TDD implementation
"""
import asyncio
import discord
from discord.ext import commands
from typing import Optional, List
import sys
from datetime import datetime

from src.core.config import get_config
from src.core.database import get_database_manager
from src.core.logging import get_logger, log_command_execution
from src.core.error_handling import get_error_handler, ErrorContext, handle_errors


class DiscordBot(commands.Bot):
    """Main Discord bot class with enterprise features."""
    
    def __init__(self):
        """Initialize Discord bot."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.error_handler = get_error_handler()
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.guild_reactions = True
        
        super().__init__(
            command_prefix="!",
            case_insensitive=True,
            intents=intents,
            description="Enterprise Discord Bot with TDD Architecture",
            help_command=None  # We'll implement custom help
        )
        
        # Bot state
        self.start_time = datetime.now()
        self.commands_executed = 0
        
        # Add built-in commands
        self._add_builtin_commands()
    
    async def setup_hook(self):
        """Setup hook called when bot is starting."""
        self.logger.info("Bot setup starting...")
        
        # Load extensions
        await self._load_extensions()
        
        self.logger.info("Bot setup completed")
    
    async def on_ready(self):
        """Called when bot is ready."""
        self.logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Initialize database
        await self._initialize_database()
        
        # Set bot status
        await self._set_status()
        
        self.logger.info("Bot is ready and operational")
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Process commands
        await self.process_commands(message)
    
    async def on_command(self, ctx: commands.Context):
        """Called when a command is invoked."""
        self.commands_executed += 1
        
        log_command_execution(
            self.logger,
            command=ctx.command.name,
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            success=True
        )
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle command errors."""
        context = ErrorContext.from_discord_context(ctx)
        
        # Handle specific Discord.py errors
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found. Use `!help` to see available commands.")
            return
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`")
            return
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided. Please check your input.")
            return
        
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
            return
        
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
        
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(f"I'm missing required permissions: {missing_perms}")
            return
        
        # Handle other errors through error handler
        await self.error_handler.handle_discord_error(error, ctx)
        
        log_command_execution(
            self.logger,
            command=ctx.command.name if ctx.command else "unknown",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            success=False,
            error=str(error)
        )
    
    async def _initialize_database(self):
        """Initialize database connection."""
        try:
            db_manager = get_database_manager(self.config.DATABASE_URL)
            await db_manager.initialize()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _set_status(self):
        """Set bot status/activity."""
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="企業のワークフローを支援中..."
            )
            await self.change_presence(activity=activity)
            self.logger.info("Bot status set successfully")
        except Exception as e:
            self.logger.warning(f"Failed to set bot status: {e}")
    
    async def _load_extensions(self):
        """Load bot extensions/cogs."""
        extensions = [
            "src.bot.commands.tasks",
            "src.bot.commands.attendance", 
            "src.bot.commands.admin",
            "src.bot.commands.help"
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                self.logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}: {e}")
                # Continue loading other extensions
    
    def _add_builtin_commands(self):
        """Add built-in commands to the bot."""
        @self.command(name="ping")
        async def ping_command(ctx):
            """Check bot latency."""
            latency_ms = round(self.latency * 1000)
            
            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Latency: {latency_ms}ms",
                color=discord.Color.green()
            )
            embed.add_field(name="Status", value="✅ Online", inline=True)
            embed.add_field(name="Uptime", value=self._get_uptime(), inline=True)
            
            await ctx.send(embed=embed)
        
        @self.command(name="info")
        async def info_command(ctx):
            """Show bot information."""
            embed = discord.Embed(
                title="🤖 Enterprise Discord Bot",
                description="Clean TDD architecture for enterprise productivity",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Version",
                value="3.0.0",
                inline=True
            )
            embed.add_field(
                name="Environment", 
                value=self.config.ENVIRONMENT,
                inline=True
            )
            embed.add_field(
                name="Guilds",
                value=str(len(self.guilds)),
                inline=True
            )
            embed.add_field(
                name="Commands Executed",
                value=str(self.commands_executed),
                inline=True
            )
            embed.add_field(
                name="Uptime",
                value=self._get_uptime(),
                inline=True
            )
            embed.add_field(
                name="Database",
                value=self.config.get_database_type(),
                inline=True
            )
            
            await ctx.send(embed=embed)
        
        @self.command(name="health")
        async def health_command(ctx):
            """Check bot health status."""
            embed = discord.Embed(
                title="🔍 Health Check",
                color=discord.Color.green()
            )
            
            # Check database connection
            try:
                db_manager = get_database_manager()
                async with db_manager.get_connection():
                    db_status = "✅ Connected"
                    db_color = discord.Color.green()
            except Exception as e:
                db_status = f"❌ Error: {str(e)[:50]}"
                db_color = discord.Color.red()
                embed.color = db_color
            
            embed.add_field(name="Database", value=db_status, inline=False)
            embed.add_field(name="Latency", value=f"{round(self.latency * 1000)}ms", inline=True)
            embed.add_field(name="Memory", value=self._get_memory_usage(), inline=True)
            
            await ctx.send(embed=embed)
        
        # Store references to commands for testing
        self.ping_command = ping_command
        self.info_command = info_command
        self.health_command = health_command
    
    def _get_uptime(self) -> str:
        """Get bot uptime as formatted string."""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _get_memory_usage(self) -> str:
        """Get memory usage information."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return f"{memory_mb:.1f} MB"
        except ImportError:
            return "N/A"


class BotManager:
    """Manager for bot lifecycle."""
    
    def __init__(self):
        """Initialize bot manager."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.bot: Optional[DiscordBot] = None
    
    async def create_bot(self) -> DiscordBot:
        """Create and configure bot instance."""
        self.logger.info("Creating bot instance...")
        
        # Validate configuration
        self.config.validate()
        
        # Create bot
        self.bot = DiscordBot()
        
        self.logger.info("Bot instance created successfully")
        return self.bot
    
    async def start_bot(self):
        """Start the bot."""
        if not self.bot:
            raise RuntimeError("Bot not created. Call create_bot() first.")
        
        self.logger.info("Starting bot...")
        
        try:
            await self.bot.start(self.config.DISCORD_TOKEN)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise
    
    async def stop_bot(self):
        """Stop the bot gracefully."""
        if self.bot:
            self.logger.info("Stopping bot...")
            await self.bot.close()
            self.logger.info("Bot stopped successfully")
    
    async def restart_bot(self):
        """Restart the bot."""
        await self.stop_bot()
        await self.start_bot()
    
    def get_status(self) -> dict:
        """Get bot status information."""
        if not self.bot:
            return {"status": "not_created"}
        
        return {
            "status": "running" if not self.bot.is_closed() else "stopped",
            "user": str(self.bot.user) if self.bot.user else None,
            "guilds": len(self.bot.guilds) if self.bot.guilds else 0,
            "latency": self.bot.latency if hasattr(self.bot, 'latency') else None,
            "commands_executed": getattr(self.bot, 'commands_executed', 0)
        }


# Global bot manager instance
_bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """Get global bot manager instance."""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager


def set_bot_manager(manager: BotManager) -> None:
    """Set global bot manager instance."""
    global _bot_manager
    _bot_manager = manager


# Utility functions for commands
async def ensure_user_registered(ctx: commands.Context) -> bool:
    """Ensure user is registered in database."""
    try:
        db_manager = get_database_manager()
        user = await db_manager.get_user(ctx.author.id)
        
        if not user:
            # Register new user
            await db_manager.create_user(
                discord_id=ctx.author.id,
                username=ctx.author.name,
                display_name=ctx.author.display_name
            )
            
            logger = get_logger(__name__)
            logger.info(f"Registered new user: {ctx.author.name} ({ctx.author.id})")
        
        return True
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to register user {ctx.author.id}: {e}")
        return False


def require_registration(func):
    """Decorator to ensure user is registered before command execution."""
    async def wrapper(self, ctx: commands.Context, *args, **kwargs):
        if await ensure_user_registered(ctx):
            return await func(self, ctx, *args, **kwargs)
        else:
            await ctx.send("Failed to register user. Please try again later.")
    
    return wrapper


def admin_only(func):
    """Decorator to restrict command to administrators."""
    async def wrapper(self, ctx: commands.Context, *args, **kwargs):
        try:
            db_manager = get_database_manager()
            user = await db_manager.get_user(ctx.author.id)
            
            if user and user.get('is_admin', False):
                return await func(self, ctx, *args, **kwargs)
            else:
                await ctx.send("This command requires administrator privileges.")
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error checking admin status for {ctx.author.id}: {e}")
            await ctx.send("Error checking permissions. Please try again later.")
    
    return wrapper