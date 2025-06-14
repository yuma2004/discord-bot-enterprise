"""
Integration tests for database operations - TDD approach
"""
import pytest
import tempfile
import os
from datetime import datetime

from src.core.database import DatabaseManager, DatabaseError


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    async def db_manager(self):
        """Create a test database manager with real SQLite connection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            manager = DatabaseManager(temp_path)
            await manager.initialize()
            yield manager
        finally:
            await manager.close()
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_user_workflow(self, db_manager):
        """Test complete user workflow."""
        # Create user
        user_id = await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User",
            is_admin=False,
            timezone="Asia/Tokyo"
        )
        assert user_id is not None
        
        # Get user
        user = await db_manager.get_user(123456789)
        assert user is not None
        assert user["discord_id"] == 123456789
        assert user["username"] == "testuser"
        assert user["display_name"] == "Test User"
        assert user["is_admin"] is False
        assert user["timezone"] == "Asia/Tokyo"
        
        # Update user
        success = await db_manager.update_user(
            discord_id=123456789,
            display_name="Updated Name",
            is_admin=True
        )
        assert success is True
        
        # Verify update
        updated_user = await db_manager.get_user(123456789)
        assert updated_user["display_name"] == "Updated Name"
        assert updated_user["is_admin"] is True
        assert updated_user["username"] == "testuser"  # Unchanged
        
        # List users
        users = await db_manager.list_users()
        assert len(users) == 1
        assert users[0]["discord_id"] == 123456789
    
    @pytest.mark.asyncio
    async def test_task_workflow(self, db_manager):
        """Test complete task workflow."""
        # Create user first
        await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User"
        )
        
        # Create task
        task_id = await db_manager.create_task(
            user_id=123456789,
            title="Integration Test Task",
            description="Test task for integration",
            priority="high",
            due_date=datetime(2024, 12, 31)
        )
        assert task_id is not None
        
        # Get task
        task = await db_manager.get_task(task_id)
        assert task is not None
        assert task["title"] == "Integration Test Task"
        assert task["description"] == "Test task for integration"
        assert task["priority"] == "high"
        assert task["status"] == "pending"
        assert task["user_id"] == 123456789
        
        # Update task
        success = await db_manager.update_task(
            task_id=task_id,
            title="Updated Task Title",
            status="in_progress",
            priority="medium"
        )
        assert success is True
        
        # Verify update
        updated_task = await db_manager.get_task(task_id)
        assert updated_task["title"] == "Updated Task Title"
        assert updated_task["status"] == "in_progress"
        assert updated_task["priority"] == "medium"
        assert updated_task["description"] == "Test task for integration"  # Unchanged
        
        # List tasks
        tasks = await db_manager.list_tasks(123456789)
        assert len(tasks) == 1
        assert tasks[0]["id"] == task_id
        
        # List tasks by status
        pending_tasks = await db_manager.list_tasks_by_status(123456789, "pending")
        assert len(pending_tasks) == 0
        
        in_progress_tasks = await db_manager.list_tasks_by_status(123456789, "in_progress")
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0]["id"] == task_id
        
        # Complete task
        success = await db_manager.complete_task(task_id)
        assert success is True
        
        # Verify completion
        completed_task = await db_manager.get_task(task_id)
        assert completed_task["status"] == "completed"
        assert completed_task["completed_at"] is not None
        
        # Delete task
        success = await db_manager.delete_task(task_id)
        assert success is True
        
        # Verify deletion
        deleted_task = await db_manager.get_task(task_id)
        assert deleted_task is None
    
    @pytest.mark.asyncio
    async def test_attendance_workflow(self, db_manager):
        """Test complete attendance workflow."""
        # Create user first
        await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User"
        )
        
        # Create attendance record
        record_id = await db_manager.create_attendance_record(
            user_id=123456789,
            date="2024-01-15",
            check_in=datetime(2024, 1, 15, 9, 0),
            work_hours=0.0
        )
        assert record_id is not None
        
        # Get attendance record
        record = await db_manager.get_attendance_record(123456789, "2024-01-15")
        assert record is not None
        assert record["user_id"] == 123456789
        assert record["date"] == "2024-01-15"
        assert record["check_out"] is None
        assert record["work_hours"] == 0.0
        
        # Update attendance record (check out)
        success = await db_manager.update_attendance_record(
            user_id=123456789,
            date="2024-01-15",
            check_out=datetime(2024, 1, 15, 18, 0),
            work_hours=8.0,
            overtime_hours=1.0
        )
        assert success is True
        
        # Verify update
        updated_record = await db_manager.get_attendance_record(123456789, "2024-01-15")
        assert updated_record["check_out"] is not None
        assert updated_record["work_hours"] == 8.0
        assert updated_record["overtime_hours"] == 1.0
        
        # Create more records for testing
        await db_manager.create_attendance_record(
            user_id=123456789,
            date="2024-01-16",
            check_in=datetime(2024, 1, 16, 9, 0)
        )
        await db_manager.create_attendance_record(
            user_id=123456789,
            date="2024-01-20",
            check_in=datetime(2024, 1, 20, 9, 0)
        )
        
        # List attendance records
        records = await db_manager.list_attendance_records(123456789)
        assert len(records) == 3
        
        # Get attendance by date range
        range_records = await db_manager.get_attendance_by_date_range(
            123456789, "2024-01-15", "2024-01-16"
        )
        assert len(range_records) == 2
        
        dates = [record["date"] for record in range_records]
        assert "2024-01-15" in dates
        assert "2024-01-16" in dates
        assert "2024-01-20" not in dates
    
    @pytest.mark.asyncio
    async def test_user_preferences_workflow(self, db_manager):
        """Test complete user preferences workflow."""
        # Create user first
        await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User"
        )
        
        # Create user preferences
        success = await db_manager.create_user_preferences(
            user_id=123456789,
            language="en",
            notification_enabled=False,
            daily_report_time="18:00"
        )
        assert success is True
        
        # Get user preferences
        prefs = await db_manager.get_user_preferences(123456789)
        assert prefs is not None
        assert prefs["user_id"] == 123456789
        assert prefs["language"] == "en"
        assert prefs["notification_enabled"] is False
        assert prefs["daily_report_time"] == "18:00"
        
        # Update user preferences
        success = await db_manager.update_user_preferences(
            user_id=123456789,
            language="ja",
            daily_report_time="19:00"
            # notification_enabled should remain unchanged
        )
        assert success is True
        
        # Verify update
        updated_prefs = await db_manager.get_user_preferences(123456789)
        assert updated_prefs["language"] == "ja"
        assert updated_prefs["daily_report_time"] == "19:00"
        assert updated_prefs["notification_enabled"] is False  # Unchanged
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, db_manager):
        """Test concurrent database operations."""
        import asyncio
        
        # Create user first
        await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User"
        )
        
        # Create multiple tasks concurrently
        async def create_task(i):
            return await db_manager.create_task(
                user_id=123456789,
                title=f"Concurrent Task {i}",
                description=f"Task {i} description"
            )
        
        task_creation_tasks = [create_task(i) for i in range(10)]
        task_ids = await asyncio.gather(*task_creation_tasks)
        
        # All tasks should be created successfully
        assert len(task_ids) == 10
        assert all(task_id is not None for task_id in task_ids)
        
        # Verify all tasks exist
        tasks = await db_manager.list_tasks(123456789)
        assert len(tasks) == 10
        
        # Update tasks concurrently
        async def update_task(task_id, status):
            return await db_manager.update_task(task_id, status=status)
        
        update_tasks = [
            update_task(task_ids[i], "in_progress" if i % 2 == 0 else "completed")
            for i in range(10)
        ]
        results = await asyncio.gather(*update_tasks)
        
        # All updates should succeed
        assert all(result is True for result in results)
        
        # Verify updates
        in_progress_tasks = await db_manager.list_tasks_by_status(123456789, "in_progress")
        completed_tasks = await db_manager.list_tasks_by_status(123456789, "completed")
        
        assert len(in_progress_tasks) == 5
        assert len(completed_tasks) == 5
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_manager):
        """Test foreign key constraints are enforced."""
        # Try to create task without user - should fail
        with pytest.raises(DatabaseError):
            await db_manager.create_task(
                user_id=999999999,  # Non-existent user
                title="Invalid Task",
                description="Should fail"
            )
        
        # Try to create attendance for non-existent user - should fail
        with pytest.raises(DatabaseError):
            await db_manager.create_attendance_record(
                user_id=999999999,  # Non-existent user
                date="2024-01-15",
                check_in=datetime(2024, 1, 15, 9, 0)
            )
        
        # Try to create preferences for non-existent user - should fail
        with pytest.raises(DatabaseError):
            await db_manager.create_user_preferences(
                user_id=999999999,  # Non-existent user
                language="en"
            )
    
    @pytest.mark.asyncio
    async def test_schema_migrations(self, db_manager):
        """Test schema migration system."""
        # Check current schema version
        version = await db_manager.get_schema_version()
        assert version > 0
        
        # Verify all expected tables exist
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            expected_tables = [
                "users", "tasks", "attendance", "settings", 
                "user_preferences", "schema_migrations"
            ]
            
            for table in expected_tables:
                assert table in table_names
    
    @pytest.mark.asyncio
    async def test_unique_constraints(self, db_manager):
        """Test unique constraints are enforced."""
        # Create user
        await db_manager.create_user(
            discord_id=123456789,
            username="testuser",
            display_name="Test User"
        )
        
        # Try to create another user with same discord_id - should fail
        with pytest.raises(DatabaseError):
            await db_manager.create_user(
                discord_id=123456789,  # Duplicate
                username="different_username",
                display_name="Different User"
            )
        
        # Create attendance record
        await db_manager.create_attendance_record(
            user_id=123456789,
            date="2024-01-15",
            check_in=datetime(2024, 1, 15, 9, 0)
        )
        
        # Try to create another attendance record for same user and date - should fail
        with pytest.raises(DatabaseError):
            await db_manager.create_attendance_record(
                user_id=123456789,
                date="2024-01-15",  # Duplicate date for same user
                check_in=datetime(2024, 1, 15, 10, 0)
            )