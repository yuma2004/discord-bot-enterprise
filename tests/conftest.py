"""
Test configuration and fixtures for Discord Bot Enterprise
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiosqlite


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
async def test_db(temp_db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Create a test database connection."""
    async with aiosqlite.connect(temp_db_path) as conn:
        # Enable foreign keys and WAL mode
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.commit()
        yield conn


@pytest.fixture
def mock_discord_bot() -> MagicMock:
    """Mock Discord bot instance."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.user.name = "TestBot"
    bot.guilds = []
    bot.latency = 0.1
    return bot


@pytest.fixture
def mock_discord_ctx() -> MagicMock:
    """Mock Discord context for command testing."""
    ctx = MagicMock()
    ctx.author = MagicMock()
    ctx.author.id = 987654321
    ctx.author.name = "TestUser"
    ctx.author.display_name = "Test User"
    ctx.guild = MagicMock()
    ctx.guild.id = 111222333
    ctx.send = AsyncMock()
    ctx.reply = AsyncMock()
    return ctx


@pytest.fixture
def mock_discord_member() -> MagicMock:
    """Mock Discord member for testing."""
    member = MagicMock()
    member.id = 987654321
    member.name = "testuser"
    member.display_name = "Test User"
    member.bot = False
    return member


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        "discord_id": 987654321,
        "username": "testuser",
        "display_name": "Test User",
        "is_admin": False,
        "timezone": "Asia/Tokyo",
        "created_at": "2024-01-01T00:00:00+09:00"
    }


@pytest.fixture
def sample_task_data() -> dict:
    """Sample task data for testing."""
    return {
        "title": "Sample Task",
        "description": "This is a test task",
        "priority": "medium",
        "status": "pending",
        "due_date": "2024-12-31T23:59:59+09:00",
        "user_id": 987654321
    }


@pytest.fixture
def sample_attendance_data() -> dict:
    """Sample attendance data for testing."""
    from datetime import datetime
    return {
        "user_id": 987654321,
        "date": "2024-01-01",
        "check_in": datetime(2024, 1, 1, 9, 0),
        "check_out": datetime(2024, 1, 1, 18, 0),
        "break_start": datetime(2024, 1, 1, 12, 0),
        "break_end": datetime(2024, 1, 1, 13, 0),
        "work_hours": 8.0,
        "overtime_hours": 0.0
    }


@pytest.fixture
def mock_datetime_utils():
    """Mock datetime utilities for testing."""
    with patch("src.utils.datetime_utils.now_jst") as mock_now, \
         patch("src.utils.datetime_utils.today_jst") as mock_today:
        from datetime import datetime, date
        mock_now.return_value = datetime(2024, 6, 15, 10, 0, 0)
        mock_today.return_value = date(2024, 6, 15)
        yield {
            "now_jst": mock_now,
            "today_jst": mock_today
        }


@pytest.fixture
def mock_config() -> Generator[MagicMock, None, None]:
    """Mock configuration for testing."""
    with patch("src.core.config.Config") as mock_config:
        mock_config.DATABASE_URL = ":memory:"
        mock_config.DISCORD_TOKEN = "test_token"
        mock_config.DISCORD_GUILD_ID = 111222333
        mock_config.TIMEZONE = "Asia/Tokyo"
        mock_config.ENVIRONMENT = "test"
        mock_config.LOG_LEVEL = "DEBUG"
        yield mock_config


@pytest.fixture
async def mock_database() -> AsyncGenerator[MagicMock, None]:
    """Mock database manager for testing."""
    db_mock = AsyncMock()
    db_mock.connection = AsyncMock()
    db_mock.execute = AsyncMock()
    db_mock.fetchone = AsyncMock()
    db_mock.fetchall = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.rollback = AsyncMock()
    db_mock.close = AsyncMock()
    
    with patch("src.core.database.DatabaseManager", return_value=db_mock):
        yield db_mock


@pytest.fixture
def mock_logger() -> Generator[MagicMock, None, None]:
    """Mock logger for testing."""
    with patch("src.core.logging.get_logger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger
        yield logger


@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """Setup test environment variables."""
    test_env = {
        "DISCORD_TOKEN": "test_token",
        "DISCORD_GUILD_ID": "111222333", 
        "DATABASE_URL": ":memory:",
        "ENVIRONMENT": "test",
        "TIMEZONE": "Asia/Tokyo",
        "LOG_LEVEL": "DEBUG"
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Pytest-asyncio configuration
pytest_plugins = ("pytest_asyncio",)