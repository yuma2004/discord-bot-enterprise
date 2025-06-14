"""
PostgreSQL database implementation for production
"""
import asyncio
import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime
import json
from urllib.parse import urlparse

from src.core.logging import get_logger


class PostgreSQLError(Exception):
    """PostgreSQL specific error."""
    pass


class PostgreSQLConnection:
    """Async PostgreSQL connection wrapper."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._connection: Optional[asyncpg.Connection] = None
        self.logger = get_logger(__name__)
    
    async def __aenter__(self) -> 'PostgreSQLConnection':
        """Enter async context manager."""
        try:
            self._connection = await asyncpg.connect(self.database_url)
            return self
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise PostgreSQLError(f"Connection failed: {e}") from e
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, query: str, *parameters) -> str:
        """Execute SQL query with error handling."""
        if not self._connection:
            raise PostgreSQLError("No active database connection")
        
        try:
            return await self._connection.execute(query, *parameters)
        except Exception as e:
            self.logger.error(f"PostgreSQL query failed: {e}")
            raise PostgreSQLError(f"Database query failed: {e}") from e
    
    async def fetch(self, query: str, *parameters) -> List[asyncpg.Record]:
        """Fetch multiple rows."""
        if not self._connection:
            raise PostgreSQLError("No active database connection")
        
        try:
            return await self._connection.fetch(query, *parameters)
        except Exception as e:
            self.logger.error(f"PostgreSQL fetch failed: {e}")
            raise PostgreSQLError(f"Database fetch failed: {e}") from e
    
    async def fetchrow(self, query: str, *parameters) -> Optional[asyncpg.Record]:
        """Fetch single row."""
        if not self._connection:
            raise PostgreSQLError("No active database connection")
        
        try:
            return await self._connection.fetchrow(query, *parameters)
        except Exception as e:
            self.logger.error(f"PostgreSQL fetchrow failed: {e}")
            raise PostgreSQLError(f"Database fetchrow failed: {e}") from e
    
    async def fetchval(self, query: str, *parameters) -> Any:
        """Fetch single value."""
        if not self._connection:
            raise PostgreSQLError("No active database connection")
        
        try:
            return await self._connection.fetchval(query, *parameters)
        except Exception as e:
            self.logger.error(f"PostgreSQL fetchval failed: {e}")
            raise PostgreSQLError(f"Database fetchval failed: {e}") from e


class PostgreSQLManager:
    """PostgreSQL database manager with connection pooling."""
    
    def __init__(self, database_url: str, pool_size: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self.connection_pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        self.logger = get_logger(__name__)
    
    async def initialize(self) -> None:
        """Initialize database connection pool and schema."""
        if self._initialized:
            return
        
        try:
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=self.pool_size,
                command_timeout=60
            )
            
            # Run migrations
            await self._run_migrations()
            self._initialized = True
            self.logger.info("PostgreSQL initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise PostgreSQLError(f"Initialization failed: {e}") from e
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[PostgreSQLConnection, None]:
        """Get connection from pool."""
        if not self._initialized:
            await self.initialize()
        
        if not self.connection_pool:
            raise PostgreSQLError("Connection pool not initialized")
        
        async with self.connection_pool.acquire() as conn:
            wrapper = PostgreSQLConnection.__new__(PostgreSQLConnection)
            wrapper.database_url = self.database_url
            wrapper._connection = conn
            wrapper.logger = self.logger
            yield wrapper
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            self._initialized = False
            self.logger.info("PostgreSQL connection pool closed")
    
    async def _run_migrations(self) -> None:
        """Run database migrations for PostgreSQL."""
        if not self.connection_pool:
            raise PostgreSQLError("Connection pool not initialized")
        
        async with self.connection_pool.acquire() as conn:
            # Create schema migrations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check current schema version
            current_version = await conn.fetchval(
                "SELECT MAX(version) FROM schema_migrations"
            ) or 0
            
            # Apply migrations
            migrations = self._get_postgresql_migrations()
            for version, migration_sql in migrations.items():
                if version > current_version:
                    await self._apply_migration(conn, version, migration_sql)
    
    def _get_postgresql_migrations(self) -> Dict[int, str]:
        """Get PostgreSQL-specific migrations."""
        return {
            1: """
                -- Core user table
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    timezone VARCHAR(50) DEFAULT 'Asia/Tokyo',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Tasks table
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
                    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
                    due_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (discord_id)
                );
                
                -- Attendance table  
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    check_in TIMESTAMP,
                    check_out TIMESTAMP,
                    break_start TIMESTAMP,
                    break_end TIMESTAMP,
                    work_hours DECIMAL(4,2) DEFAULT 0.0,
                    overtime_hours DECIMAL(4,2) DEFAULT 0.0,
                    work_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (discord_id),
                    UNIQUE(user_id, work_date)
                );
                
                -- Settings table
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id);
                CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(work_date);
            """,
            
            2: """
                -- Add task completion tracking
                ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
                
                -- Add user preferences
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY,
                    language VARCHAR(10) DEFAULT 'ja',
                    notification_enabled BOOLEAN DEFAULT TRUE,
                    daily_report_time TIME DEFAULT '17:00',
                    FOREIGN KEY (user_id) REFERENCES users (discord_id)
                );
                
                -- Add audit log table
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action VARCHAR(100) NOT NULL,
                    resource_type VARCHAR(50),
                    resource_id VARCHAR(100),
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (discord_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
            """
        }
    
    async def _apply_migration(self, conn: asyncpg.Connection, version: int, migration_sql: str) -> None:
        """Apply a single migration."""
        try:
            async with conn.transaction():
                # Split and execute statements
                statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
                for statement in statements:
                    await conn.execute(statement)
                
                # Record migration
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    version
                )
                
                self.logger.info(f"Applied PostgreSQL migration version {version}")
                
        except Exception as e:
            self.logger.error(f"PostgreSQL migration {version} failed: {e}")
            raise PostgreSQLError(f"Migration {version} failed: {e}") from e
    
    async def get_schema_version(self) -> int:
        """Get current schema version."""
        if not self.connection_pool:
            return 0
        
        async with self.connection_pool.acquire() as conn:
            version = await conn.fetchval(
                "SELECT MAX(version) FROM schema_migrations"
            )
            return version or 0
    
    # User operations
    async def create_user(self, discord_id: int, username: str, display_name: str, **kwargs) -> int:
        """Create a new user."""
        if not self.connection_pool:
            raise PostgreSQLError("Connection pool not initialized")
        
        try:
            async with self.connection_pool.acquire() as conn:
                user_id = await conn.fetchval("""
                    INSERT INTO users (discord_id, username, display_name, is_admin, timezone)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, 
                    discord_id,
                    username, 
                    display_name,
                    kwargs.get('is_admin', False),
                    kwargs.get('timezone', 'Asia/Tokyo')
                )
                return user_id
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            raise PostgreSQLError(f"Failed to create user: {e}") from e
    
    async def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Discord ID."""
        if not self.connection_pool:
            return None
        
        async with self.connection_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1",
                discord_id
            )
            return dict(record) if record else None
    
    async def update_user(self, discord_id: int, **kwargs) -> bool:
        """Update user information."""
        if not kwargs or not self.connection_pool:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        param_index = 1
        
        for key, value in kwargs.items():
            if key in ['username', 'display_name', 'is_admin', 'timezone']:
                set_clauses.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1
        
        if not set_clauses:
            return False
        
        set_clauses.append(f"updated_at = CURRENT_TIMESTAMP")
        values.append(discord_id)
        
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE discord_id = ${param_index} RETURNING id"
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchval(query, *values)
            return result is not None
    
    async def list_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        if not self.connection_pool:
            return []
        
        async with self.connection_pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM users ORDER BY created_at")
            return [dict(record) for record in records]