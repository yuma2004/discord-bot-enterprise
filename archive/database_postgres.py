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
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"ユーザー取得エラー: {e}")
            return None
    
    def get_or_create_user(self, discord_id: str, username: str, display_name: str = None) -> Dict[str, Any]:
        """ユーザーを取得、存在しない場合は作成"""
        user = self.get_user_by_discord_id(discord_id)
        if not user:
            user_id = self.create_user(discord_id, username, display_name)
            user = self.get_user_by_discord_id(discord_id)
        return user
    
    def update_user(self, discord_id: str, **kwargs) -> bool:
        """ユーザー情報を更新"""
        if not kwargs:
            return False
        
        set_clause = ', '.join([f"{key} = %s" for key in kwargs.keys()])
        values = list(kwargs.values()) + [discord_id]
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE users SET {set_clause}, created_at = CURRENT_TIMESTAMP
                    WHERE discord_id = %s
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"ユーザー更新エラー: {e}")
            return False

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

class PostgreSQLDailyReportRepository:
    """PostgreSQL用日報リポジトリ"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db_manager = db_manager
    
    def create_daily_report(self, user_id: int, report_date: str, content: str, 
                          mood: str = 'normal', challenges: str = '', next_day_plan: str = '') -> Optional[int]:
        """日報を作成"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO daily_reports (user_id, report_date, content, mood, challenges, next_day_plan)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, report_date) DO UPDATE SET
                        content = EXCLUDED.content,
                        mood = EXCLUDED.mood,
                        challenges = EXCLUDED.challenges,
                        next_day_plan = EXCLUDED.next_day_plan
                    RETURNING id
                ''', (user_id, report_date, content, mood, challenges, next_day_plan))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"日報作成エラー: {e}")
            return None
    
    def get_daily_report(self, user_id: int, report_date: str) -> Optional[Dict[str, Any]]:
        """指定日の日報を取得"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    SELECT * FROM daily_reports 
                    WHERE user_id = %s AND report_date = %s
                ''', (user_id, report_date))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"日報取得エラー: {e}")
            return None
    
    def get_users_without_report(self, report_date: str) -> List[Dict[str, Any]]:
        """指定日に日報を提出していないユーザーを取得"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    SELECT u.* FROM users u
                    LEFT JOIN daily_reports dr ON u.id = dr.user_id AND dr.report_date = %s
                    WHERE dr.id IS NULL
                ''', (report_date,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"未提出ユーザー取得エラー: {e}")
            return []

class PostgreSQLTaskRepository:
    """PostgreSQL用タスクリポジトリ"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db_manager = db_manager
    
    def create_task(self, user_id: int, title: str, description: str = '', 
                   priority: str = 'medium', due_date: str = None) -> Optional[int]:
        """タスクを作成"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks (user_id, title, description, priority, due_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (user_id, title, description, priority, due_date))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"タスク作成エラー: {e}")
            return None
    
    def get_user_tasks(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """ユーザーのタスクを取得"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                if status:
                    cursor.execute('SELECT * FROM tasks WHERE user_id = %s AND status = %s ORDER BY created_at DESC', 
                                 (user_id, status))
                else:
                    cursor.execute('SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC', (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"タスク取得エラー: {e}")
            return []
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """タスクのステータスを更新"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tasks 
                    SET status = %s, completed_at = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END
                    WHERE id = %s
                ''', (status, status, task_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"タスクステータス更新エラー: {e}")
            return False
    
    def delete_task(self, task_id: int) -> bool:
        """タスクを削除"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"タスク削除エラー: {e}")
            return False

class PostgreSQLAttendanceRepository:
    """PostgreSQL用出退勤リポジトリ"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db_manager = db_manager
    
    def clock_in(self, user_id: int, work_date: str = None) -> bool:
        """出勤記録"""
        if not work_date:
            work_date = date.today().isoformat()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO attendance (user_id, work_date, clock_in_time, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, work_date) DO UPDATE SET
                        clock_in_time = EXCLUDED.clock_in_time,
                        status = EXCLUDED.status
                ''', (user_id, work_date, datetime.now(), 'present'))
                return True
        except Exception as e:
            logger.error(f"出勤記録エラー: {e}")
            return False
    
    def clock_out(self, user_id: int, work_date: str = None) -> bool:
        """退勤記録"""
        if not work_date:
            work_date = date.today().isoformat()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE attendance 
                    SET clock_out_time = %s, status = %s
                    WHERE user_id = %s AND work_date = %s
                ''', (datetime.now(), 'absent', user_id, work_date))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"退勤記録エラー: {e}")
            return False
    
    def start_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩開始記録"""
        if not work_date:
            work_date = date.today().isoformat()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE attendance 
                    SET break_start_time = %s, status = %s
                    WHERE user_id = %s AND work_date = %s
                ''', (datetime.now(), 'on_break', user_id, work_date))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"休憩開始記録エラー: {e}")
            return False
    
    def end_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩終了記録"""
        if not work_date:
            work_date = date.today().isoformat()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE attendance 
                    SET break_end_time = %s, status = %s,
                        total_break_minutes = COALESCE(total_break_minutes, 0) + 
                        EXTRACT(EPOCH FROM (%s - break_start_time))/60
                    WHERE user_id = %s AND work_date = %s
                ''', (datetime.now(), 'present', datetime.now(), user_id, work_date))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"休憩終了記録エラー: {e}")
            return False
    
    def get_today_attendance(self, user_id: int, work_date: str = None) -> Optional[Dict[str, Any]]:
        """今日の出退勤記録を取得"""
        if not work_date:
            work_date = date.today().isoformat()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    SELECT * FROM attendance 
                    WHERE user_id = %s AND work_date = %s
                ''', (user_id, work_date))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"出退勤記録取得エラー: {e}")
            return None
    
    def get_all_users_status(self) -> List[Dict[str, Any]]:
        """全ユーザーの今日の在席状況を取得"""
        today = date.today().isoformat()
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    SELECT u.username, u.display_name, a.status, a.clock_in_time, a.clock_out_time
                    FROM users u
                    LEFT JOIN attendance a ON u.id = a.user_id AND a.work_date = %s
                    ORDER BY u.username
                ''', (today,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"全ユーザー状況取得エラー: {e}")
            return []

# グローバルインスタンス
db_manager = PostgreSQLManager()
user_repo = PostgreSQLUserRepository(db_manager)
daily_report_repo = PostgreSQLDailyReportRepository(db_manager)
task_repo = PostgreSQLTaskRepository(db_manager)
attendance_repo = PostgreSQLAttendanceRepository(db_manager) 