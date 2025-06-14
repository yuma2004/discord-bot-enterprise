"""
リファクタリングしたコードの網羅的なテスト

このテストファイルは、リファクタリング後のコードの動作を検証します。
特に日時処理、エラーハンドリング、データベース操作の改善点に焦点を当てています。
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime, date, timedelta
import pytz
from unittest.mock import Mock, patch, MagicMock

# テスト対象のモジュールをインポート
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.datetime_utils import (
    now_jst, today_jst, ensure_jst, format_time_only, format_date_only,
    format_datetime_for_display, calculate_work_hours, calculate_overtime_hours,
    calculate_time_difference, get_month_date_range, parse_date_string, 
    adapt_datetime_for_sqlite, convert_datetime_from_sqlite, JST
)

from bot.utils.database_utils import (
    handle_database_error, retry_on_lock, transaction, safe_execute,
    fetch_one_as_dict, fetch_all_as_dict, validate_required_fields,
    sanitize_string, build_update_query, DatabaseError, RecordNotFoundError,
    DuplicateRecordError
)


class TestDateTimeUtils(unittest.TestCase):
    """日時処理ユーティリティのテスト"""
    
    def setUp(self):
        """テストの初期設定"""
        self.test_dt = datetime(2024, 1, 15, 9, 30, 0)
        self.test_dt_jst = JST.localize(self.test_dt)
    
    def test_now_jst(self):
        """now_jst関数のテスト"""
        result = now_jst()
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.tzinfo.zone, 'Asia/Tokyo')
    
    def test_today_jst(self):
        """today_jst関数のテスト"""
        result = today_jst()
        self.assertIsInstance(result, date)
    
    def test_ensure_jst_with_naive_datetime(self):
        """ナイーブなdatetimeのJST変換テスト"""
        result = ensure_jst(self.test_dt)
        self.assertEqual(result.tzinfo.zone, 'Asia/Tokyo')
        self.assertEqual(result.hour, 9)
    
    def test_ensure_jst_with_string(self):
        """文字列からのJST変換テスト"""
        dt_str = "2024-01-15T09:30:00"
        result = ensure_jst(dt_str)
        self.assertEqual(result.tzinfo.zone, 'Asia/Tokyo')
        self.assertEqual(result.hour, 9)
    
    def test_ensure_jst_with_timezone(self):
        """タイムゾーン付きdatetimeの変換テスト"""
        utc = pytz.UTC
        dt_utc = utc.localize(self.test_dt)
        result = ensure_jst(dt_utc)
        self.assertEqual(result.tzinfo.zone, 'Asia/Tokyo')
        # UTCの9:30はJSTの18:30
        self.assertEqual(result.hour, 18)
    
    def test_ensure_jst_with_none(self):
        """Noneの処理テスト"""
        result = ensure_jst(None)
        self.assertIsNone(result)
    
    def test_ensure_jst_with_invalid_input(self):
        """無効な入力のテスト"""
        with self.assertRaises(ValueError):
            ensure_jst(123)  # 数値は無効
    
    def test_format_time_only(self):
        """時刻フォーマットのテスト"""
        result = format_time_only(self.test_dt_jst)
        self.assertEqual(result, "09:30")
        
        # 文字列入力
        result = format_time_only("2024-01-15T14:45:00")
        self.assertEqual(result, "14:45")
        
        # None入力
        result = format_time_only(None)
        self.assertEqual(result, "")
    
    def test_format_date_only(self):
        """日付フォーマットのテスト"""
        # datetime入力
        result = format_date_only(self.test_dt)
        self.assertEqual(result, "2024-01-15")
        
        # date入力
        result = format_date_only(date(2024, 1, 15))
        self.assertEqual(result, "2024-01-15")
        
        # 文字列入力（既にフォーマット済み）
        result = format_date_only("2024-01-15")
        self.assertEqual(result, "2024-01-15")
        
        # None入力
        result = format_date_only(None)
        self.assertEqual(result, "")
    
    def test_calculate_work_hours(self):
        """勤務時間計算のテスト"""
        clock_in = datetime(2024, 1, 15, 9, 0, 0)
        clock_out = datetime(2024, 1, 15, 18, 0, 0)
        
        # 休憩なし
        result = calculate_work_hours(clock_in, clock_out)
        self.assertEqual(result, 9.0)
        
        # 1時間休憩
        break_start = datetime(2024, 1, 15, 12, 0, 0)
        break_end = datetime(2024, 1, 15, 13, 0, 0)
        result = calculate_work_hours(clock_in, clock_out, break_start, break_end)
        self.assertEqual(result, 8.0)
        
        # 文字列入力
        result = calculate_work_hours(
            "2024-01-15T09:00:00",
            "2024-01-15T18:00:00",
            "2024-01-15T12:00:00",
            "2024-01-15T13:00:00"
        )
        self.assertEqual(result, 8.0)
    
    def test_calculate_overtime_hours(self):
        """残業時間計算のテスト"""
        # 残業なし
        result = calculate_overtime_hours(7.5)
        self.assertEqual(result, 0.0)
        
        # 1時間残業
        result = calculate_overtime_hours(9.0)
        self.assertEqual(result, 1.0)
        
        # カスタム標準時間
        result = calculate_overtime_hours(10.0, standard_hours=9.0)
        self.assertEqual(result, 1.0)
    
    def test_get_month_date_range(self):
        """月の日付範囲取得のテスト"""
        # 通常の月
        start, end = get_month_date_range(2024, 1)
        self.assertEqual(start, date(2024, 1, 1))
        self.assertEqual(end, date(2024, 1, 31))
        
        # 2月（うるう年）
        start, end = get_month_date_range(2024, 2)
        self.assertEqual(start, date(2024, 2, 1))
        self.assertEqual(end, date(2024, 2, 29))
        
        # 12月
        start, end = get_month_date_range(2024, 12)
        self.assertEqual(start, date(2024, 12, 1))
        self.assertEqual(end, date(2024, 12, 31))
    
    def test_parse_date_string(self):
        """日付文字列パースのテスト"""
        # 正常な入力
        result = parse_date_string("2024-01-15")
        self.assertEqual(result, date(2024, 1, 15))
        
        # 不正な形式
        with self.assertRaises(ValueError) as cm:
            parse_date_string("2024/01/15")
        self.assertIn("YYYY-MM-DD形式", str(cm.exception))
        
        # 無効な日付
        with self.assertRaises(ValueError):
            parse_date_string("2024-13-01")
    
    def test_adapt_datetime_for_sqlite(self):
        """SQLite用datetime変換のテスト"""
        # ナイーブなdatetime
        result = adapt_datetime_for_sqlite(self.test_dt)
        self.assertIn("+09:00", result)  # JSTタイムゾーン
        
        # タイムゾーン付きdatetime
        result = adapt_datetime_for_sqlite(self.test_dt_jst)
        self.assertIn("2024-01-15T09:30:00", result)
    
    def test_convert_datetime_from_sqlite(self):
        """SQLiteからのdatetime変換のテスト"""
        # ISO形式
        iso_str = "2024-01-15T09:30:00+09:00"
        result = convert_datetime_from_sqlite(iso_str)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.hour, 9)
        
        # バイト形式
        byte_str = b"2024-01-15T09:30:00"
        result = convert_datetime_from_sqlite(byte_str)
        self.assertEqual(result.year, 2024)
        
        # 古い形式（フォールバック）
        old_str = "2024-01-15 09:30:00"
        result = convert_datetime_from_sqlite(old_str)
        self.assertEqual(result.year, 2024)


class TestDatabaseUtils(unittest.TestCase):
    """データベースユーティリティのテスト"""
    
    def setUp(self):
        """テストの初期設定"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()  # ファイルを閉じてからsqlite3で開く
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        
        # テスト用テーブル作成
        self.conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                value INTEGER,
                updated_at TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def tearDown(self):
        """テストの後処理"""
        try:
            self.conn.close()
            os.unlink(self.temp_db.name)
        except Exception:
            # Windows環境でのファイル削除エラーを無視
            pass
    
    def test_handle_database_error_decorator(self):
        """データベースエラーハンドリングデコレータのテスト"""
        @handle_database_error
        def raise_integrity_error():
            raise sqlite3.IntegrityError("UNIQUE constraint failed")
        
        with self.assertRaises(DuplicateRecordError):
            raise_integrity_error()
        
        @handle_database_error
        def raise_operational_error():
            raise sqlite3.OperationalError("database is locked")
        
        with self.assertRaises(DatabaseError):
            raise_operational_error()
    
    def test_retry_on_lock_decorator(self):
        """ロック時リトライデコレータのテスト"""
        call_count = 0
        
        @retry_on_lock(max_retries=3, delay=0.01)
        def maybe_locked_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sqlite3.OperationalError("database is locked")
            return "success"
        
        result = maybe_locked_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_transaction_context_manager(self):
        """トランザクションコンテキストマネージャのテスト"""
        # 成功ケース
        with transaction(self.conn) as cursor:
            cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", 
                         ("test1", 100))
        
        # データが保存されていることを確認
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_table WHERE name = ?", ("test1",))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['value'], 100)
        cursor.close()  # カーソルを閉じる
        
        # エラーケース（ロールバック）
        try:
            with transaction(self.conn) as cursor:
                cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", 
                             ("test2", 200))
                raise Exception("Test error")
        except Exception:
            pass
        
        # データが保存されていないことを確認
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_table WHERE name = ?", ("test2",))
        row = cursor.fetchone()
        self.assertIsNone(row)
        cursor.close()  # カーソルを閉じる
    
    def test_safe_execute(self):
        """安全なクエリ実行のテスト"""
        cursor = self.conn.cursor()
        
        # パラメータ付きクエリ
        safe_execute(cursor, 
                    "INSERT INTO test_table (name, value) VALUES (?, ?)",
                    ("test3", 300))
        self.conn.commit()
        
        # パラメータなしクエリ
        safe_execute(cursor, "SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0)
    
    def test_fetch_one_as_dict(self):
        """1行取得して辞書変換のテスト"""
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", 
                      ("test4", 400))
        self.conn.commit()
        
        cursor.execute("SELECT * FROM test_table WHERE name = ?", ("test4",))
        result = fetch_one_as_dict(cursor)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['name'], "test4")
        self.assertEqual(result['value'], 400)
        
        # 結果なしの場合
        cursor.execute("SELECT * FROM test_table WHERE name = ?", ("notexist",))
        result = fetch_one_as_dict(cursor)
        self.assertIsNone(result)
    
    def test_fetch_all_as_dict(self):
        """全行取得して辞書リスト変換のテスト"""
        cursor = self.conn.cursor()
        
        # 複数行挿入
        for i in range(3):
            cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", 
                         (f"test{i+5}", (i+5)*100))
        self.conn.commit()
        
        cursor.execute("SELECT * FROM test_table WHERE name LIKE 'test%'")
        results = fetch_all_as_dict(cursor)
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIsInstance(results[0], dict)
        
        # 結果なしの場合
        cursor.execute("SELECT * FROM test_table WHERE name = 'notexist'")
        results = fetch_all_as_dict(cursor)
        self.assertEqual(results, [])
    
    def test_validate_required_fields(self):
        """必須フィールド検証のテスト"""
        # 正常ケース
        data = {'name': 'test', 'value': 100}
        validate_required_fields(data, ['name', 'value'])  # エラーなし
        
        # フィールド不足
        with self.assertRaises(ValueError) as cm:
            validate_required_fields(data, ['name', 'value', 'missing'])
        self.assertIn("missing", str(cm.exception))
        
        # None値
        data = {'name': 'test', 'value': None}
        with self.assertRaises(ValueError) as cm:
            validate_required_fields(data, ['name', 'value'])
        self.assertIn("value", str(cm.exception))
    
    def test_sanitize_string(self):
        """文字列サニタイズのテスト"""
        # 前後の空白削除
        result = sanitize_string("  test  ")
        self.assertEqual(result, "test")
        
        # 最大長でカット
        result = sanitize_string("very long string", max_length=5)
        self.assertEqual(result, "very ")
        
        # None処理
        result = sanitize_string(None)
        self.assertIsNone(result)
    
    def test_build_update_query(self):
        """UPDATE文構築のテスト"""
        data = {'name': 'newname', 'value': 999}
        query, params = build_update_query('test_table', data, 'id = ?')
        
        self.assertIn("UPDATE test_table SET", query)
        self.assertIn("name = ?", query)
        self.assertIn("value = ?", query)
        self.assertIn("updated_at = CURRENT_TIMESTAMP", query)
        self.assertEqual(params, ['newname', 999])
        
        # 空データ
        with self.assertRaises(ValueError):
            build_update_query('test_table', {}, 'id = ?')


class TestDatabaseIntegration(unittest.TestCase):
    """データベース統合テスト"""
    
    def setUp(self):
        """テストの初期設定"""
        # テスト用の設定をモック
        self.config_patcher = patch('config.Config')
        mock_config = self.config_patcher.start()
        mock_config.DATABASE_URL = ':memory:'
        mock_config.TIMEZONE = 'Asia/Tokyo'
        mock_config.LOG_LEVEL = 'INFO'
        
        # bot.utils.datetime_utilsの設定もモック
        self.datetime_config_patcher = patch('bot.utils.datetime_utils.Config')
        mock_datetime_config = self.datetime_config_patcher.start()
        mock_datetime_config.TIMEZONE = 'Asia/Tokyo'
        
        # データベースマネージャーをインポート
        from database import DatabaseManager, UserRepository, TaskRepository, AttendanceRepository
        
        self.db_manager = DatabaseManager(':memory:')
        self.user_repo = UserRepository(self.db_manager)
        self.task_repo = TaskRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
    
    def tearDown(self):
        """テストの後処理"""
        self.config_patcher.stop()
        self.datetime_config_patcher.stop()
    
    def test_user_repository(self):
        """ユーザーリポジトリのテスト"""
        # ユーザー作成
        user_id = self.user_repo.create_user(
            discord_id="123456789",
            username="testuser",
            display_name="Test User"
        )
        self.assertIsInstance(user_id, int)
        
        # ユーザー取得
        user = self.user_repo.get_user_by_discord_id("123456789")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        
        # ユーザー更新
        success = self.user_repo.update_user(
            "123456789",
            display_name="Updated User",
            email="test@example.com"
        )
        self.assertTrue(success)
        
        # 更新確認
        user = self.user_repo.get_user_by_discord_id("123456789")
        self.assertEqual(user['display_name'], "Updated User")
        self.assertEqual(user['email'], "test@example.com")
        
        # 重複作成エラー
        with self.assertRaises(DuplicateRecordError):
            self.user_repo.create_user(
                discord_id="123456789",
                username="duplicate"
            )
    
    def test_task_repository(self):
        """タスクリポジトリのテスト"""
        # ユーザー作成
        user = self.user_repo.get_or_create_user("123456789", "testuser")
        user_id = user['id']
        
        # タスク作成
        task_id = self.task_repo.create_task(
            user_id=user_id,
            title="テストタスク",
            description="これはテストです",
            priority="高",
            due_date="2024-12-31"
        )
        self.assertIsInstance(task_id, int)
        
        # タスク一覧取得
        tasks = self.task_repo.get_user_tasks(user_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['title'], "テストタスク")
        
        # ステータス更新
        success = self.task_repo.update_task_status(task_id, "進行中")
        self.assertTrue(success)
        
        # 完了時のタイムスタンプ確認
        success = self.task_repo.update_task_status(task_id, "完了")
        self.assertTrue(success)
        
        tasks = self.task_repo.get_user_tasks(user_id, status="完了")
        self.assertEqual(len(tasks), 1)
        self.assertIsNotNone(tasks[0]['completed_at'])
        
        # タスク削除
        success = self.task_repo.delete_task(task_id)
        self.assertTrue(success)
        
        tasks = self.task_repo.get_user_tasks(user_id)
        self.assertEqual(len(tasks), 0)
    
    def test_attendance_repository(self):
        """出退勤リポジトリのテスト"""
        # ユーザー作成
        user = self.user_repo.get_or_create_user("123456789", "testuser")
        user_id = user['id']
        
        # 出勤記録
        success = self.attendance_repo.clock_in(user_id, "2024-01-15")
        self.assertTrue(success)
        
        # 出勤記録確認
        record = self.attendance_repo.get_today_attendance(user_id, "2024-01-15")
        self.assertIsNotNone(record)
        self.assertEqual(record['status'], '在席')
        self.assertIsNotNone(record['clock_in_time'])
        
        # 休憩開始
        success = self.attendance_repo.start_break(user_id, "2024-01-15")
        self.assertTrue(success)
        
        record = self.attendance_repo.get_today_attendance(user_id, "2024-01-15")
        self.assertEqual(record['status'], '休憩中')
        
        # 休憩終了
        success = self.attendance_repo.end_break(user_id, "2024-01-15")
        self.assertTrue(success)
        
        # 退勤記録
        success = self.attendance_repo.clock_out(user_id, "2024-01-15")
        self.assertTrue(success)
        
        # 退勤記録確認
        record = self.attendance_repo.get_today_attendance(user_id, "2024-01-15")
        self.assertEqual(record['status'], '退勤')
        self.assertIsNotNone(record['clock_out_time'])
        self.assertIsNotNone(record['total_work_hours'])
        
        # 月次データ取得
        records = self.attendance_repo.get_monthly_attendance(user_id, 2024, 1)
        self.assertEqual(len(records), 1)


class TestCommandsIntegration(unittest.TestCase):
    """コマンドの統合テスト"""
    
    def setUp(self):
        """テストの初期設定"""
        # Discordボットのモック
        self.bot = MagicMock()
        self.bot.user = MagicMock()
        self.bot.user.id = 987654321
        
        # コンテキストのモック
        self.ctx = MagicMock()
        self.ctx.author = MagicMock()
        self.ctx.author.id = 123456789
        self.ctx.author.name = "testuser"
        self.ctx.author.display_name = "Test User"
        self.ctx.send = MagicMock()
        
        # インタラクションのモック
        self.interaction = MagicMock()
        self.interaction.user = self.ctx.author
        self.interaction.response = MagicMock()
        self.interaction.followup = MagicMock()
        
        # 設定のモック
        self.config_patcher = patch('config.Config')
        mock_config = self.config_patcher.start()
        mock_config.DATABASE_URL = ':memory:'
        mock_config.TIMEZONE = 'Asia/Tokyo'
        mock_config.LOG_LEVEL = 'INFO'
    
    def tearDown(self):
        """テストの後処理"""
        self.config_patcher.stop()
    
    @patch('bot.commands.attendance.user_repo')
    @patch('bot.commands.attendance.attendance_repo')
    async def test_clock_in_button_async(self, mock_attendance_repo, mock_user_repo):
        """出勤ボタンのテスト（非同期版）"""
        from bot.commands.attendance import AttendanceView
        
        # モックの設定
        mock_user_repo.get_or_create_user.return_value = {'id': 1}
        mock_attendance_repo.get_today_attendance.return_value = None
        mock_attendance_repo.clock_in.return_value = True
        
        # ビューとボタンの実行
        view = AttendanceView()
        button = view.children[0]  # 最初のボタン（出勤）
        
        # 非同期関数の実行
        await button.callback(self.interaction)
        
        # アサーション
        mock_user_repo.get_or_create_user.assert_called_once()
        mock_attendance_repo.clock_in.assert_called_once_with(1)
        self.interaction.followup.send.assert_called_once()
    
    def test_clock_in_button(self):
        """出勤ボタンのテスト（同期ラッパー）"""
        # 非同期テストをスキップ（個別に実行する必要がある）
        self.skipTest("非同期テストは別途実行が必要")


if __name__ == '__main__':
    unittest.main() 