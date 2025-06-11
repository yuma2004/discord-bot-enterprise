#!/usr/bin/env python3
"""
データベース統合テストファイル
実際のデータベース操作、複雑なワークフロー、データ整合性をテスト
"""

import unittest
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
import sqlite3
import tempfile
import shutil

# テスト用環境変数を設定
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager, UserRepository, TaskRepository, AttendanceRepository


class TestDatabaseIntegration(unittest.TestCase):
    """統合的なデータベーステスト"""
    
    def setUp(self):
        """テストセットアップ"""
        import time
        import random
        
        # 一意なテスト用データベースを作成
        self.test_db_path = f'integration_test_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        # リポジトリ
        self.user_repo = UserRepository(self.db_manager)
        self.task_repo = TaskRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
        
        # テストユーザー作成
        self.test_user_id = self.user_repo.create_user(
            discord_id="123456789",
            username="testuser",
            display_name="Test User"
        )
        
        self.test_user2_id = self.user_repo.create_user(
            discord_id="987654321",
            username="testuser2", 
            display_name="Test User 2"
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # データベース接続を確実に閉じる
        if hasattr(self, 'db_manager'):
            del self.db_manager
        
        # ファイルを削除
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except PermissionError:
            import time
            time.sleep(0.1)
            try:
                if os.path.exists(self.test_db_path):
                    os.remove(self.test_db_path)
            except:
                pass
    
    def test_multi_user_attendance_workflow(self):
        """複数ユーザーの出退勤ワークフローテスト"""
        today = date.today().isoformat()
        
        # User1の出勤
        success = self.attendance_repo.clock_in(self.test_user_id, today)
        self.assertTrue(success)
        
        # User2の出勤
        success = self.attendance_repo.clock_in(self.test_user2_id, today)
        self.assertTrue(success)
        
        # User1の休憩開始
        success = self.attendance_repo.start_break(self.test_user_id, today)
        self.assertTrue(success)
        
        # User1の休憩終了
        success = self.attendance_repo.end_break(self.test_user_id, today)
        self.assertTrue(success)
        
        # User1の退勤
        success = self.attendance_repo.clock_out(self.test_user_id, today)
        self.assertTrue(success)
        
        # ステータス確認
        all_status = self.attendance_repo.get_all_users_status()
        self.assertEqual(len(all_status), 2)
        
        # User1は退勤、User2は在席であることを確認
        user1_status = next((u for u in all_status if u['discord_id'] == "123456789"), None)
        user2_status = next((u for u in all_status if u['discord_id'] == "987654321"), None)
        
        self.assertIsNotNone(user1_status)
        self.assertIsNotNone(user2_status)
        self.assertEqual(user1_status['status'], '退勤')
        self.assertEqual(user2_status['status'], '在席')
    
    def test_attendance_csv_data_workflow(self):
        """CSV出力用データの統合テスト"""
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        # 昨日と今日の勤怠記録を作成
        for work_date in [yesterday, today]:
            for user_id in [self.test_user_id, self.test_user2_id]:
                # 出勤
                self.attendance_repo.clock_in(user_id, work_date)
                # 退勤
                self.attendance_repo.clock_out(user_id, work_date)
        
        # CSV用データ取得
        csv_data = self.attendance_repo.get_attendance_range(yesterday, today)
        
        # 4レコード（2ユーザー x 2日）が取得されることを確認
        self.assertEqual(len(csv_data), 4)
        
        # 必要なフィールドが含まれていることを確認
        required_fields = ['date', 'username', 'display_name', 'clock_in_time', 'clock_out_time', 'total_work_hours']
        for record in csv_data:
            for field in required_fields:
                self.assertIn(field, record, f"フィールド '{field}' が見つかりません")
    
    def test_task_and_user_integration(self):
        """タスクとユーザーの統合テスト"""
        # 複数のタスクを作成
        task_titles = ["タスク1", "タスク2", "タスク3"]
        created_tasks = []
        
        for title in task_titles:
            task_id = self.task_repo.create_task(
                user_id=self.test_user_id,
                title=title,
                priority="中",
                due_date=(date.today() + timedelta(days=1)).isoformat()
            )
            created_tasks.append(task_id)
        
        # タスク取得
        tasks = self.task_repo.get_user_tasks(self.test_user_id)
        self.assertEqual(len(tasks), 3)
        
        # タスクの完了
        success = self.task_repo.update_task_status(created_tasks[0], "完了")
        self.assertTrue(success)
        
        # 未完了タスクの確認
        pending_tasks = self.task_repo.get_user_tasks(self.test_user_id, status="未着手")
        self.assertEqual(len(pending_tasks), 2)
        
        # 期限が近いタスクの確認
        due_soon_tasks = self.task_repo.get_tasks_due_soon(days=2)
        self.assertEqual(len(due_soon_tasks), 2)  # 完了済みを除く2件
    
    def test_concurrent_database_operations(self):
        """並行データベース操作のテスト"""
        today = date.today().isoformat()
        
        # 同時に複数の操作を実行
        operations = [
            lambda: self.attendance_repo.clock_in(self.test_user_id, today),
            lambda: self.task_repo.create_task(self.test_user_id, "並行タスク1"),
            lambda: self.task_repo.create_task(self.test_user2_id, "並行タスク2"),
            lambda: self.attendance_repo.clock_in(self.test_user2_id, today),
        ]
        
        # 全ての操作を実行
        results = []
        for operation in operations:
            try:
                result = operation()
                results.append(result)
            except Exception as e:
                self.fail(f"並行操作でエラー: {e}")
        
        # 全ての操作が成功することを確認
        self.assertEqual(len([r for r in results if r]), 4)
    
    def test_database_schema_consistency(self):
        """データベーススキーマの一貫性テスト"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # テーブルの存在確認
            expected_tables = ['users', 'tasks', 'attendance', 'settings']
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = [row[0] for row in cursor.fetchall()]
            
            for table in expected_tables:
                self.assertIn(table, actual_tables, f"テーブル '{table}' が見つかりません")
            
            # 外部キー制約の確認
            cursor.execute("PRAGMA foreign_key_list(tasks)")
            fk_constraints = cursor.fetchall()
            self.assertGreater(len(fk_constraints), 0, "tasksテーブルに外部キー制約がありません")
            
            cursor.execute("PRAGMA foreign_key_list(attendance)")
            fk_constraints = cursor.fetchall()
            self.assertGreater(len(fk_constraints), 0, "attendanceテーブルに外部キー制約がありません")
    
    def test_data_type_consistency(self):
        """データ型の一貫性テスト"""
        # 日時データの一貫性
        today = date.today().isoformat()
        
        # 出勤記録
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        # 記録確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertIsNotNone(record)
        
        # 日時フィールドのタイプチェック
        clock_in_time = record['clock_in_time']
        
        # 文字列またはdatetimeオブジェクトであることを確認
        self.assertTrue(
            isinstance(clock_in_time, (str, datetime)),
            f"clock_in_timeの型が不正: {type(clock_in_time)}"
        )
        
        # 文字列の場合はISO形式であることを確認
        if isinstance(clock_in_time, str):
            try:
                datetime.fromisoformat(clock_in_time)
            except ValueError:
                self.fail(f"clock_in_timeが不正なISO形式: {clock_in_time}")
    
    def test_edge_cases_handling(self):
        """エッジケースの処理テスト"""
        # 存在しないユーザーでの操作
        today = date.today().isoformat()
        
        # 存在しないユーザーの出勤試行
        result = self.attendance_repo.clock_in(99999, today)
        # エラーが発生しないことを確認（ユーザー作成/取得は呼び出し元の責任）
        self.assertTrue(isinstance(result, bool))
        
        # 出勤していないユーザーの退勤試行
        result = self.attendance_repo.clock_out(self.test_user2_id, today)
        self.assertFalse(result)  # 失敗することを確認
        
        # 重複する出勤記録
        self.attendance_repo.clock_in(self.test_user_id, today)
        result = self.attendance_repo.clock_in(self.test_user_id, today)  # 再度出勤
        self.assertTrue(result)  # INSERT OR REPLACEで成功するはず
    
    def test_performance_with_large_dataset(self):
        """大量データでのパフォーマンステスト"""
        import time
        
        # 大量のユーザー作成
        user_ids = []
        start_time = time.time()
        
        for i in range(100):
            user_id = self.user_repo.create_user(
                discord_id=f"user_{i}",
                username=f"testuser_{i}"
            )
            user_ids.append(user_id)
        
        creation_time = time.time() - start_time
        
        # パフォーマンス基準（100ユーザー作成が3秒以内）
        self.assertLess(creation_time, 3.0, f"ユーザー作成が遅すぎます: {creation_time:.2f}秒")
        
        # 大量データの取得
        start_time = time.time()
        all_status = self.attendance_repo.get_all_users_status()
        query_time = time.time() - start_time
        
        # 102ユーザー（初期2 + 追加100）が取得されることを確認
        self.assertEqual(len(all_status), 102)
        
        # パフォーマンス基準（100ユーザーの状況取得が1秒以内）
        self.assertLess(query_time, 1.0, f"ステータス取得が遅すぎます: {query_time:.2f}秒")

def run_integration_tests():
    """統合テストの実行"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDatabaseIntegration)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1) 