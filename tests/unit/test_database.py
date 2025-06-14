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