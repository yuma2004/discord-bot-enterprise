#!/usr/bin/env python3
"""
出退勤機能のテストファイル
PostgreSQLとSQLiteの互換性、日時処理、CRUD操作をテスト
"""

import unittest
import asyncio
import sys
import os
import csv
import io
import tempfile
from datetime import datetime, date, timedelta
from unittest.mock import Mock, AsyncMock, patch

# テスト用環境変数を設定（他のインポートより前に設定）
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# PostgreSQLがローカルで利用できない場合はSQLiteのみでテスト
try:
    from database_postgres import PostgreSQLUserRepository, PostgreSQLAttendanceRepository, PostgreSQLManager
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from database import DatabaseManager, UserRepository, AttendanceRepository
from config import Config

class TestDateTimeCompatibility(unittest.TestCase):
    """日時処理の互換性テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_datetime = datetime(2025, 6, 10, 9, 0, 0)
        self.test_date_str = "2025-06-10"
        self.test_datetime_str = "2025-06-10T09:00:00"
    
    def test_datetime_object_handling(self):
        """datetimeオブジェクトの処理テスト"""
        # PostgreSQL形式（datetimeオブジェクト）
        test_value = self.test_datetime
        
        # 文字列チェック
        if isinstance(test_value, str):
            result = datetime.fromisoformat(test_value)
        else:
            result = test_value
        
        self.assertEqual(result, self.test_datetime)
        self.assertIsInstance(result, datetime)
    
    def test_string_datetime_handling(self):
        """文字列日時の処理テスト"""
        # SQLite形式（文字列）
        test_value = self.test_datetime_str
        
        # 文字列チェック
        if isinstance(test_value, str):
            result = datetime.fromisoformat(test_value)
        else:
            result = test_value
        
        self.assertEqual(result, self.test_datetime)
        self.assertIsInstance(result, datetime)
    
    def test_none_datetime_handling(self):
        """None値の日時処理テスト"""
        test_value = None
        
        try:
            if test_value:
                if isinstance(test_value, str):
                    result = datetime.fromisoformat(test_value)
                else:
                    result = test_value
            else:
                result = None
                
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"None値の処理でエラー: {e}")

class TestDatabaseCompatibility(unittest.TestCase):
    """データベース互換性テスト"""
    
    def test_postgresql_imports(self):
        """PostgreSQL関連のインポートテスト"""
        if not POSTGRES_AVAILABLE:
            self.skipTest("PostgreSQL libraries not available in local environment")
        
        try:
            from database_postgres import db_manager, user_repo, attendance_repo
            self.assertTrue(True, "PostgreSQL imports successful")
        except ImportError as e:
            self.fail(f"PostgreSQL import failed: {e}")
    
    def test_sqlite_fallback(self):
        """SQLite フォールバックテスト"""
        try:
            from database import db_manager, user_repo, attendance_repo
            self.assertTrue(True, "SQLite imports successful")
        except ImportError as e:
            self.fail(f"SQLite import failed: {e}")

class TestAttendanceBusinessLogic(unittest.TestCase):
    """出退勤ビジネスロジックのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        # モック出退勤レコード
        self.mock_attendance_record = {
            'id': 1,
            'user_id': 1,
            'work_date': '2025-06-10',
            'clock_in_time': '2025-06-10T09:00:00',
            'clock_out_time': '2025-06-10T18:00:00',
            'break_start_time': '2025-06-10T12:00:00',
            'break_end_time': '2025-06-10T13:00:00',
            'total_work_hours': 8.0,
            'overtime_hours': 0.0,
            'status': '退勤',
            'notes': None
        }
    
    def test_work_hours_calculation(self):
        """勤務時間計算テスト"""
        clock_in = self.mock_attendance_record['clock_in_time']
        clock_out = self.mock_attendance_record['clock_out_time']
        
        # 型の統一
        if isinstance(clock_in, str):
            clock_in = datetime.fromisoformat(clock_in)
        if isinstance(clock_out, str):
            clock_out = datetime.fromisoformat(clock_out)
        
        work_hours = (clock_out - clock_in).total_seconds() / 3600
        self.assertEqual(work_hours, 9.0)  # 9時間勤務
    
    def test_break_time_calculation(self):
        """休憩時間計算テスト"""
        break_start = self.mock_attendance_record['break_start_time']
        break_end = self.mock_attendance_record['break_end_time']
        
        if isinstance(break_start, str):
            break_start = datetime.fromisoformat(break_start)
        if isinstance(break_end, str):
            break_end = datetime.fromisoformat(break_end)
        
        break_hours = (break_end - break_start).total_seconds() / 3600
        self.assertEqual(break_hours, 1.0)  # 1時間休憩
    
    def test_overtime_calculation(self):
        """残業時間計算テスト"""
        total_work_hours = 9.0  # 9時間勤務
        standard_work_hours = 8.0
        
        overtime_hours = max(0, total_work_hours - standard_work_hours)
        self.assertEqual(overtime_hours, 1.0)  # 1時間残業

class TestAttendanceCSVExport(unittest.TestCase):
    """出退勤CSV出力のテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        import time
        import random
        self.test_db_path = f'test_csv_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        self.user_repo = UserRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
        
        # テストユーザー作成
        self.test_user_id = self.user_repo.create_user(
            discord_id="123456789",
            username="csvtestuser",
            display_name="CSV Test User"
        )
        
        self.test_user2_id = self.user_repo.create_user(
            discord_id="987654321",
            username="csvtestuser2",
            display_name="CSV Test User 2"
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'db_manager'):
            del self.db_manager
        
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except:
            pass
    
    def test_csv_data_format(self):
        """CSV出力データ形式のテスト"""
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        # テストデータ作成
        for work_date in [yesterday, today]:
            self.attendance_repo.clock_in(self.test_user_id, work_date)
            self.attendance_repo.clock_out(self.test_user_id, work_date)
            
            self.attendance_repo.clock_in(self.test_user2_id, work_date)
            self.attendance_repo.clock_out(self.test_user2_id, work_date)
        
        # CSV用データ取得
        csv_data = self.attendance_repo.get_attendance_range(yesterday, today)
        
        # データが正常に取得されることを確認
        self.assertGreater(len(csv_data), 0)
        
        # 必須フィールドの存在確認
        required_fields = [
            'date', 'username', 'display_name', 'clock_in_time', 'clock_out_time',
            'break_start_time', 'break_end_time', 'total_break_minutes',
            'total_work_hours', 'overtime_hours', 'status', 'notes'
        ]
        
        for record in csv_data:
            for field in required_fields:
                self.assertIn(field, record, f"必須フィールド '{field}' が見つかりません")
    
    def test_csv_time_formatting(self):
        """CSV時刻フォーマットのテスト"""
        today = date.today().isoformat()
        
        # 勤怠記録作成
        self.attendance_repo.clock_in(self.test_user_id, today)
        self.attendance_repo.clock_out(self.test_user_id, today)
        
        # CSV用データ取得
        csv_data = self.attendance_repo.get_attendance_range(today, today)
        
        self.assertGreater(len(csv_data), 0)
        
        record = csv_data[0]
        
        # 時刻フォーマット関数のテスト
        def format_time(time_str):
            if not time_str:
                return ''
            try:
                if isinstance(time_str, str):
                    dt = datetime.fromisoformat(time_str)
                else:
                    dt = time_str
                return dt.strftime('%H:%M')
            except (ValueError, TypeError):
                return str(time_str) if time_str else ''
        
        # 出勤時刻のフォーマットテスト
        clock_in_formatted = format_time(record['clock_in_time'])
        self.assertRegex(clock_in_formatted, r'^\d{2}:\d{2}$', 
                        f"出勤時刻のフォーマットが不正: {clock_in_formatted}")
        
        # 退勤時刻のフォーマットテスト
        clock_out_formatted = format_time(record['clock_out_time'])
        self.assertRegex(clock_out_formatted, r'^\d{2}:\d{2}$',
                        f"退勤時刻のフォーマットが不正: {clock_out_formatted}")
    
    def test_csv_creation_and_encoding(self):
        """CSV作成とエンコーディングのテスト"""
        today = date.today().isoformat()
        
        # テストデータ作成
        self.attendance_repo.clock_in(self.test_user_id, today)
        self.attendance_repo.clock_out(self.test_user_id, today)
        
        # CSV用データ取得
        csv_data = self.attendance_repo.get_attendance_range(today, today)
        
        # CSVファイル作成テスト
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # ヘッダー行
        headers = [
            '日付', 'ユーザー名', '表示名', '出勤時刻', '退勤時刻',
            '休憩開始', '休憩終了', '総休憩時間（分）', '総勤務時間（時間）',
            '残業時間（時間）', 'ステータス', '備考'
        ]
        csv_writer.writerow(headers)
        
        # データ行
        for record in csv_data:
            def format_time(time_str):
                if not time_str:
                    return ''
                try:
                    if isinstance(time_str, str):
                        dt = datetime.fromisoformat(time_str)
                    else:
                        dt = time_str
                    return dt.strftime('%H:%M')
                except (ValueError, TypeError):
                    return str(time_str) if time_str else ''
            
            csv_writer.writerow([
                record.get('date', ''),
                record.get('username', ''),
                record.get('display_name', ''),
                format_time(record.get('clock_in_time')),
                format_time(record.get('clock_out_time')),
                format_time(record.get('break_start_time')),
                format_time(record.get('break_end_time')),
                record.get('total_break_minutes', 0),
                f"{record.get('total_work_hours', 0):.1f}",
                f"{record.get('overtime_hours', 0):.1f}",
                record.get('status', ''),
                record.get('notes', '')
            ])
        
        # CSV内容の確認
        csv_content = csv_buffer.getvalue()
        self.assertIn('日付', csv_content)
        self.assertIn('ユーザー名', csv_content)
        self.assertIn('csvtestuser', csv_content)
        
        # エンコーディングテスト
        try:
            csv_bytes = io.BytesIO(csv_content.encode('utf-8-sig'))
            self.assertIsNotNone(csv_bytes.getvalue())
        except Exception as e:
            self.fail(f"CSVエンコーディングでエラー: {e}")
    
    def test_csv_edge_cases(self):
        """CSVエッジケースのテスト"""
        # データが存在しない場合
        future_date = (date.today() + timedelta(days=30)).isoformat()
        csv_data = self.attendance_repo.get_attendance_range(future_date, future_date)
        self.assertEqual(len(csv_data), 0)
        
        # 特定ユーザーのみの場合
        today = date.today().isoformat()
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        csv_data = self.attendance_repo.get_attendance_range(
            today, today, self.test_user_id
        )
        self.assertEqual(len(csv_data), 1)
        self.assertEqual(csv_data[0]['username'], 'csvtestuser')
    
    def test_csv_japanese_timezone(self):
        """CSV出力での日本時間テスト"""
        import pytz
        
        # 日本時間の設定
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        
        # タイムゾーンが正しく設定されていることを確認
        self.assertEqual(Config.TIMEZONE, 'Asia/Tokyo')
        
        # 日時フォーマットが日本時間ベースで動作することを確認
        today = date.today().isoformat()
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertIsNotNone(record)
        
        # 日時データが存在し、処理可能であることを確認
        clock_in_time = record['clock_in_time']
        if isinstance(clock_in_time, str):
            dt = datetime.fromisoformat(clock_in_time)
        else:
            dt = clock_in_time
        
        # 日時オブジェクトが正常に作成されることを確認
        self.assertIsInstance(dt, datetime)

def run_attendance_tests():
    """出退勤テストの実行"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDateTimeCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestAttendanceBusinessLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestAttendanceCSVExport))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_attendance_tests()
    sys.exit(0 if success else 1) 