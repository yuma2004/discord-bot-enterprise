"""
Test task manager commands - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from datetime import datetime

from src.bot.commands.task_manager import TaskManagerCog


class TestTaskManagerCog:
    """Test task manager cog functionality."""
    
    @pytest.fixture
    def mock_bot(self):
        """Mock Discord bot."""
        bot = MagicMock()
        return bot
    
    @pytest.fixture
    def task_cog(self, mock_bot):
        """Create TaskManagerCog instance."""
        with patch('src.bot.commands.task_manager.get_database_manager'), \
             patch('src.bot.commands.task_manager.get_error_handler'):
            return TaskManagerCog(mock_bot)
    
    @pytest.fixture
    def mock_ctx(self):
        """Mock Discord context."""
        ctx = MagicMock()
        ctx.author.id = 123456789
        ctx.author.name = "testuser"
        ctx.author.display_name = "Test User"
        ctx.guild.id = 987654321
        ctx.send = AsyncMock()
        return ctx
    
    def test_parse_task_info_basic(self, task_cog):
        """Test basic task info parsing."""
        result = task_cog._parse_task_info("Sample task")
        
        assert result['title'] == "Sample task"
        assert result['priority'] == 'medium'
        assert result['due_date'] is None
    
    def test_parse_task_info_with_priority(self, task_cog):
        """Test task info parsing with priority."""
        result = task_cog._parse_task_info("Important task priority:高")
        
        assert result['title'] == "Important task"
        assert result['priority'] == 'high'
    
    def test_parse_task_info_with_due_date(self, task_cog):
        """Test task info parsing with due date."""
        result = task_cog._parse_task_info("Task with deadline due:2024-12-31")
        
        assert result['title'] == "Task with deadline"
        assert result['due_date'] == datetime(2024, 12, 31)
    
    def test_parse_task_info_full_options(self, task_cog):
        """Test task info parsing with all options."""
        result = task_cog._parse_task_info("Complex task priority:low due:2024-06-15")
        
        assert result['title'] == "Complex task"
        assert result['priority'] == 'low'
        assert result['due_date'] == datetime(2024, 6, 15)
    
    def test_parse_task_info_empty_title(self, task_cog):
        """Test task info parsing with empty title."""
        from src.core.error_handling import UserError
        
        with pytest.raises(UserError):
            task_cog._parse_task_info("priority:high")
    
    @pytest.mark.asyncio
    async def test_add_task_success(self, task_cog, mock_ctx):
        """Test successful task addition."""
        # Mock database manager
        task_cog.db_manager.create_task = AsyncMock(return_value=123)
        
        await task_cog.add_task(mock_ctx, task_info="Test task")
        
        # Verify database call
        task_cog.db_manager.create_task.assert_called_once()
        call_args = task_cog.db_manager.create_task.call_args
        assert call_args[1]['user_id'] == 123456789
        assert call_args[1]['title'] == "Test task"
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, task_cog, mock_ctx):
        """Test listing tasks when none exist."""
        task_cog.db_manager.list_tasks = AsyncMock(return_value=[])
        
        await task_cog.list_tasks(mock_ctx)
        
        # Verify database call
        task_cog.db_manager.list_tasks.assert_called_once_with(123456789)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[0][0]
        assert "タスクがありません" in call_args
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, task_cog, mock_ctx):
        """Test successful task completion."""
        # Mock task exists and belongs to user
        mock_task = {
            'id': 123,
            'title': 'Test Task',
            'user_id': 123456789,
            'status': 'pending'
        }
        task_cog.db_manager.get_task = AsyncMock(return_value=mock_task)
        task_cog.db_manager.complete_task = AsyncMock(return_value=True)
        
        await task_cog.complete_task(mock_ctx, task_id=123)
        
        # Verify database calls
        task_cog.db_manager.get_task.assert_called_once_with(123)
        task_cog.db_manager.complete_task.assert_called_once_with(123)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_task_not_found(self, task_cog, mock_ctx):
        """Test completing non-existent task."""
        task_cog.db_manager.get_task = AsyncMock(return_value=None)
        
        await task_cog.complete_task(mock_ctx, task_id=999)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[0][0]
        assert "見つかりません" in call_args
    
    @pytest.mark.asyncio
    async def test_complete_task_wrong_user(self, task_cog, mock_ctx):
        """Test completing task owned by different user."""
        # Mock task exists but belongs to different user
        mock_task = {
            'id': 123,
            'title': 'Test Task',
            'user_id': 999999999,  # Different user
            'status': 'pending'
        }
        task_cog.db_manager.get_task = AsyncMock(return_value=mock_task)
        
        await task_cog.complete_task(mock_ctx, task_id=123)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args[0][0]
        assert "他のユーザーのタスク" in call_args
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_cog, mock_ctx):
        """Test successful task deletion."""
        # Mock task exists and belongs to user
        mock_task = {
            'id': 123,
            'title': 'Test Task',
            'user_id': 123456789,
            'status': 'pending'
        }
        task_cog.db_manager.get_task = AsyncMock(return_value=mock_task)
        task_cog.db_manager.delete_task = AsyncMock(return_value=True)
        
        await task_cog.delete_task(mock_ctx, task_id=123)
        
        # Verify database calls
        task_cog.db_manager.get_task.assert_called_once_with(123)
        task_cog.db_manager.delete_task.assert_called_once_with(123)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_progress_task_success(self, task_cog, mock_ctx):
        """Test successful task progress update."""
        # Mock task exists and belongs to user
        mock_task = {
            'id': 123,
            'title': 'Test Task',
            'user_id': 123456789,
            'status': 'pending'
        }
        task_cog.db_manager.get_task = AsyncMock(return_value=mock_task)
        task_cog.db_manager.update_task = AsyncMock(return_value=True)
        
        await task_cog.progress_task(mock_ctx, task_id=123)
        
        # Verify database calls
        task_cog.db_manager.get_task.assert_called_once_with(123)
        task_cog.db_manager.update_task.assert_called_once_with(123, status='in_progress')
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_task_help(self, task_cog, mock_ctx):
        """Test task help command."""
        await task_cog.task_help(mock_ctx)
        
        # Verify response sent
        mock_ctx.send.assert_called_once()
        
        # Check if embed was sent
        call_args = mock_ctx.send.call_args
        assert len(call_args[1]) > 0 or len(call_args[0]) > 0


class TestTaskParsingEdgeCases:
    """Test edge cases in task parsing."""
    
    @pytest.fixture
    def task_cog(self):
        """Create TaskManagerCog instance for parsing tests."""
        with patch('src.bot.commands.task_manager.get_database_manager'), \
             patch('src.bot.commands.task_manager.get_error_handler'):
            return TaskManagerCog(MagicMock())
    
    def test_parse_multiple_priority_options(self, task_cog):
        """Test parsing with multiple priority options."""
        result = task_cog._parse_task_info("Task priority:high priority:low")
        
        # Should use the first match
        assert result['priority'] == 'high'
        assert "Task" in result['title']
    
    def test_parse_japanese_priority(self, task_cog):
        """Test parsing with Japanese priority."""
        result = task_cog._parse_task_info("日本語タスク priority:高")
        
        assert result['priority'] == 'high'
        assert result['title'] == "日本語タスク"
    
    def test_parse_invalid_date(self, task_cog):
        """Test parsing with invalid date."""
        result = task_cog._parse_task_info("Task due:2024-13-40")
        
        # Invalid date should be ignored
        assert result['due_date'] is None
        assert result['title'] == "Task"
    
    def test_parse_case_insensitive(self, task_cog):
        """Test case insensitive parsing."""
        result = task_cog._parse_task_info("Task PRIORITY:HIGH DUE:2024-12-31")
        
        assert result['priority'] == 'high'
        assert result['due_date'] == datetime(2024, 12, 31)
    
    def test_parse_whitespace_handling(self, task_cog):
        """Test whitespace handling in parsing."""
        result = task_cog._parse_task_info("  Task with spaces   priority:medium  ")
        
        assert result['title'] == "Task with spaces"
        assert result['priority'] == 'medium'