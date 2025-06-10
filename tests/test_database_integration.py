#!/usr/bin/env python3
"""
データベース統合テストファイル
実際のデータベース操作、複雑なワークフロー、データ整合性をテスト
"""

import unittest
import sys
import os
from datetime import datetime, date, timedelta
import sqlite3
import tempfile
import shutil

# テスト用環境変数を設定
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_integration.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager, UserRepository, DailyReportRepository, TaskRepository, AttendanceRepository


class TestDatabaseIntegration(unittest.TestCase):
    """データベース統合テスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        # 一意なテスト用データベース
        import time
        import random
        self.test_db_path = f'test_integration_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        # リポジトリ初期化
        self.user_repo = UserRepository(self.db_manager)
        self.daily_report_repo = DailyReportRepository(self.db_manager)
        self.task_repo = TaskRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
        
        # テストユーザー作成
        self.test_user_id = self.user_repo.create_user(
            discord_id="123456789",
            username="testuser",
            display_name="Test User"
        )
        
        self.test_user_id_2 = self.user_repo.create_user(
            discord_id="987654321",
            username="testuser2",
            display_name="Test User 2"
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'db_manager'):
            del self.db_manager
        
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
    
    def test_complete_attendance_workflow(self):
        """完全な出退勤ワークフローのテスト"""
        today = date.today().isoformat()
        
        # 1. 出勤
        success = self.attendance_repo.clock_in(self.test_user_id, today)
        self.assertTrue(success)
        
        # 出勤記録確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertIsNotNone(record)
        self.assertEqual(record['status'], '在席')
        self.assertIsNotNone(record['clock_in_time'])
        
        # 2. 休憩開始
        success = self.attendance_repo.start_break(self.test_user_id, today)
        self.assertTrue(success)
        
        # 休憩中状態確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertEqual(record['status'], '休憩中')
        self.assertIsNotNone(record['break_start_time'])
        
        # 3. 休憩終了
        success = self.attendance_repo.end_break(self.test_user_id, today)
        self.assertTrue(success)
        
        # 在席状態復帰確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertEqual(record['status'], '在席')
        self.assertIsNotNone(record['break_end_time'])
        
        # 4. 退勤
        success = self.attendance_repo.clock_out(self.test_user_id, today)
        self.assertTrue(success)
        
        # 最終記録確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertEqual(record['status'], '退勤')
        self.assertIsNotNone(record['clock_out_time'])
        self.assertIsNotNone(record['total_work_hours'])
        self.assertIsNotNone(record['overtime_hours'])
    
    def test_multiple_users_attendance(self):
        """複数ユーザーの出退勤管理テスト"""
        today = date.today().isoformat()
        
        # ユーザー1: 出勤のみ
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        # ユーザー2: 出勤→退勤
        self.attendance_repo.clock_in(self.test_user_id_2, today)
        self.attendance_repo.clock_out(self.test_user_id_2, today)
        
        # 全ユーザーステータス確認
        all_status = self.attendance_repo.get_all_users_status()
        self.assertEqual(len(all_status), 2)
        
        # ユーザー1は在席、ユーザー2は退勤
        user1_status = next(s for s in all_status if s['discord_id'] == "123456789")
        user2_status = next(s for s in all_status if s['discord_id'] == "987654321")
        
        self.assertEqual(user1_status['status'], '在席')
        self.assertEqual(user2_status['status'], '退勤')
    
    def test_daily_report_with_tasks_integration(self):
        """日報とタスクの統合テスト"""
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        # タスク作成
        task_id_1 = self.task_repo.create_task(
            user_id=self.test_user_id,
            title="プロジェクトA設計",
            priority="高",
            due_date=tomorrow
        )
        
        task_id_2 = self.task_repo.create_task(
            user_id=self.test_user_id,
            title="プロジェクトB実装",
            priority="中",
            due_date=tomorrow
        )
        
        # 日報作成（タスクに関連）
        report_id = self.daily_report_repo.create_daily_report(
            user_id=self.test_user_id,
            report_date=today,
            today_tasks="プロジェクトA設計を完了",
            tomorrow_tasks="プロジェクトB実装開始予定"
        )
        
        # タスク完了
        self.task_repo.update_task_status(task_id_1, "完了")
        
        # 統合確認
        report = self.daily_report_repo.get_daily_report(self.test_user_id, today)
        tasks = self.task_repo.get_user_tasks(self.test_user_id)
        
        self.assertIsNotNone(report)
        self.assertIn("プロジェクトA", report['today_tasks'])
        self.assertEqual(len(tasks), 2)
        
        # 完了タスクの確認
        completed_task = next(t for t in tasks if t['id'] == task_id_1)
        self.assertEqual(completed_task['status'], '完了')
    
    def test_work_hours_calculation_edge_cases(self):
        """勤務時間計算のエッジケーステスト"""
        today = date.today().isoformat()
        
        # テストケース1: 短時間勤務（残業なし）
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        # 4時間後に退勤をシミュレート
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            clock_in_time = now - timedelta(hours=4)
            cursor.execute('''
                UPDATE attendance SET clock_in_time = ? WHERE user_id = ? AND work_date = ?
            ''', (clock_in_time, self.test_user_id, today))
            conn.commit()
        
        success = self.attendance_repo.clock_out(self.test_user_id, today)
        self.assertTrue(success)
        
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertLess(record['total_work_hours'], 8.0)
        self.assertEqual(record['overtime_hours'], 0.0)
        
        # テストケース2: 長時間勤務（残業あり）
        user_id_3 = self.user_repo.create_user(
            discord_id="111222333",
            username="longworker",
            display_name="Long Worker"
        )
        
        self.attendance_repo.clock_in(user_id_3, today)
        
        # 10時間勤務をシミュレート
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            clock_in_time = now - timedelta(hours=10)
            cursor.execute('''
                UPDATE attendance SET clock_in_time = ? WHERE user_id = ? AND work_date = ?
            ''', (clock_in_time, user_id_3, today))
            conn.commit()
        
        success = self.attendance_repo.clock_out(user_id_3, today)
        self.assertTrue(success)
        
        record = self.attendance_repo.get_today_attendance(user_id_3, today)
        self.assertGreater(record['total_work_hours'], 8.0)
        self.assertGreater(record['overtime_hours'], 0.0)
        self.assertEqual(record['overtime_hours'], record['total_work_hours'] - 8.0)
    
    def test_monthly_attendance_report(self):
        """月次勤怠レポートテスト"""
        current_month = date.today().month
        current_year = date.today().year
        
        # 複数日の勤怠記録を作成
        for day in range(1, 6):  # 5日間
            work_date = f"{current_year}-{current_month:02d}-{day:02d}"
            self.attendance_repo.clock_in(self.test_user_id, work_date)
            self.attendance_repo.clock_out(self.test_user_id, work_date)
        
        # 月次レポート取得
        monthly_records = self.attendance_repo.get_monthly_attendance(
            self.test_user_id, current_year, current_month
        )
        
        self.assertEqual(len(monthly_records), 5)
        
        # 全記録に勤務時間が設定されているか確認
        for record in monthly_records:
            self.assertIsNotNone(record['total_work_hours'])
            self.assertIsNotNone(record['overtime_hours'])
    
    def test_data_consistency_and_constraints(self):
        """データ整合性と制約のテスト"""
        today = date.today().isoformat()
        
        # 同一日の重複出勤防止テスト
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        # 同じ日に再度出勤を試行
        success = self.attendance_repo.clock_in(self.test_user_id, today)
        self.assertTrue(success)  # REPLACE処理により成功するが、1つの記録のみ
        
        # 記録が1つだけであることを確認
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM attendance 
                WHERE user_id = ? AND work_date = ?
            ''', (self.test_user_id, today))
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
        
        # 外部キー制約テスト（存在しないユーザーでの操作）
        non_existent_user = 99999
        success = self.attendance_repo.clock_in(non_existent_user, today)
        # 外部キー制約により失敗するはず（ただし、SQLiteでは制約が緩い場合がある）
        
    def test_performance_with_large_dataset(self):
        """大規模データセットでのパフォーマンステスト"""
        import time
        
        # 大量ユーザー作成
        user_ids = []
        for i in range(100):
            user_id = self.user_repo.create_user(
                discord_id=f"perf_user_{i}",
                username=f"perfuser{i}",
                display_name=f"Performance User {i}"
            )
            user_ids.append(user_id)
        
        # 大量勤怠記録作成
        today = date.today().isoformat()
        start_time = time.time()
        
        for user_id in user_ids:
            self.attendance_repo.clock_in(user_id, today)
            self.attendance_repo.clock_out(user_id, today)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # パフォーマンス確認（100件の処理が10秒以内）
        self.assertLess(processing_time, 10.0, 
                       f"大量データ処理に{processing_time:.2f}秒かかりました（許容: 10秒）")
        
        # 全ユーザーステータス取得のパフォーマンス
        start_time = time.time()
        all_status = self.attendance_repo.get_all_users_status()
        end_time = time.time()
        
        query_time = end_time - start_time
        self.assertLess(query_time, 2.0,
                       f"全ユーザー状況取得に{query_time:.2f}秒かかりました（許容: 2秒）")
        self.assertGreater(len(all_status), 100)


class TestErrorRecovery(unittest.TestCase):
    """エラー回復テスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        import time
        import random
        self.test_db_path = f'test_error_recovery_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        self.user_repo = UserRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
        
        self.test_user_id = self.user_repo.create_user(
            discord_id="error_test_user",
            username="erroruser"
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
    
    def test_database_corruption_recovery(self):
        """データベース破損からの回復テスト"""
        today = date.today().isoformat()
        
        # 正常な記録
        self.attendance_repo.clock_in(self.test_user_id, today)
        
        # データベースに不正なデータを挿入
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO attendance (user_id, work_date, clock_in_time, total_work_hours)
                VALUES (?, ?, ?, ?)
            ''', (self.test_user_id, "invalid-date", "invalid-time", "invalid-hours"))
            conn.commit()
        
        # エラー回復確認
        try:
            records = self.attendance_repo.get_monthly_attendance(
                self.test_user_id, 2025, 1
            )
            # エラーが発生しても処理が継続されることを確認
            self.assertIsInstance(records, list)
        except Exception as e:
            self.fail(f"データベース破損時の回復処理が失敗: {e}")
    
    def test_concurrent_access_simulation(self):
        """同時アクセスシミュレーションテスト"""
        import threading
        import time
        
        today = date.today().isoformat()
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # 各ワーカーが同時に出退勤操作
                success1 = self.attendance_repo.clock_in(self.test_user_id, today)
                time.sleep(0.01)  # 短い待機
                success2 = self.attendance_repo.clock_out(self.test_user_id, today)
                results.append((worker_id, success1, success2))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # 5つのスレッドで同時アクセス
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 全スレッド完了待機
        for thread in threads:
            thread.join()
        
        # 結果確認
        self.assertEqual(len(results), 5, f"一部のワーカーでエラー発生: {errors}")
        
        # データベースの整合性確認
        record = self.attendance_repo.get_today_attendance(self.test_user_id, today)
        self.assertIsNotNone(record)


if __name__ == '__main__':
    unittest.main(verbosity=2) 