"""
Test database abstraction layer - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiosqlite
from datetime import datetime

from src.core.database import DatabaseManager, DatabaseConnection, DatabaseError


class TestDatabaseConnection:
    """Test database connection wrapper."""
    
    @pytest.mark.asyncio
    async def test_connection_context_manager(self, temp_db_path):
        """Test connection can be used as async context manager."""
        async with DatabaseConnection(temp_db_path) as conn:
            assert conn is not None
            # Should be able to execute queries
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            await conn.commit()
    
    @pytest.mark.asyncio 
    async def test_connection_execute_query(self, temp_db_path):
        """Test executing basic SQL queries."""
        async with DatabaseConnection(temp_db_path) as conn:
            # Create table
            await conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
            await conn.commit()
            
            # Insert data
            await conn.execute("INSERT INTO users (name) VALUES (?)", ("test_user",))
            await conn.commit()
            
            # Query data
            cursor = await conn.execute("SELECT name FROM users WHERE id = 1")
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] == "test_user"
    
    @pytest.mark.asyncio
    async def test_connection_handles_errors(self, temp_db_path):
        """Test connection properly handles SQL errors."""
        async with DatabaseConnection(temp_db_path) as conn:
            with pytest.raises(DatabaseError):
                await conn.execute("INVALID SQL SYNTAX")
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, temp_db_path):
        """Test transaction rollback on error."""
        async with DatabaseConnection(temp_db_path) as conn:
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            await conn.commit()
            
            try:
                await conn.execute("BEGIN TRANSACTION")
                await conn.execute("INSERT INTO test (id) VALUES (1)")
                # Force error to trigger rollback
                await conn.execute("INSERT INTO test (id) VALUES (1)")  # Duplicate key
                await conn.commit()
            except DatabaseError:
                await conn.rollback()
            
            # Should have no records due to rollback
            cursor = await conn.execute("SELECT COUNT(*) FROM test")
            count = await cursor.fetchone()
            assert count[0] == 0


class TestDatabaseManager:
    """Test database manager functionality."""
    
    def test_manager_initialization(self):
        """Test database manager can be initialized."""
        manager = DatabaseManager(":memory:")
        assert manager.database_url == ":memory:"
        assert manager.connection_pool is None
    
    @pytest.mark.asyncio
    async def test_manager_connection_creation(self):
        """Test manager can create database connections."""
        manager = DatabaseManager(":memory:")
        async with manager.get_connection() as conn:
            assert conn is not None
            await conn.execute("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_manager_initializes_schema(self):
        """Test manager initializes database schema."""
        manager = DatabaseManager(":memory:")
        await manager.initialize()
        
        # Check if core tables exist
        async with manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            assert "users" in table_names
            assert "tasks" in table_names  
            assert "attendance" in table_names
            assert "settings" in table_names
    
    @pytest.mark.asyncio
    async def test_manager_handles_concurrent_connections(self):
        """Test manager handles multiple concurrent connections."""
        manager = DatabaseManager(":memory:")
        await manager.initialize()
        
        # Create multiple concurrent connections
        connections = []
        for i in range(5):
            conn = await manager.get_connection().__aenter__()
            connections.append(conn)
        
        # All connections should work
        for i, conn in enumerate(connections):
            await conn.execute("SELECT ?", (i,))
        
        # Clean up
        for conn in connections:
            await manager.get_connection().__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_manager_connection_pooling(self):
        """Test connection pooling functionality."""
        manager = DatabaseManager(":memory:", pool_size=3)
        await manager.initialize()
        
        # Should maintain pool of connections
        assert manager.connection_pool is not None
        assert manager.pool_size == 3
    
    @pytest.mark.asyncio
    async def test_manager_cleanup(self):
        """Test manager properly cleans up resources."""
        manager = DatabaseManager(":memory:")
        await manager.initialize()
        
        # Should be able to close cleanly
        await manager.close()
        assert manager.connection_pool is None


class TestDatabaseOperations:
    """Test common database operations."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, temp_db_path, sample_user_data):
        """Test creating a user record."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        user_id = await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        assert user_id is not None
        assert isinstance(user_id, int)
        
        # Verify user was created
        user = await manager.get_user(sample_user_data["discord_id"])
        assert user is not None
        assert user["username"] == sample_user_data["username"]
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, temp_db_path):
        """Test getting user that doesn't exist."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        user = await manager.get_user(999999999)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user(self, temp_db_path, sample_user_data):
        """Test updating user information."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Update user
        await manager.update_user(
            discord_id=sample_user_data["discord_id"],
            display_name="Updated Name",
            is_admin=True
        )
        
        # Verify update
        user = await manager.get_user(sample_user_data["discord_id"])
        assert user["display_name"] == "Updated Name"
        assert user["is_admin"] is True
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, temp_db_path):
        """Test database error handling."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Try to create user with invalid data
        with pytest.raises(DatabaseError):
            await manager.create_user(
                discord_id="invalid_id",  # Should be integer
                username="test",
                display_name="test"
            )


class TestTaskOperations:
    """Test task management operations - TDD implementation."""
    
    @pytest.mark.asyncio
    async def test_create_task(self, temp_db_path, sample_user_data, sample_task_data):
        """Test creating a new task."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user first
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create task
        task_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title=sample_task_data["title"],
            description=sample_task_data["description"],
            priority=sample_task_data["priority"],
            due_date=sample_task_data.get("due_date")
        )
        
        assert task_id is not None
        assert isinstance(task_id, int)
        
        # Verify task was created
        task = await manager.get_task(task_id)
        assert task is not None
        assert task["title"] == sample_task_data["title"]
        assert task["user_id"] == sample_user_data["discord_id"]
        assert task["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, temp_db_path):
        """Test getting task that doesn't exist."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        task = await manager.get_task(999999)
        assert task is None
    
    @pytest.mark.asyncio
    async def test_update_task(self, temp_db_path, sample_user_data, sample_task_data):
        """Test updating task information."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user and task
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"], 
            display_name=sample_user_data["display_name"]
        )
        task_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title=sample_task_data["title"],
            description=sample_task_data["description"]
        )
        
        # Update task
        result = await manager.update_task(
            task_id=task_id,
            title="Updated Title",
            status="in_progress",
            priority="high"
        )
        assert result is True
        
        # Verify update
        task = await manager.get_task(task_id)
        assert task["title"] == "Updated Title"
        assert task["status"] == "in_progress"
        assert task["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_delete_task(self, temp_db_path, sample_user_data, sample_task_data):
        """Test deleting a task."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user and task
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        task_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title=sample_task_data["title"],
            description=sample_task_data["description"]
        )
        
        # Delete task
        result = await manager.delete_task(task_id)
        assert result is True
        
        # Verify deletion
        task = await manager.get_task(task_id)
        assert task is None
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, temp_db_path, sample_user_data):
        """Test listing all tasks for a user."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create multiple tasks
        task1_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title="Task 1",
            description="First task"
        )
        task2_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title="Task 2", 
            description="Second task",
            status="in_progress"
        )
        
        # List tasks
        tasks = await manager.list_tasks(sample_user_data["discord_id"])
        assert len(tasks) == 2
        
        task_titles = [task["title"] for task in tasks]
        assert "Task 1" in task_titles
        assert "Task 2" in task_titles
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, temp_db_path, sample_user_data):
        """Test listing tasks filtered by status."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create tasks with different statuses
        await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title="Pending Task",
            status="pending"
        )
        await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title="In Progress Task",
            status="in_progress"
        )
        await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title="Completed Task",
            status="completed"
        )
        
        # List only pending tasks
        pending_tasks = await manager.list_tasks_by_status(
            sample_user_data["discord_id"], "pending"
        )
        assert len(pending_tasks) == 1
        assert pending_tasks[0]["title"] == "Pending Task"
        
        # List only completed tasks
        completed_tasks = await manager.list_tasks_by_status(
            sample_user_data["discord_id"], "completed"
        )
        assert len(completed_tasks) == 1
        assert completed_tasks[0]["title"] == "Completed Task"
    
    @pytest.mark.asyncio
    async def test_complete_task(self, temp_db_path, sample_user_data, sample_task_data):
        """Test marking a task as completed."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user and task
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        task_id = await manager.create_task(
            user_id=sample_user_data["discord_id"],
            title=sample_task_data["title"],
            description=sample_task_data["description"]
        )
        
        # Complete task
        result = await manager.complete_task(task_id)
        assert result is True
        
        # Verify completion
        task = await manager.get_task(task_id)
        assert task["status"] == "completed"
        assert task["completed_at"] is not None


class TestAttendanceOperations:
    """Test attendance management operations - TDD implementation."""
    
    @pytest.mark.asyncio
    async def test_create_attendance_record(self, temp_db_path, sample_user_data, sample_attendance_data):
        """Test creating a new attendance record."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user first
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create attendance record
        record_id = await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date=sample_attendance_data["date"],
            check_in=sample_attendance_data["check_in"],
            check_out=sample_attendance_data.get("check_out"),
            work_hours=sample_attendance_data.get("work_hours", 0.0)
        )
        
        assert record_id is not None
        assert isinstance(record_id, int)
        
        # Verify record was created
        record = await manager.get_attendance_record(sample_user_data["discord_id"], sample_attendance_data["date"])
        assert record is not None
        assert record["user_id"] == sample_user_data["discord_id"]
        assert record["date"] == sample_attendance_data["date"]
    
    @pytest.mark.asyncio
    async def test_get_attendance_record_not_found(self, temp_db_path):
        """Test getting attendance record that doesn't exist."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        record = await manager.get_attendance_record(999999, "2024-01-01")
        assert record is None
    
    @pytest.mark.asyncio
    async def test_update_attendance_record(self, temp_db_path, sample_user_data, sample_attendance_data):
        """Test updating attendance record."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user and attendance record
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date=sample_attendance_data["date"],
            check_in=sample_attendance_data["check_in"]
        )
        
        # Update with check out time
        result = await manager.update_attendance_record(
            user_id=sample_user_data["discord_id"],
            date=sample_attendance_data["date"],
            check_out=sample_attendance_data["check_out"],
            work_hours=8.0
        )
        assert result is True
        
        # Verify update
        record = await manager.get_attendance_record(sample_user_data["discord_id"], sample_attendance_data["date"])
        assert record["check_out"] is not None
        assert record["work_hours"] == 8.0
    
    @pytest.mark.asyncio 
    async def test_list_attendance_records(self, temp_db_path, sample_user_data):
        """Test listing attendance records for a user."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create multiple attendance records
        from datetime import datetime
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date="2024-01-01",
            check_in=datetime(2024, 1, 1, 9, 0)
        )
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date="2024-01-02", 
            check_in=datetime(2024, 1, 2, 9, 0)
        )
        
        # List records
        records = await manager.list_attendance_records(sample_user_data["discord_id"])
        assert len(records) == 2
        
        dates = [record["date"] for record in records]
        assert "2024-01-01" in dates
        assert "2024-01-02" in dates
    
    @pytest.mark.asyncio
    async def test_get_attendance_by_date_range(self, temp_db_path, sample_user_data):
        """Test getting attendance records within date range."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create attendance records across different dates
        from datetime import datetime
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date="2024-01-01",
            check_in=datetime(2024, 1, 1, 9, 0)
        )
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date="2024-01-05",
            check_in=datetime(2024, 1, 5, 9, 0)
        )
        await manager.create_attendance_record(
            user_id=sample_user_data["discord_id"],
            date="2024-01-10",
            check_in=datetime(2024, 1, 10, 9, 0)
        )
        
        # Get records within date range
        records = await manager.get_attendance_by_date_range(
            sample_user_data["discord_id"], "2024-01-01", "2024-01-05"
        )
        assert len(records) == 2
        
        dates = [record["date"] for record in records]
        assert "2024-01-01" in dates
        assert "2024-01-05" in dates
        assert "2024-01-10" not in dates


class TestUserPreferencesOperations:
    """Test user preferences operations - TDD implementation."""
    
    @pytest.mark.asyncio
    async def test_create_user_preferences(self, temp_db_path, sample_user_data):
        """Test creating user preferences."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user first
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        
        # Create preferences
        result = await manager.create_user_preferences(
            user_id=sample_user_data["discord_id"],
            language="en",
            notification_enabled=False,
            daily_report_time="18:00"
        )
        assert result is True
        
        # Verify preferences
        prefs = await manager.get_user_preferences(sample_user_data["discord_id"])
        assert prefs is not None
        assert prefs["user_id"] == sample_user_data["discord_id"]
        assert prefs["language"] == "en"
        assert prefs["notification_enabled"] is False
        assert prefs["daily_report_time"] == "18:00"
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_not_found(self, temp_db_path):
        """Test getting preferences for user that doesn't exist."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        prefs = await manager.get_user_preferences(999999)
        assert prefs is None
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, temp_db_path, sample_user_data):
        """Test updating user preferences."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        # Create user and preferences
        await manager.create_user(
            discord_id=sample_user_data["discord_id"],
            username=sample_user_data["username"],
            display_name=sample_user_data["display_name"]
        )
        await manager.create_user_preferences(
            user_id=sample_user_data["discord_id"],
            language="ja",
            notification_enabled=True
        )
        
        # Update preferences
        result = await manager.update_user_preferences(
            user_id=sample_user_data["discord_id"],
            language="en",
            daily_report_time="19:00"
        )
        assert result is True
        
        # Verify update
        prefs = await manager.get_user_preferences(sample_user_data["discord_id"])
        assert prefs["language"] == "en"
        assert prefs["daily_report_time"] == "19:00"
        # notification_enabled should remain unchanged
        assert prefs["notification_enabled"] is True


class TestDatabaseMigrations:
    """Test database migration system."""
    
    @pytest.mark.asyncio
    async def test_migration_tracking(self, temp_db_path):
        """Test migration tracking table creation."""
        manager = DatabaseManager(temp_db_path)
        await manager.initialize()
        
        async with manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE name='schema_migrations'"
            )
            result = await cursor.fetchone()
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_migration_execution(self, temp_db_path):
        """Test executing database migrations."""
        manager = DatabaseManager(temp_db_path)
        
        # Should run initial migrations
        await manager.initialize()
        
        # Check schema version
        version = await manager.get_schema_version()
        assert version > 0
    
    @pytest.mark.asyncio
    async def test_migration_idempotency(self, temp_db_path):
        """Test migrations are idempotent."""
        manager = DatabaseManager(temp_db_path)
        
        # Run migrations twice
        await manager.initialize()
        version1 = await manager.get_schema_version()
        
        await manager.initialize()
        version2 = await manager.get_schema_version()
        
        # Should be same version
        assert version1 == version2