import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース操作管理クラス"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_URL
        self.init_database()
    
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でのアクセスを可能にする
        return conn
    
    def init_database(self):
        """データベースとテーブルの初期化"""
        with self.get_connection() as conn:
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

class UserRepository:
    """ユーザー関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_user(self, discord_id: str, username: str, display_name: str = None, email: str = None) -> int:
        """新しいユーザーを作成"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (discord_id, username, display_name, email)
                VALUES (?, ?, ?, ?)
            ''', (discord_id, username, display_name, email))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Discord IDでユーザーを取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE discord_id = ?', (discord_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
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
        
        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [discord_id]
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0

class DailyReportRepository:
    """日報関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_daily_report(self, user_id: int, report_date: str, today_tasks: str, 
                          tomorrow_tasks: str = "", obstacles: str = "", comments: str = "") -> int:
        """日報を作成"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_reports 
                (user_id, report_date, today_tasks, tomorrow_tasks, obstacles, comments)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, report_date, today_tasks, tomorrow_tasks, obstacles, comments))
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_report(self, user_id: int, report_date: str) -> Optional[Dict[str, Any]]:
        """指定日の日報を取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM daily_reports 
                WHERE user_id = ? AND report_date = ?
            ''', (user_id, report_date))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_users_without_report(self, report_date: str) -> List[Dict[str, Any]]:
        """指定日に日報を提出していないユーザーを取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.* FROM users u
                LEFT JOIN daily_reports dr ON u.id = dr.user_id AND dr.report_date = ?
                WHERE dr.id IS NULL
            ''', (report_date,))
            return [dict(row) for row in cursor.fetchall()]

class TaskRepository:
    """タスク関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_task(self, user_id: int, title: str, description: str = "", 
                   priority: str = "中", due_date: str = None) -> int:
        """新しいタスクを作成"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (user_id, title, description, priority, due_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, title, description, priority, due_date))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_tasks(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """ユーザーのタスク一覧を取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute('''
                    SELECT * FROM tasks WHERE user_id = ? AND status = ?
                    ORDER BY 
                        CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 WHEN '低' THEN 3 END,
                        due_date ASC
                ''', (user_id, status))
            else:
                cursor.execute('''
                    SELECT * FROM tasks WHERE user_id = ?
                    ORDER BY 
                        CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 WHEN '低' THEN 3 END,
                        due_date ASC
                ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """タスクのステータスを更新"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            completed_at = datetime.now() if status == '完了' else None
            cursor.execute('''
                UPDATE tasks SET status = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, completed_at, task_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_task(self, task_id: int) -> bool:
        """タスクを削除"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_tasks_due_soon(self, days: int = 1) -> List[Dict[str, Any]]:
        """期限が近いタスクを取得"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, u.discord_id, u.username 
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.due_date <= date('now', '+' || ? || ' days')
                AND t.status != '完了'
                ORDER BY t.due_date ASC
            ''', (days,))
            return [dict(row) for row in cursor.fetchall()]

class AttendanceRepository:
    """出退勤関連のデータベース操作"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def clock_in(self, user_id: int, work_date: str = None) -> bool:
        """出勤記録"""
        if work_date is None:
            work_date = date.today().isoformat()
        
        now = datetime.now()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO attendance 
                (user_id, work_date, clock_in_time, status, updated_at)
                VALUES (?, ?, ?, '在席', CURRENT_TIMESTAMP)
            ''', (user_id, work_date, now))
            conn.commit()
            return cursor.rowcount > 0
    
    def clock_out(self, user_id: int, work_date: str = None) -> bool:
        """退勤記録"""
        if work_date is None:
            work_date = date.today().isoformat()
        
        now = datetime.now()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 既存の出勤記録を取得
            cursor.execute('''
                SELECT clock_in_time, break_start_time, break_end_time 
                FROM attendance 
                WHERE user_id = ? AND work_date = ?
            ''', (user_id, work_date))
            
            record = cursor.fetchone()
            if not record or not record['clock_in_time']:
                return False
            
            # 勤務時間を計算
            clock_in = datetime.fromisoformat(record['clock_in_time'])
            total_hours = (now - clock_in).total_seconds() / 3600
            
            # 休憩時間を引く
            if record['break_start_time'] and record['break_end_time']:
                break_start = datetime.fromisoformat(record['break_start_time'])
                break_end = datetime.fromisoformat(record['break_end_time'])
                break_hours = (break_end - break_start).total_seconds() / 3600
                total_hours -= break_hours
            
            # 残業時間を計算（8時間を超えた分）
            overtime_hours = max(0, total_hours - 8.0)
            
            cursor.execute('''
                UPDATE attendance SET 
                clock_out_time = ?, 
                total_work_hours = ?, 
                overtime_hours = ?,
                status = '退勤',
                updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND work_date = ?
            ''', (now, total_hours, overtime_hours, user_id, work_date))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def start_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩開始"""
        if work_date is None:
            work_date = date.today().isoformat()
        
        now = datetime.now()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE attendance SET 
                break_start_time = ?, 
                status = '休憩中',
                updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND work_date = ? AND clock_in_time IS NOT NULL
            ''', (now, user_id, work_date))
            conn.commit()
            return cursor.rowcount > 0
    
    def end_break(self, user_id: int, work_date: str = None) -> bool:
        """休憩終了"""
        if work_date is None:
            work_date = date.today().isoformat()
        
        now = datetime.now()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE attendance SET 
                break_end_time = ?, 
                status = '在席',
                updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND work_date = ? AND break_start_time IS NOT NULL
            ''', (now, user_id, work_date))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_today_attendance(self, user_id: int, work_date: str = None) -> Optional[Dict[str, Any]]:
        """今日の出退勤記録を取得"""
        if work_date is None:
            work_date = date.today().isoformat()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE user_id = ? AND work_date = ?
            ''', (user_id, work_date))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_monthly_attendance(self, user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
        """月次出退勤記録を取得"""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE user_id = ? AND work_date >= ? AND work_date < ?
                ORDER BY work_date
            ''', (user_id, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_users_status(self) -> List[Dict[str, Any]]:
        """全ユーザーの現在の勤怠状況を取得"""
        today = date.today().isoformat()
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.discord_id, u.username, u.display_name, 
                       COALESCE(a.status, '離席') as status,
                       a.clock_in_time, a.clock_out_time
                FROM users u
                LEFT JOIN attendance a ON u.id = a.user_id AND a.work_date = ?
            ''', (today,))
            return [dict(row) for row in cursor.fetchall()]

# データベースマネージャーのインスタンスを作成（テスト時以外）
def get_default_instances():
    """デフォルトのデータベースインスタンスを取得"""
    db_manager = DatabaseManager()
    return {
        'db_manager': db_manager,
        'user_repo': UserRepository(db_manager),
        'daily_report_repo': DailyReportRepository(db_manager),
        'task_repo': TaskRepository(db_manager),
        'attendance_repo': AttendanceRepository(db_manager)
    }

# メイン実行時のみインスタンスを作成
if __name__ != '__main__':
    # テスト実行時以外でインスタンス作成
    try:
        _instances = get_default_instances()
        db_manager = _instances['db_manager']
        user_repo = _instances['user_repo']
        daily_report_repo = _instances['daily_report_repo']
        task_repo = _instances['task_repo']
        attendance_repo = _instances['attendance_repo']
    except Exception as e:
        # 設定ファイルが無い場合等はインスタンス作成をスキップ
        logger = logging.getLogger(__name__)
        logger.warning(f"デフォルトインスタンスの作成をスキップ: {e}")
        db_manager = None
        user_repo = None
        daily_report_repo = None
        task_repo = None
        attendance_repo = None 