"""
Test the testing infrastructure itself
"""
import pytest


def test_pytest_works():
    """Test that pytest is working correctly."""
    assert True


def test_fixtures_available(mock_config, mock_logger, temp_db_path):
    """Test that our custom fixtures are available."""
    assert mock_config is not None
    assert mock_logger is not None
    assert temp_db_path is not None
    assert temp_db_path.endswith('.db')


@pytest.mark.asyncio
async def test_async_support():
    """Test that async tests work correctly."""
    import asyncio
    await asyncio.sleep(0.001)  # Minimal async operation
    assert True


def test_sample_data_fixtures(sample_user_data, sample_task_data, sample_attendance_data):
    """Test that sample data fixtures provide correct structure."""
    # Test user data
    assert 'discord_id' in sample_user_data
    assert 'username' in sample_user_data
    assert sample_user_data['discord_id'] == 987654321
    
    # Test task data
    assert 'title' in sample_task_data
    assert 'priority' in sample_task_data
    assert sample_task_data['title'] == "Sample Task"
    
    # Test attendance data
    assert 'user_id' in sample_attendance_data
    assert 'check_in' in sample_attendance_data
    assert sample_attendance_data['work_hours'] == 8.0


def test_mock_discord_fixtures(mock_discord_bot, mock_discord_ctx, mock_discord_member):
    """Test that Discord mock fixtures are properly configured."""
    # Test bot mock
    assert mock_discord_bot.user.id == 123456789
    assert mock_discord_bot.user.name == "TestBot"
    
    # Test context mock
    assert mock_discord_ctx.author.id == 987654321
    assert mock_discord_ctx.author.name == "TestUser"
    
    # Test member mock
    assert mock_discord_member.id == 987654321
    assert mock_discord_member.name == "testuser"
    assert not mock_discord_member.bot