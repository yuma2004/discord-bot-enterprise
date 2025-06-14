"""
Test bot core framework - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from src.bot.core import DiscordBot, BotManager, ensure_user_registered, require_registration, admin_only


class TestDiscordBot:
    """Test Discord bot core functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = MagicMock()
        config.DATABASE_URL = ":memory:"
        config.ENVIRONMENT = "test"
        config.get_database_type.return_value = "SQLite"
        return config
    
    @pytest.fixture
    def bot(self, mock_config):
        """Create DiscordBot instance."""
        with patch('src.bot.core.get_config', return_value=mock_config), \
             patch('src.bot.core.get_logger'), \
             patch('src.bot.core.get_error_handler'):
            return DiscordBot()
    
    def test_bot_initialization(self, bot):
        """Test bot initialization."""
        assert bot is not None
        assert hasattr(bot, 'config')
        assert hasattr(bot, 'logger')
        assert hasattr(bot, 'error_handler')
        assert hasattr(bot, 'start_time')
        assert bot.commands_executed == 0
    
    def test_bot_intents_configuration(self, bot):
        """Test bot intents are properly configured."""
        intents = bot.intents
        assert intents.message_content is True
        assert intents.members is True
        assert intents.guilds is True
        assert intents.guild_reactions is True
    
    def test_builtin_commands_registered(self, bot):
        """Test built-in commands are registered."""
        command_names = [cmd.name for cmd in bot.commands]
        assert 'ping' in command_names
        assert 'info' in command_names
        assert 'health' in command_names
    
    @pytest.mark.asyncio
    async def test_on_ready(self, bot):
        """Test on_ready event handler."""
        bot.user = MagicMock()
        bot.user.id = 123456789
        bot.guilds = []
        
        with patch.object(bot, '_initialize_database') as mock_init_db, \
             patch.object(bot, '_set_status') as mock_set_status:
            await bot.on_ready()
            
            mock_init_db.assert_called_once()
            mock_set_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_message_ignores_bots(self, bot):
        """Test on_message ignores bot messages."""
        message = MagicMock()
        message.author.bot = True
        
        with patch.object(bot, 'process_commands') as mock_process:
            await bot.on_message(message)
            mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_message_processes_user_messages(self, bot):
        """Test on_message processes user messages."""
        message = MagicMock()
        message.author.bot = False
        
        with patch.object(bot, 'process_commands') as mock_process:
            await bot.on_message(message)
            mock_process.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_on_command_increments_counter(self, bot):
        """Test on_command increments command counter."""
        ctx = MagicMock()
        ctx.command.name = "test_command"
        ctx.author.id = 123456789
        ctx.guild.id = 987654321
        
        initial_count = bot.commands_executed
        await bot.on_command(ctx)
        
        assert bot.commands_executed == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_on_command_error_handles_not_found(self, bot):
        """Test command error handling for CommandNotFound."""
        ctx = MagicMock()
        ctx.send = AsyncMock()
        error = commands.CommandNotFound()
        
        await bot.on_command_error(ctx, error)
        
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "Command not found" in call_args
    
    @pytest.mark.asyncio
    async def test_on_command_error_handles_missing_argument(self, bot):
        """Test command error handling for MissingRequiredArgument."""
        ctx = MagicMock()
        ctx.send = AsyncMock()
        param = MagicMock()
        param.name = "test_param"
        error = commands.MissingRequiredArgument(param)
        
        await bot.on_command_error(ctx, error)
        
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "Missing required argument" in call_args
        assert "test_param" in call_args
    
    def test_get_uptime_format(self, bot):
        """Test uptime formatting."""
        # Test different uptime scenarios
        import datetime
        
        # Mock start time to 1 hour ago
        bot.start_time = datetime.datetime.now() - datetime.timedelta(hours=1, minutes=30)
        uptime = bot._get_uptime()
        assert "1h 30m" in uptime
        
        # Mock start time to 2 days ago
        bot.start_time = datetime.datetime.now() - datetime.timedelta(days=2, hours=3, minutes=15)
        uptime = bot._get_uptime()
        assert "2d 3h 15m" in uptime
    
    def test_get_memory_usage(self, bot):
        """Test memory usage retrieval."""
        memory_info = bot._get_memory_usage()
        
        # Should return either actual memory info or "N/A"
        assert isinstance(memory_info, str)
        assert memory_info == "N/A" or "MB" in memory_info


class TestBotManager:
    """Test bot manager functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = MagicMock()
        config.validate.return_value = None
        config.DISCORD_TOKEN = "test_token"
        return config
    
    @pytest.fixture
    def bot_manager(self, mock_config):
        """Create BotManager instance."""
        with patch('src.bot.core.get_config', return_value=mock_config), \
             patch('src.bot.core.get_logger'):
            return BotManager()
    
    @pytest.mark.asyncio
    async def test_create_bot(self, bot_manager):
        """Test bot creation."""
        with patch('src.bot.core.DiscordBot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot_class.return_value = mock_bot
            
            bot = await bot_manager.create_bot()
            
            assert bot == mock_bot
            assert bot_manager.bot == mock_bot
            bot_manager.config.validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_bot_without_create(self, bot_manager):
        """Test starting bot without creating first."""
        with pytest.raises(RuntimeError, match="Bot not created"):
            await bot_manager.start_bot()
    
    @pytest.mark.asyncio
    async def test_start_bot_success(self, bot_manager):
        """Test successful bot start."""
        mock_bot = AsyncMock()
        bot_manager.bot = mock_bot
        
        await bot_manager.start_bot()
        
        mock_bot.start.assert_called_once_with(bot_manager.config.DISCORD_TOKEN)
    
    @pytest.mark.asyncio
    async def test_stop_bot(self, bot_manager):
        """Test bot stopping."""
        mock_bot = AsyncMock()
        bot_manager.bot = mock_bot
        
        await bot_manager.stop_bot()
        
        mock_bot.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restart_bot(self, bot_manager):
        """Test bot restarting."""
        mock_bot = AsyncMock()
        bot_manager.bot = mock_bot
        
        with patch.object(bot_manager, 'stop_bot') as mock_stop, \
             patch.object(bot_manager, 'start_bot') as mock_start:
            await bot_manager.restart_bot()
            
            mock_stop.assert_called_once()
            mock_start.assert_called_once()
    
    def test_get_status_no_bot(self, bot_manager):
        """Test getting status when no bot created."""
        status = bot_manager.get_status()
        assert status["status"] == "not_created"
    
    def test_get_status_with_bot(self, bot_manager):
        """Test getting status with bot."""
        mock_bot = MagicMock()
        mock_bot.is_closed.return_value = False
        mock_bot.user = "TestBot#1234"
        mock_bot.guilds = [1, 2, 3]
        mock_bot.latency = 0.123
        mock_bot.commands_executed = 456
        
        bot_manager.bot = mock_bot
        
        status = bot_manager.get_status()
        assert status["status"] == "running"
        assert status["user"] == "TestBot#1234"
        assert status["guilds"] == 3
        assert status["latency"] == 0.123
        assert status["commands_executed"] == 456


class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_ensure_user_registered_existing_user(self):
        """Test ensuring user registration for existing user."""
        ctx = MagicMock()
        ctx.author.id = 123456789
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.return_value = {"id": 1, "discord_id": 123456789}
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await ensure_user_registered(ctx)
            
            assert result is True
            mock_db_manager.get_user.assert_called_once_with(123456789)
            mock_db_manager.create_user.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ensure_user_registered_new_user(self):
        """Test ensuring user registration for new user."""
        ctx = MagicMock()
        ctx.author.id = 123456789
        ctx.author.name = "testuser"
        ctx.author.display_name = "Test User"
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.return_value = None
        mock_db_manager.create_user.return_value = 1
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await ensure_user_registered(ctx)
            
            assert result is True
            mock_db_manager.get_user.assert_called_once_with(123456789)
            mock_db_manager.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_user_registered_database_error(self):
        """Test ensuring user registration with database error."""
        ctx = MagicMock()
        ctx.author.id = 123456789
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.side_effect = Exception("Database error")
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await ensure_user_registered(ctx)
            
            assert result is False


class TestDecorators:
    """Test command decorators."""
    
    @pytest.mark.asyncio
    async def test_require_registration_decorator_success(self):
        """Test require_registration decorator with successful registration."""
        @require_registration
        async def test_command(self, ctx):
            return "success"
        
        ctx = MagicMock()
        
        with patch('src.bot.core.ensure_user_registered', return_value=True):
            result = await test_command(None, ctx)
            assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_registration_decorator_failure(self):
        """Test require_registration decorator with failed registration."""
        @require_registration
        async def test_command(self, ctx):
            return "success"
        
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        with patch('src.bot.core.ensure_user_registered', return_value=False):
            result = await test_command(None, ctx)
            assert result is None
            ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator_success(self):
        """Test admin_only decorator with admin user."""
        @admin_only
        async def test_command(self, ctx):
            return "admin_success"
        
        ctx = MagicMock()
        ctx.author.id = 123456789
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.return_value = {"is_admin": True}
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await test_command(None, ctx)
            assert result == "admin_success"
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator_non_admin(self):
        """Test admin_only decorator with non-admin user."""
        @admin_only
        async def test_command(self, ctx):
            return "admin_success"
        
        ctx = MagicMock()
        ctx.author.id = 123456789
        ctx.send = AsyncMock()
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.return_value = {"is_admin": False}
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await test_command(None, ctx)
            assert result is None
            ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator_no_user(self):
        """Test admin_only decorator with non-existent user."""
        @admin_only
        async def test_command(self, ctx):
            return "admin_success"
        
        ctx = MagicMock()
        ctx.author.id = 123456789
        ctx.send = AsyncMock()
        
        mock_db_manager = AsyncMock()
        mock_db_manager.get_user.return_value = None
        
        with patch('src.bot.core.get_database_manager', return_value=mock_db_manager):
            result = await test_command(None, ctx)
            assert result is None
            ctx.send.assert_called_once()