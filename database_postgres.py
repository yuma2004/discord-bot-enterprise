import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime, date, timedelta
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PostgreSQLManager:
    """PostgreSQL データベース管理クラス（Supabase対応）"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL環境変数が設定されていません")
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        connection = None
        try:
            connection = psycopg2.connect(self.database_url)
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"データベースエラー: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def initialize_database(self):
        """データベースとテーブルの初期化"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # usersテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        discord_id VARCHAR(20) UNIQUE NOT NULL,
                        username VARCHAR(100) NOT NULL,
                        display_name VARCHAR(100),
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # daily_reportsテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_reports (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        report_date DATE NOT NULL,
                        content TEXT NOT NULL,
                        mood VARCHAR(10) DEFAULT 'normal',
                        tasks_completed INTEGER DEFAULT 0,
                        challenges TEXT,
                        next_day_plan TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, report_date)
                    )
                ''')
                
                # tasksテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        status VARCHAR(20) DEFAULT 'pending',
                        priority VARCHAR(10) DEFAULT 'medium',
                        due_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # attendanceテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        work_date DATE NOT NULL,
                        clock_in_time TIMESTAMP,
                        clock_out_time TIMESTAMP,
                        break_start_time TIMESTAMP,
                        break_end_time TIMESTAMP,
                        total_break_minutes INTEGER DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'absent',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, work_date)
                    )
                ''')
                
                # settingsテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                logger.info("PostgreSQLデータベースとテーブルの初期化が完了しました")
                
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise

class PostgreSQLUserRepository:
    """PostgreSQL用ユーザーリポジトリ"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db_manager = db_manager
    
    def create_user(self, discord_id: str, username: str, display_name: str = None) -> Optional[int]:
        """ユーザーを作成"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (discord_id, username, display_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (discord_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        display_name = EXCLUDED.display_name
                    RETURNING id
                ''', (discord_id, username, display_name))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"ユーザー作成エラー: {e}")
            return None
    
    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Discord IDでユーザーを取得"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT * FROM users WHERE discord_id = %s', (discord_id,))
                return dict(cursor.fetchone()) if cursor.fetchone() else None
        except Exception as e:
            logger.error(f"ユーザー取得エラー: {e}")
            return None

# Supabaseを使用する場合の設定例
def get_supabase_config():
    """Supabase設定を返す"""
    return {
        'host': os.getenv('SUPABASE_HOST'),
        'port': os.getenv('SUPABASE_PORT', '5432'),
        'database': os.getenv('SUPABASE_DB'),
        'user': os.getenv('SUPABASE_USER'),
        'password': os.getenv('SUPABASE_PASSWORD'),
    }

# グローバルインスタンス
postgres_db_manager = PostgreSQLManager()
postgres_user_repo = PostgreSQLUserRepository(postgres_db_manager) 