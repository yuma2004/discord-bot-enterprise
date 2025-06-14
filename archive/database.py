import sqlite3
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import os
from config import Config
from bot.utils.datetime_utils import (
    now_jst, today_jst, ensure_jst, format_time_only,
    calculate_work_hours, calculate_overtime_hours,
    adapt_datetime_for_sqlite, convert_datetime_from_sqlite
)
from bot.utils.database_utils import (
    handle_database_error, retry_on_lock, transaction,
    safe_execute, fetch_one_as_dict, fetch_all_as_dict,
    validate_required_fields, sanitize_string, build_update_query,
    log_query_performance, DatabaseError, RecordNotFoundError, DuplicateRecordError
)

logger = logging.getLogger(__name__)

# カスタムアダプターとコンバーターを登録
sqlite3.register_adapter(datetime, adapt_datetime_for_sqlite)
sqlite3.register_converter("datetime", convert_datetime_from_sqlite)


class DatabaseManager:
    """データベース操作管理クラス"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_URL
        self.init_database()
    
    @retry_on_lock()
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,  # PARSE_COLNAMESを削除してタイムスタンプエラーを回避
            timeout=30.0  # タイムアウトを30秒に設定
        )
        conn.row_factory = sqlite3.Row  # 辞書形式でのアクセスを可能にする
        return conn
    
    @handle_database_error
    def init_database(self):
        """データベースとテーブルの初期化"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # ユーザーテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    email TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 日報テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    report_date DATE NOT NULL,
                    today_tasks TEXT,
                    tomorrow_tasks TEXT,
                    obstacles TEXT,
                    comments TEXT,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, report_date)
                )
            ''')
            
            # タスクテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT CHECK(priority IN ('高', '中', '低')) DEFAULT '中',
                    status TEXT CHECK(status IN ('未着手', '進行中', '完了', '中断')) DEFAULT '未着手',
                    due_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 出退勤テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    work_date DATE NOT NULL,
                    clock_in_time TIMESTAMP,
                    clock_out_time TIMESTAMP,
                    break_start_time TIMESTAMP,
                    break_end_time TIMESTAMP,
                    total_work_hours REAL,
                    overtime_hours REAL DEFAULT 0,
                    status TEXT CHECK(status IN ('在席', '離席', '休憩中', '退勤')) DEFAULT '離席',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, work_date)
                )
            ''')
            
            # 設定テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    setting_key TEXT NOT NULL,
                    setting_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, setting_key)
                )
            ''')
            
            conn.commit()
            logger.info("データベースの初期化が完了しました")
        finally:
            conn.close()
    
    def initialize_database(self):
        """データベースの初期化（互換性のためのエイリアス）"""
        self.init_database()


class UserRepository:
    """ユーザー関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    @handle_database_error
    @retry_on_lock()
    def create_user(self, discord_id: str, username: str, display_name: str = None, email: str = None) -> int:
        """新しいユーザーを作成"""
        validate_required_fields({'discord_id': discord_id, 'username': username}, ['discord_id', 'username'])
        
        discord_id = sanitize_string(discord_id, 50)
        username = sanitize_string(username, 100)
        display_name = sanitize_string(display_name, 100)
        email = sanitize_string(email, 255)
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, '''
                    INSERT INTO users (discord_id, username, display_name, email)
                    VALUES (?, ?, ?, ?)
                ''', (discord_id, username, display_name, email))
                return cursor.lastrowid
    
    @handle_database_error
    @log_query_performance
    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Discord IDでユーザーを取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            safe_execute(cursor, 'SELECT * FROM users WHERE discord_id = ?', (discord_id,))
            return fetch_one_as_dict(cursor)
    
    @handle_database_error
    def get_or_create_user(self, discord_id: str, username: str, display_name: str = None) -> Dict[str, Any]:
        """ユーザーを取得、存在しない場合は作成"""
        user = self.get_user_by_discord_id(discord_id)
        if not user:
            user_id = self.create_user(discord_id, username, display_name)
            user = self.get_user_by_discord_id(discord_id)
            if not user:
                raise DatabaseError("ユーザーの作成後に取得できませんでした")
        return user
    
    @handle_database_error
    @retry_on_lock()
    def update_user(self, discord_id: str, **kwargs) -> bool:
        """ユーザー情報を更新"""
        if not kwargs:
            return False
        
        # サニタイズ
        if 'username' in kwargs:
            kwargs['username'] = sanitize_string(kwargs['username'], 100)
        if 'display_name' in kwargs:
            kwargs['display_name'] = sanitize_string(kwargs['display_name'], 100)
        if 'email' in kwargs:
            kwargs['email'] = sanitize_string(kwargs['email'], 255)
        
        query, params = build_update_query('users', kwargs, 'discord_id = ?')
        params = list(params) + [discord_id]
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, query, tuple(params))
                return cursor.rowcount > 0


class TaskRepository:
    """タスク関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    @handle_database_error
    @retry_on_lock()
    def create_task(self, user_id: int, title: str, description: str = "", 
                   priority: str = "中", due_date: str = None) -> int:
        """新しいタスクを作成"""
        validate_required_fields({'user_id': user_id, 'title': title}, ['user_id', 'title'])
        
        title = sanitize_string(title, 200)
        description = sanitize_string(description, 1000)
        
        if priority not in ['高', '中', '低']:
            priority = '中'
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, '''
                    INSERT INTO tasks (user_id, title, description, priority, due_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, title, description, priority, due_date))
                return cursor.lastrowid
    
    @handle_database_error
    @log_query_performance
    def get_user_tasks(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """ユーザーのタスク一覧を取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                safe_execute(cursor, '''
                    SELECT * FROM tasks WHERE user_id = ? AND status = ?
                    ORDER BY 
                        CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 WHEN '低' THEN 3 END,
                        due_date ASC
                ''', (user_id, status))
            else:
                safe_execute(cursor, '''
                    SELECT * FROM tasks WHERE user_id = ?
                    ORDER BY 
                        CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 WHEN '低' THEN 3 END,
                        due_date ASC
                ''', (user_id,))
            return fetch_all_as_dict(cursor)
    
    @handle_database_error
    @retry_on_lock()
    def update_task_status(self, task_id: int, status: str) -> bool:
        """タスクのステータスを更新"""
        if status not in ['未着手', '進行中', '完了', '中断']:
            raise ValueError(f"無効なステータス: {status}")
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                completed_at = now_jst() if status == '完了' else None
                safe_execute(cursor, '''
                    UPDATE tasks SET status = ?, completed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, completed_at, now_jst(), task_id))
                return cursor.rowcount > 0
    
    @handle_database_error
    @retry_on_lock()
    def delete_task(self, task_id: int) -> bool:
        """タスクを削除"""
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, 'DELETE FROM tasks WHERE id = ?', (task_id,))
                return cursor.rowcount > 0
    
    @handle_database_error
    @log_query_performance
    def get_tasks_due_soon(self, days: int = 1) -> List[Dict[str, Any]]:
        """期限が近いタスクを取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            safe_execute(cursor, '''
                SELECT t.*, u.discord_id, u.username 
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.due_date <= date('now', '+' || ? || ' days')
                AND t.status != '完了'
                ORDER BY t.due_date ASC
            ''', (days,))
            return fetch_all_as_dict(cursor)


class AttendanceRepository:
    """出退勤関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    @handle_database_error
    @retry_on_lock()
    def clock_in(self, user_id: int, work_date: str = None) -> bool:
        """出勤記録"""
        if work_date is None:
            work_date = today_jst().isoformat()
        
        now = now_jst()
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, '''
                    INSERT OR REPLACE INTO attendance 
                    (user_id, work_date, clock_in_time, status, updated_at)
                    VALUES (?, ?, ?, '在席', ?)
                ''', (user_id, work_date, now.isoformat(), now.isoformat()))
                return cursor.rowcount > 0
    
    @handle_database_error
    @retry_on_lock()
    def clock_out(self, user_id: int, work_date: str = None) -> bool:
        """退勤記録"""
        if work_date is None:
            work_date = today_jst().isoformat()
        
        now = now_jst()
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                # 既存の出勤記録を取得
                safe_execute(cursor, '''
                    SELECT clock_in_time, break_start_time, break_end_time 
                    FROM attendance 
                    WHERE user_id = ? AND work_date = ?
                ''', (user_id, work_date))
                
                record = fetch_one_as_dict(cursor)
                if not record or not record['clock_in_time']:
                    return False
                
                # 勤務時間を計算
                total_hours = calculate_work_hours(
                    record['clock_in_time'],
                    now,
                    record['break_start_time'],
                    record['break_end_time']
                )
                
                # 残業時間を計算
                overtime_hours = calculate_overtime_hours(total_hours)
                
                safe_execute(cursor, '''
                    UPDATE attendance SET 
                    clock_out_time = ?, 
                    total_work_hours = ?, 
                    overtime_hours = ?,
                    status = '退勤',
                    updated_at = ?
                    WHERE user_id = ? AND work_date = ?
                ''', (now.isoformat(), total_hours, overtime_hours, now.isoformat(), user_id, work_date))
                
                return cursor.rowcount > 0
    
    @handle_database_error
    @retry_on_lock()
    def start_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩開始"""
        if work_date is None:
            work_date = today_jst().isoformat()
        
        now = now_jst()
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, '''
                    UPDATE attendance SET 
                    break_start_time = ?, 
                    status = '休憩中',
                    updated_at = ?
                    WHERE user_id = ? AND work_date = ? AND clock_in_time IS NOT NULL
                ''', (now.isoformat(), now.isoformat(), user_id, work_date))
                return cursor.rowcount > 0
    
    @handle_database_error
    @retry_on_lock()
    def end_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩終了"""
        if work_date is None:
            work_date = today_jst().isoformat()
        
        now = now_jst()
        
        with self.db_manager.get_connection() as conn:
            with transaction(conn) as cursor:
                safe_execute(cursor, '''
                    UPDATE attendance SET 
                    break_end_time = ?, 
                    status = '在席',
                    updated_at = ?
                    WHERE user_id = ? AND work_date = ? AND break_start_time IS NOT NULL
                ''', (now.isoformat(), now.isoformat(), user_id, work_date))
                return cursor.rowcount > 0
    
    @handle_database_error
    @log_query_performance
    def get_today_attendance(self, user_id: int, work_date: str = None) -> Optional[Dict[str, Any]]:
        """今日の出退勤記録を取得"""
        if work_date is None:
            work_date = today_jst().isoformat()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            safe_execute(cursor, '''
                SELECT * FROM attendance 
                WHERE user_id = ? AND work_date = ?
            ''', (user_id, work_date))
            return fetch_one_as_dict(cursor)
    
    @handle_database_error
    @log_query_performance
    def get_monthly_attendance(self, user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
        """月次出退勤記録を取得"""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            safe_execute(cursor, '''
                SELECT * FROM attendance 
                WHERE user_id = ? AND work_date >= ? AND work_date < ?
                ORDER BY work_date
            ''', (user_id, start_date, end_date))
            return fetch_all_as_dict(cursor)
    
    @handle_database_error
    @log_query_performance
    def get_all_users_status(self) -> List[Dict[str, Any]]:
        """全ユーザーの現在の勤怠状況を取得"""
        today = today_jst().isoformat()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            safe_execute(cursor, '''
                SELECT u.discord_id, u.username, u.display_name, 
                       COALESCE(a.status, '離席') as status,
                       a.clock_in_time, a.clock_out_time
                FROM users u
                LEFT JOIN attendance a ON u.id = a.user_id AND a.work_date = ?
            ''', (today,))
            return fetch_all_as_dict(cursor)
    
    @handle_database_error
    @log_query_performance
    def get_attendance_range(self, start_date: str, end_date: str, user_id: int = None) -> List[Dict[str, Any]]:
        """指定期間の勤怠データを取得（CSV出力用）"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                # 特定ユーザーのデータ
                safe_execute(cursor, '''
                    SELECT a.work_date as date, 
                           u.username, u.display_name,
                           a.clock_in_time, a.clock_out_time,
                           a.break_start_time, a.break_end_time,
                           CASE 
                               WHEN a.break_start_time IS NOT NULL AND a.break_end_time IS NOT NULL
                               THEN CAST((julianday(a.break_end_time) - julianday(a.break_start_time)) * 24 * 60 AS INTEGER)
                               ELSE 0
                           END as total_break_minutes,
                           COALESCE(a.total_work_hours, 0) as total_work_hours,
                           COALESCE(a.overtime_hours, 0) as overtime_hours,
                           COALESCE(a.status, '') as status,
                           COALESCE(a.notes, '') as notes
                    FROM attendance a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.work_date BETWEEN ? AND ? AND a.user_id = ?
                    ORDER BY a.work_date, u.username
                ''', (start_date, end_date, user_id))
            else:
                # 全ユーザーのデータ
                safe_execute(cursor, '''
                    SELECT a.work_date as date, 
                           u.username, u.display_name,
                           a.clock_in_time, a.clock_out_time,
                           a.break_start_time, a.break_end_time,
                           CASE 
                               WHEN a.break_start_time IS NOT NULL AND a.break_end_time IS NOT NULL
                               THEN CAST((julianday(a.break_end_time) - julianday(a.break_start_time)) * 24 * 60 AS INTEGER)
                               ELSE 0
                           END as total_break_minutes,
                           COALESCE(a.total_work_hours, 0) as total_work_hours,
                           COALESCE(a.overtime_hours, 0) as overtime_hours,
                           COALESCE(a.status, '') as status,
                           COALESCE(a.notes, '') as notes
                    FROM attendance a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.work_date BETWEEN ? AND ?
                    ORDER BY a.work_date, u.username
                ''', (start_date, end_date))
            
            return fetch_all_as_dict(cursor)


# データベースマネージャーのインスタンスを作成（テスト時以外）
def get_default_instances():
    """デフォルトのデータベースインスタンスを取得"""
    db_manager = DatabaseManager()
    return {
        'db_manager': db_manager,
        'user_repo': UserRepository(db_manager),
        'task_repo': TaskRepository(db_manager),
        'attendance_repo': AttendanceRepository(db_manager)
    }


# メイン実行時のみインスタンスを作成
if __name__ != '__main__':
    # テスト実行時以外でインスタンス作成
    try:
        # Always create instances for imports, but log a warning if Discord token is missing
        _instances = get_default_instances()
        db_manager = _instances['db_manager']
        user_repo = _instances['user_repo']
        task_repo = _instances['task_repo']
        attendance_repo = _instances['attendance_repo']
        
        # Check for Discord token and warn if missing
        if not os.getenv('DISCORD_TOKEN'):
            logger = logging.getLogger(__name__)
            logger.warning("DISCORD_TOKEN not set - database created but bot won't start")
        
        # 互換性のため
        daily_report_repo = None
    except Exception as e:
        # 設定ファイルが無い場合等はインスタンス作成をスキップ
        logger = logging.getLogger(__name__)
        logger.warning(f"デフォルトインスタンスの作成をスキップ: {e}")
        db_manager = None
        user_repo = None
        daily_report_repo = None
        task_repo = None
        attendance_repo = None 