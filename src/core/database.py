"""
Database abstraction layer - Clean TDD implementation with PostgreSQL support
"""
import asyncio
import aiosqlite
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime
import json
from pathlib import Path
import os

# Import PostgreSQL support if available
try:
    from .database_postgres import PostgreSQLManager
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseError(Exception):
    """Custom database error."""
    pass


class DatabaseConnection:
    """Async database connection wrapper."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def __aenter__(self) -> 'DatabaseConnection':
        """Enter async context manager."""
        self._connection = await aiosqlite.connect(self.database_url)
        self._connection.row_factory = aiosqlite.Row
        # Enable foreign keys and WAL mode for better performance
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA journal_mode = WAL")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, query: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """Execute SQL query with error handling."""
        if not self._connection:
            raise DatabaseError("No active database connection")
        
        try:
            return await self._connection.execute(query, parameters)
        except Exception as e:
            raise DatabaseError(f"Database query failed: {e}") from e
    
    async def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            await self._connection.commit()
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection:
            await self._connection.rollback()


class DatabaseManager:
    """Main database manager with connection pooling."""
    
    def __init__(self, database_url: str, pool_size: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self.connection_pool: Optional[asyncio.Queue] = None
        self._initialized = False
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize database schema and connection pool."""
        if self._initialized:
            return
        
        # Create connection pool
        self.connection_pool = asyncio.Queue(maxsize=self.pool_size)
        
        # Run initial migration
        await self._run_migrations()
        self._initialized = True
        self.logger.info("Database initialized successfully")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[DatabaseConnection, None]:
        """Get database connection from pool."""
        if not self._initialized:
            await self.initialize()
        
        # For now, create new connections (can be optimized with actual pooling)
        async with DatabaseConnection(self.database_url) as conn:
            yield conn
    
    async def close(self) -> None:
        """Close all connections and cleanup."""
        self.connection_pool = None
        self._initialized = False
        self.logger.info("Database connections closed")
    
    async def _run_migrations(self) -> None:
        """Run database migrations."""
        async with DatabaseConnection(self.database_url) as conn:
            # Create schema migrations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check current schema version
            cursor = await conn.execute(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            result = await cursor.fetchone()
            current_version = result[0] if result[0] else 0
            
            # Apply migrations
            migrations = self._get_migrations()
            for version, migration_sql in migrations.items():
                if version > current_version:
                    await self._apply_migration(conn, version, migration_sql)
            
            await conn.commit()
    
    def _get_migrations(self) -> Dict[int, str]:
        """Get all database migrations."""
        return {
            1: """
                -- Core user table
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id INTEGER UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    timezone TEXT DEFAULT 'Asia/Tokyo',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Tasks table
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
                    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
                    due_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (discord_id)
                );
                
                -- Attendance table  
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    check_in TIMESTAMP NOT NULL,
                    check_out TIMESTAMP,
                    break_start TIMESTAMP,
                    break_end TIMESTAMP,
                    work_hours REAL DEFAULT 0.0,
                    overtime_hours REAL DEFAULT 0.0,
                    date TEXT NOT NULL, -- YYYY-MM-DD format
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (discord_id),
                    UNIQUE(user_id, date)
                );
                
                -- Settings table
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id);
                CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
            """,
            
            2: """
                -- Add task completion tracking
                ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMP;
                
                -- Add user preferences
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ja',
                    notification_enabled BOOLEAN DEFAULT TRUE,
                    daily_report_time TEXT DEFAULT '17:00',
                    FOREIGN KEY (user_id) REFERENCES users (discord_id)
                );
            """
        }
    
    async def _apply_migration(self, conn: DatabaseConnection, version: int, migration_sql: str) -> None:
        """Apply a single migration."""
        try:
            # Execute migration
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement:
                    await conn.execute(statement)
            
            # Record migration
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,)
            )
            
            self.logger.info(f"Applied migration version {version}")
            
        except Exception as e:
            await conn.rollback()
            raise DatabaseError(f"Migration {version} failed: {e}") from e
    
    async def get_schema_version(self) -> int:
        """Get current schema version."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            result = await cursor.fetchone()
            return result[0] if result[0] else 0
    
    # User operations
    async def create_user(self, discord_id: int, username: str, display_name: str, **kwargs) -> int:
        """Create a new user."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    INSERT INTO users (discord_id, username, display_name, is_admin, timezone)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    discord_id,
                    username, 
                    display_name,
                    kwargs.get('is_admin', False),
                    kwargs.get('timezone', 'Asia/Tokyo')
                ))
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            raise DatabaseError(f"Failed to create user: {e}") from e
    
    async def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Discord ID."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    
    async def update_user(self, discord_id: int, **kwargs) -> bool:
        """Update user information."""
        if not kwargs:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['username', 'display_name', 'is_admin', 'timezone']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(discord_id)
        
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE discord_id = ?"
        
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, values)
            await conn.commit()
            return cursor.rowcount > 0
    
    async def list_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        async with self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM users ORDER BY created_at")
            results = await cursor.fetchall()
            return [dict(row) for row in results]
    
    # Task operations
    async def create_task(self, user_id: int, title: str, description: str = None, 
                         priority: str = "medium", status: str = "pending", 
                         due_date: Optional[datetime] = None) -> int:
        """Create a new task."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    INSERT INTO tasks (user_id, title, description, priority, status, due_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, title, description, priority, status, due_date))
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            raise DatabaseError(f"Failed to create task: {e}") from e
    
    async def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    
    async def update_task(self, task_id: int, **kwargs) -> bool:
        """Update task information."""
        if not kwargs:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['title', 'description', 'status', 'priority', 'due_date', 'completed_at']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, values)
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to update task: {e}") from e
    
    async def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete task: {e}") from e
    
    async def list_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all tasks for a user."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            results = await cursor.fetchall()
            return [dict(row) for row in results]
    
    async def list_tasks_by_status(self, user_id: int, status: str) -> List[Dict[str, Any]]:
        """Get tasks filtered by status."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (user_id, status)
            )
            results = await cursor.fetchall()
            return [dict(row) for row in results]
    
    async def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    UPDATE tasks 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (task_id,))
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to complete task: {e}") from e
    
    # Attendance operations
    async def create_attendance_record(self, user_id: int, date: str, check_in: datetime,
                                     check_out: Optional[datetime] = None,
                                     break_start: Optional[datetime] = None,
                                     break_end: Optional[datetime] = None,
                                     work_hours: float = 0.0,
                                     overtime_hours: float = 0.0) -> int:
        """Create a new attendance record."""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    INSERT INTO attendance (user_id, date, check_in, check_out, break_start, break_end, work_hours, overtime_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, date, check_in, check_out, break_start, break_end, work_hours, overtime_hours))
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            raise DatabaseError(f"Failed to create attendance record: {e}") from e
    
    async def get_attendance_record(self, user_id: int, date: str) -> Optional[Dict[str, Any]]:
        """Get attendance record by user ID and date."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM attendance WHERE user_id = ? AND date = ?",
                (user_id, date)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    
    async def update_attendance_record(self, user_id: int, date: str, **kwargs) -> bool:
        """Update attendance record."""
        if not kwargs:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['check_out', 'break_start', 'break_end', 'work_hours', 'overtime_hours']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        values.extend([user_id, date])
        query = f"UPDATE attendance SET {', '.join(set_clauses)} WHERE user_id = ? AND date = ?"
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, values)
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to update attendance record: {e}") from e
    
    async def list_attendance_records(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all attendance records for a user."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM attendance WHERE user_id = ? ORDER BY date DESC",
                (user_id,)
            )
            results = await cursor.fetchall()
            return [dict(row) for row in results]
    
    async def get_attendance_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get attendance records within date range."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM attendance WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date",
                (user_id, start_date, end_date)
            )
            results = await cursor.fetchall()
            return [dict(row) for row in results]
    
    # User preferences operations
    async def create_user_preferences(self, user_id: int, language: str = "ja",
                                    notification_enabled: bool = True,
                                    daily_report_time: str = "17:00") -> bool:
        """Create user preferences."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO user_preferences (user_id, language, notification_enabled, daily_report_time)
                    VALUES (?, ?, ?, ?)
                """, (user_id, language, notification_enabled, daily_report_time))
                await conn.commit()
                return True
        except Exception as e:
            raise DatabaseError(f"Failed to create user preferences: {e}") from e
    
    async def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences by user ID."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    
    async def update_user_preferences(self, user_id: int, **kwargs) -> bool:
        """Update user preferences."""
        if not kwargs:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['language', 'notification_enabled', 'daily_report_time']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        values.append(user_id)
        query = f"UPDATE user_preferences SET {', '.join(set_clauses)} WHERE user_id = ?"
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, values)
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to update user preferences: {e}") from e


# Global database manager instance
_db_manager: Optional[Union[DatabaseManager, 'PostgreSQLManager']] = None


def get_database_manager(database_url: str = ":memory:") -> Union[DatabaseManager, 'PostgreSQLManager']:
    """Get global database manager instance with automatic PostgreSQL/SQLite selection."""
    global _db_manager
    if _db_manager is None:
        # Determine database type from URL
        if database_url and ('postgresql://' in database_url or 'postgres://' in database_url):
            if POSTGRES_AVAILABLE:
                from .database_postgres import PostgreSQLManager
                _db_manager = PostgreSQLManager(database_url)
                logging.getLogger(__name__).info("Using PostgreSQL database manager")
            else:
                logging.getLogger(__name__).warning("PostgreSQL requested but asyncpg not available, falling back to SQLite")
                _db_manager = DatabaseManager(":memory:")
        else:
            _db_manager = DatabaseManager(database_url)
            logging.getLogger(__name__).info("Using SQLite database manager")
    return _db_manager


def set_database_manager(manager: Union[DatabaseManager, 'PostgreSQLManager']) -> None:
    """Set global database manager instance."""
    global _db_manager
    _db_manager = manager


def is_postgresql_url(database_url: str) -> bool:
    """Check if database URL is for PostgreSQL."""
    return 'postgresql://' in database_url or 'postgres://' in database_url