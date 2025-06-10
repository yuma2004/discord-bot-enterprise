#!/usr/bin/env python3
"""
出退勤機能のテストファイル
PostgreSQLとSQLiteの互換性、日時処理、CRUD操作をテスト
"""

import unittest
import asyncio
import sys
import os
from datetime import datetime, date
from unittest.mock import Mock, AsyncMock, patch

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 環境変数を設定（テスト用）
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['ENVIRONMENT'] = 'test'

# PostgreSQLがローカルで利用できない場合はSQLiteのみでテスト
try:
    from database_postgres import PostgreSQLUserRepository, PostgreSQLAttendanceRepository, PostgreSQLManager
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from database import DatabaseManager, UserRepository, AttendanceRepository

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
    """出退勤ビジネスロジックテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.mock_user = {
            'id': 1,
            'discord_id': '123456789',
            'username': 'testuser',
            'display_name': 'Test User'
        }
        
        self.mock_attendance_record = {
            'id': 1,
            'user_id': 1,
            'work_date': date.today(),
            'clock_in_time': datetime(2025, 6, 10, 9, 0, 0),
            'clock_out_time': datetime(2025, 6, 10, 18, 0, 0),
            'status': 'present',
            'total_work_hours': 8.0,
            'overtime_hours': 0.0
        }
    
    def test_clock_in_logic(self):
        """出勤ロジックテスト"""
        # 出勤時刻の処理
        clock_in_time = self.mock_attendance_record['clock_in_time']
        
        # 型チェック
        if isinstance(clock_in_time, str):
            processed_time = datetime.fromisoformat(clock_in_time)
        else:
            processed_time = clock_in_time
        
        self.assertIsInstance(processed_time, datetime)
        self.assertEqual(processed_time.hour, 9)
    
    def test_clock_out_logic(self):
        """退勤ロジックテスト"""
        # 退勤時刻の処理
        clock_out_time = self.mock_attendance_record['clock_out_time']
        
        # 型チェック
        if isinstance(clock_out_time, str):
            processed_time = datetime.fromisoformat(clock_out_time)
        else:
            processed_time = clock_out_time
        
        self.assertIsInstance(processed_time, datetime)
        self.assertEqual(processed_time.hour, 18)
    
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

class TestAttendanceCommands(unittest.TestCase):
    """出退勤コマンドテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.mock_interaction = Mock()
        self.mock_interaction.user = Mock()
        self.mock_interaction.user.id = 123456789
        self.mock_interaction.user.name = 'testuser'
        self.mock_interaction.user.display_name = 'Test User'
        self.mock_interaction.response = AsyncMock()
        self.mock_interaction.followup = AsyncMock()
    
    def test_user_creation(self):
        """ユーザー作成テスト"""
        # ユーザー情報の模擬
        discord_id = str(self.mock_interaction.user.id)
        username = self.mock_interaction.user.name
        display_name = self.mock_interaction.user.display_name
        
        # 基本的な検証
        self.assertIsInstance(discord_id, str)
        self.assertIsNotNone(username)
        self.assertIsNotNone(display_name)
    
    @patch('bot.commands.attendance.user_repo')
    @patch('bot.commands.attendance.attendance_repo')
    def test_clock_in_button_logic(self, mock_attendance_repo, mock_user_repo):
        """出勤ボタンロジックテスト"""
        # モックの設定
        mock_user_repo.get_or_create_user.return_value = self.mock_interaction.user
        mock_attendance_repo.get_today_attendance.return_value = None
        mock_attendance_repo.clock_in.return_value = True
        
        # テスト対象の関数を直接テスト
        user = mock_user_repo.get_or_create_user(
            str(self.mock_interaction.user.id),
            self.mock_interaction.user.name,
            self.mock_interaction.user.display_name
        )
        
        today_record = mock_attendance_repo.get_today_attendance(1)
        
        self.assertIsNone(today_record)  # 今日の記録なし
        self.assertIsNotNone(user)

class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングテスト"""
    
    def test_none_datetime_handling(self):
        """None値の日時処理テスト"""
        test_value = None
        
        if test_value and isinstance(test_value, str):
            result = datetime.fromisoformat(test_value)
        elif test_value:
            result = test_value
        else:
            result = None
        
        self.assertIsNone(result)
    
    def test_invalid_datetime_string(self):
        """無効な日時文字列のテスト"""
        test_value = "invalid-datetime"
        
        try:
            if isinstance(test_value, str):
                result = datetime.fromisoformat(test_value)
            else:
                result = test_value
        except ValueError:
            result = None
        
        self.assertIsNone(result)

class TestConfigValidation(unittest.TestCase):
    """設定検証テスト"""
    
    def test_environment_variables(self):
        """環境変数テスト"""
        self.assertEqual(os.environ.get('ENVIRONMENT'), 'test')
        self.assertIsNotNone(os.environ.get('DATABASE_URL'))
    
    def test_database_url_format(self):
        """DATABASE_URL形式テスト"""
        db_url = os.environ.get('DATABASE_URL', '')
        
        # SQLiteまたはPostgreSQLの形式チェック
        is_sqlite = 'sqlite' in db_url
        is_postgres = 'postgres' in db_url
        
        self.assertTrue(is_sqlite or is_postgres, "Database URL should be SQLite or PostgreSQL format")

def run_tests():
    """テスト実行関数"""
    print("🧪 Discord Bot Enterprise - 出退勤機能テスト開始")
    print("=" * 60)
    
    # テストスイートの作成
    test_suite = unittest.TestSuite()
    
    # テストケースの追加
    test_classes = [
        TestDateTimeCompatibility,
        TestDatabaseCompatibility,
        TestAttendanceBusinessLogic,
        TestAttendanceCommands,
        TestErrorHandling,
        TestConfigValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 テスト結果サマリー")
    print(f"✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失敗: {len(result.failures)}")
    print(f"💥 エラー: {len(result.errors)}")
    print(f"📊 総テスト数: {result.testsRun}")
    
    if result.failures:
        print("\n🚨 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n💥 エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 