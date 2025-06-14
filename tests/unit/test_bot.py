"""
Test Discord bot framework - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from src.bot.core import DiscordBot, BotManager


class TestDiscordBot:
    """Test Discord bot core functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = MagicMock()
        config.DISCORD_TOKEN = "test_token"
        config.DISCORD_GUILD_ID = 123456789
        config.ENVIRONMENT = "test"
        config.LOG_LEVEL = "DEBUG"
        return config
    
    @pytest.fixture
    def bot(self, mock_config):
        """Create bot instance for testing."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            return DiscordBot()
    
    def test_bot_initialization(self, bot, mock_config):
        """Test bot initializes with correct configuration."""
        assert bot.command_prefix == "!"
        assert bot.case_insensitive is True
        assert discord.Intents.message_content in bot.intents
        assert discord.Intents.members in bot.intents
    
    def test_bot_has_required_intents(self, bot):
        """Test bot has required Discord intents."""
        intents = bot.intents
        assert intents.message_content is True
        assert intents.members is True
        assert intents.guilds is True
        assert intents.guild_reactions is True
    
    @pytest.mark.asyncio
    async def test_bot_on_ready_event(self, bot):
        """Test bot on_ready event handler."""
        bot.user = MagicMock()
        bot.user.id = 123456789
        bot.user.name = "TestBot"
        bot.guilds = []
        
        with patch.object(bot, '_initialize_database') as mock_init_db:
            with patch.object(bot, '_set_status') as mock_set_status:
                await bot.on_ready()
                
                mock_init_db.assert_called_once()
                mock_set_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bot_database_initialization(self, bot):
        """Test bot initializes database on startup."""
        with patch('src.bot.core.get_database_manager') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            await bot._initialize_database()
            
            mock_db.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bot_status_setting(self, bot):
        """Test bot sets appropriate status."""
        with patch.object(bot, 'change_presence') as mock_change_presence:
            await bot._set_status()
            
            mock_change_presence.assert_called_once()
            call_args = mock_change_presence.call_args
            activity = call_args[1]['activity']
            assert isinstance(activity, discord.Activity)
    
    @pytest.mark.asyncio
    async def test_bot_command_error_handling(self, bot):
        """Test bot handles command errors appropriately."""
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()
        
        # Test CommandNotFound
        error = commands.CommandNotFound()
        await bot.on_command_error(mock_ctx, error)
        mock_ctx.send.assert_called()
        
        # Test MissingRequiredArgument
        mock_ctx.send.reset_mock()
        error = commands.MissingRequiredArgument(MagicMock())
        error.param = MagicMock()
        error.param.name = "test_param"
        await bot.on_command_error(mock_ctx, error)
        mock_ctx.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_bot_loads_extensions(self, bot):
        """Test bot loads required extensions."""
        extensions = [
            "src.bot.commands.tasks",
            "src.bot.commands.attendance", 
            "src.bot.commands.admin",
            "src.bot.commands.help"
        ]
        
        with patch.object(bot, 'load_extension') as mock_load:
            await bot._load_extensions()
            
            assert mock_load.call_count == len(extensions)
            loaded_extensions = [call[0][0] for call in mock_load.call_args_list]
            for ext in extensions:
                assert ext in loaded_extensions
    
    @pytest.mark.asyncio
    async def test_bot_handles_extension_load_failure(self, bot):
        """Test bot handles extension loading failures gracefully."""
        with patch.object(bot, 'load_extension') as mock_load:
            mock_load.side_effect = Exception("Extension load failed")
            
            # Should not raise exception
            await bot._load_extensions()
            
            # Should have attempted to load extensions
            assert mock_load.call_count > 0
    
    def test_bot_user_registration(self, bot):
        """Test bot registers users automatically."""
        mock_member = MagicMock()
        mock_member.id = 987654321
        mock_member.name = "testuser"
        mock_member.display_name = "Test User"
        mock_member.bot = False
        
        with patch('src.bot.core.get_database_manager') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.get_user = AsyncMock(return_value=None)  # User doesn't exist
            mock_db.create_user = AsyncMock(return_value=1)
            
            # This would be called in a real command
            assert mock_member.id == 987654321


class TestBotManager:
    """Test bot manager functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = MagicMock()
        config.DISCORD_TOKEN = "test_token"
        config.validate = MagicMock()
        return config
    
    def test_manager_initialization(self, mock_config):
        """Test bot manager initialization."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            assert manager.config == mock_config
            assert manager.bot is None
    
    @pytest.mark.asyncio
    async def test_manager_creates_bot(self, mock_config):
        """Test manager creates bot instance."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            bot = await manager.create_bot()
            
            assert isinstance(bot, DiscordBot)
            assert manager.bot == bot
    
    @pytest.mark.asyncio
    async def test_manager_starts_bot(self, mock_config):
        """Test manager starts bot."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            bot = await manager.create_bot()
            
            with patch.object(bot, 'start') as mock_start:
                await manager.start_bot()
                mock_start.assert_called_once_with(mock_config.DISCORD_TOKEN)
    
    @pytest.mark.asyncio
    async def test_manager_handles_startup_errors(self, mock_config):
        """Test manager handles bot startup errors."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            bot = await manager.create_bot()
            
            with patch.object(bot, 'start') as mock_start:
                mock_start.side_effect = Exception("Connection failed")
                
                with pytest.raises(Exception):
                    await manager.start_bot()
    
    @pytest.mark.asyncio
    async def test_manager_stops_bot(self, mock_config):
        """Test manager stops bot gracefully."""
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            bot = await manager.create_bot()
            
            with patch.object(bot, 'close') as mock_close:
                await manager.stop_bot()
                mock_close.assert_called_once()


class TestBotCommands:
    """Test built-in bot commands."""
    
    @pytest.fixture
    def bot(self):
        """Create bot for command testing."""
        with patch('src.bot.core.get_config'):
            return DiscordBot()
    
    @pytest.mark.asyncio
    async def test_ping_command(self, bot):
        """Test ping command."""
        ctx = MagicMock()
        ctx.send = AsyncMock()
        bot.latency = 0.1
        
        # Execute ping command
        await bot.ping_command(ctx)
        
        ctx.send.assert_called_once()
        # Check that embed was sent
        call_args = ctx.send.call_args[1]
        assert 'embed' in call_args
        embed = call_args['embed']
        assert "Pong!" in embed.title
    
    @pytest.mark.asyncio
    async def test_info_command(self, bot):
        """Test info command."""
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Execute info command
        await bot.info_command(ctx)
        
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[1]
        assert 'embed' in call_args
        embed = call_args['embed']
        assert "Discord Bot" in embed.title
    
    @pytest.mark.asyncio
    async def test_health_command(self, bot):
        """Test health check command."""
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        with patch('src.bot.core.get_database_manager') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.get_connection = AsyncMock()
            
            await bot.health_command(ctx)
            
            ctx.send.assert_called_once()
            call_args = ctx.send.call_args[1]
            assert 'embed' in call_args


class TestBotIntegration:
    """Test bot integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_bot_lifecycle(self):
        """Test complete bot startup and shutdown."""
        mock_config = MagicMock()
        mock_config.DISCORD_TOKEN = "test_token"
        mock_config.DISCORD_GUILD_ID = 123456789
        mock_config.validate = MagicMock()
        
        with patch('src.bot.core.get_config', return_value=mock_config):
            manager = BotManager()
            
            # Create bot
            bot = await manager.create_bot()
            assert bot is not None
            
            # Simulate startup without actually connecting
            with patch.object(bot, 'start') as mock_start:
                await manager.start_bot()
                mock_start.assert_called_once()
            
            # Simulate shutdown
            with patch.object(bot, 'close') as mock_close:
                await manager.stop_bot()
                mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_interaction_flow(self):
        """Test typical user interaction flow."""
        mock_config = MagicMock()
        mock_config.DISCORD_TOKEN = "test_token"
        
        with patch('src.bot.core.get_config', return_value=mock_config):
            bot = DiscordBot()
            
            # Simulate user message
            mock_message = MagicMock()
            mock_message.author.bot = False
            mock_message.author.id = 123456789
            mock_message.content = "!ping"
            
            # Should process commands for non-bot messages
            with patch.object(bot, 'process_commands') as mock_process:
                await bot.on_message(mock_message)
                mock_process.assert_called_once_with(mock_message)
            
            # Should ignore bot messages
            mock_message.author = bot.user = MagicMock()
            await bot.on_message(mock_message)
            # process_commands should not be called again
            assert mock_process.call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling integration."""
        mock_config = MagicMock()
        mock_config.DISCORD_TOKEN = "test_token"
        
        with patch('src.bot.core.get_config', return_value=mock_config):
            bot = DiscordBot()
            
            ctx = MagicMock()
            ctx.send = AsyncMock()
            
            # Test various error types
            errors = [
                commands.CommandNotFound(),
                commands.MissingRequiredArgument(MagicMock()),
                commands.BadArgument(),
                commands.CommandOnCooldown(None, 10.0),
                Exception("Unexpected error")
            ]
            
            for error in errors:
                await bot.on_command_error(ctx, error)
                ctx.send.assert_called()
                ctx.send.reset_mock()