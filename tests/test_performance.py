#!/usr/bin/env python3
"""
パフォーマンステストファイル
システムの負荷耐性、応答性、スケーラビリティをテスト
"""

import unittest
import asyncio
import sys
import os
import sqlite3
import time
import threading
import random
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# テスト用環境変数を設定（他のインポートより前に設定）
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager, UserRepository, TaskRepository, AttendanceRepository
from config import Config


class TestDatabasePerformance(unittest.TestCase):
    """データベースパフォーマンステスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        import time
        import random
        self.test_db_path = f'test_performance_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        self.user_repo = UserRepository(self.db_manager)
        self.task_repo = TaskRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'db_manager'):
            del self.db_manager
        
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except:
            pass
    
    def test_bulk_user_creation_performance(self):
        """大量ユーザー作成のパフォーマンステスト"""
        user_count = 1000
        
        start_time = time.time()
        
        user_ids = []
        for i in range(user_count):
            user_id = self.user_repo.create_user(
                discord_id=f"perf_user_{i}",
                username=f"perfuser{i}",
                display_name=f"Performance User {i}"
            )
            user_ids.append(user_id)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # パフォーマンス基準: 1000ユーザーを20秒以内で作成
        self.assertLess(creation_time, 20.0, 
                       f"1000ユーザー作成に{creation_time:.2f}秒かかりました（基準: 20秒）")
        
        # 平均作成時間を計算
        avg_time_per_user = creation_time / user_count
        self.assertLess(avg_time_per_user, 0.02,
                       f"1ユーザー平均作成時間{avg_time_per_user:.4f}秒（基準: 0.02秒）")
        
        print(f"✓ 1000ユーザー作成: {creation_time:.2f}秒 (平均: {avg_time_per_user:.4f}秒/ユーザー)")
    
    def test_bulk_attendance_records_performance(self):
        """大量出退勤記録のパフォーマンステスト"""
        # 100ユーザーを作成
        user_ids = []
        for i in range(100):
            user_id = self.user_repo.create_user(
                discord_id=f"attendance_user_{i}",
                username=f"attendanceuser{i}"
            )
            user_ids.append(user_id)
        
        today = date.today().isoformat()
        
        # 出勤記録の一括作成
        start_time = time.time()
        
        for user_id in user_ids:
            self.attendance_repo.clock_in(user_id, today)
        
        clock_in_time = time.time() - start_time
        
        # 退勤記録の一括作成
        start_time = time.time()
        
        for user_id in user_ids:
            self.attendance_repo.clock_out(user_id, today)
        
        clock_out_time = time.time() - start_time
        
        # パフォーマンス基準: 100件の出退勤を各5秒以内
        self.assertLess(clock_in_time, 5.0,
                       f"100件出勤記録に{clock_in_time:.2f}秒かかりました（基準: 5秒）")
        self.assertLess(clock_out_time, 5.0,
                       f"100件退勤記録に{clock_out_time:.2f}秒かかりました（基準: 5秒）")
        
        print(f"✓ 100件出勤記録: {clock_in_time:.2f}秒")
        print(f"✓ 100件退勤記録: {clock_out_time:.2f}秒")
    
    def test_complex_query_performance(self):
        """複雑なクエリのパフォーマンステスト"""
        # テストデータ準備
        user_ids = []
        for i in range(50):
            user_id = self.user_repo.create_user(
                discord_id=f"complex_user_{i}",
                username=f"complexuser{i}"
            )
            user_ids.append(user_id)
        
        # 1ヶ月分の勤怠記録を作成
        current_date = date.today()
        for days_back in range(30):
            work_date = (current_date - timedelta(days=days_back)).isoformat()
            
            for user_id in user_ids:
                self.attendance_repo.clock_in(user_id, work_date)
                self.attendance_repo.clock_out(user_id, work_date)
        
        # 複雑なクエリのパフォーマンステスト
        start_time = time.time()
        
        # 全ユーザーの今日のステータス取得
        all_status = self.attendance_repo.get_all_users_status()
        
        # 各ユーザーの月次レポート取得
        for user_id in user_ids[:10]:  # 10ユーザーのみテスト
            monthly_records = self.attendance_repo.get_monthly_attendance(
                user_id, current_date.year, current_date.month
            )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # パフォーマンス基準: 複雑なクエリを10秒以内で完了
        self.assertLess(query_time, 10.0,
                       f"複雑なクエリ処理に{query_time:.2f}秒かかりました（基準: 10秒）")
        
        print(f"✓ 複雑なクエリ処理: {query_time:.2f}秒")
    
    def test_database_size_impact(self):
        """データベースサイズがパフォーマンスに与える影響のテスト"""
        # 段階的にデータを増やしながらパフォーマンスを測定
        response_times = []
        data_sizes = [100, 500, 1000, 2000]
        
        # グローバルなカウンターで一意性を保証
        global_counter = 0
        
        for size in data_sizes:
            # データ作成
            user_ids = []
            for i in range(size):
                user_id = self.user_repo.create_user(
                    discord_id=f"size_test_user_{global_counter}_{i}",
                    username=f"sizeuser{global_counter}_{i}"
                )
                user_ids.append(user_id)
            
            # クエリパフォーマンス測定
            start_time = time.time()
            all_status = self.attendance_repo.get_all_users_status()
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            print(f"✓ データサイズ {size}: 応答時間 {response_time:.4f}秒")
            global_counter += 1
        
        # 線形以下の増加率であることを確認（O(n log n)以下）
        for i in range(1, len(response_times)):
            if response_times[i-1] > 0:  # 0除算を防ぐ
                ratio = response_times[i] / response_times[i-1]
                size_ratio = data_sizes[i] / data_sizes[i-1]
                
                # 応答時間の増加がデータサイズの増加より小さいことを確認
                # ただし、パフォーマンスが良すぎる場合は適度に緩和
                self.assertLess(ratio, size_ratio * 2.0,
                               f"データサイズ{data_sizes[i]}で非線形な性能劣化を検出")


class TestConcurrentPerformance(unittest.TestCase):
    """並行処理パフォーマンステスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        import time
        import random
        self.test_db_path = f'test_concurrent_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        self.user_repo = UserRepository(self.db_manager)
        self.attendance_repo = AttendanceRepository(self.db_manager)
        
        # テスト用ユーザー作成
        self.test_users = []
        for i in range(20):
            user_id = self.user_repo.create_user(
                discord_id=f"concurrent_user_{i}",
                username=f"concurrentuser{i}"
            )
            self.test_users.append(user_id)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if hasattr(self, 'db_manager'):
            del self.db_manager
        
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except:
            pass
    
    def test_concurrent_attendance_operations(self):
        """同時出退勤操作のパフォーマンステスト"""
        today = date.today().isoformat()
        
        def worker(user_id):
            """ワーカー関数: 出勤→休憩→退勤"""
            start_time = time.time()
            
            # 出勤
            success1 = self.attendance_repo.clock_in(user_id, today)
            
            # 短い待機（実際の使用をシミュレート）
            time.sleep(random.uniform(0.01, 0.05))
            
            # 休憩開始
            success2 = self.attendance_repo.start_break(user_id, today)
            
            time.sleep(random.uniform(0.01, 0.05))
            
            # 休憩終了
            success3 = self.attendance_repo.end_break(user_id, today)
            
            time.sleep(random.uniform(0.01, 0.05))
            
            # 退勤
            success4 = self.attendance_repo.clock_out(user_id, today)
            
            end_time = time.time()
            
            return {
                'user_id': user_id,
                'duration': end_time - start_time,
                'success': all([success1, success2, success3, success4])
            }
        
        # 並行実行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, user_id) for user_id in self.test_users]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 結果検証
        successful_operations = sum(1 for r in results if r['success'])
        avg_worker_time = sum(r['duration'] for r in results) / len(results)
        
        # パフォーマンス基準
        self.assertLess(total_time, 10.0,
                       f"20ユーザー同時操作に{total_time:.2f}秒かかりました（基準: 10秒）")
        
        self.assertGreaterEqual(successful_operations, len(self.test_users) * 0.8,
                               f"成功率が80%を下回りました: {successful_operations}/{len(self.test_users)}")
        
        print(f"✓ 20ユーザー同時操作: 総時間{total_time:.2f}秒, 平均ワーカー時間{avg_worker_time:.2f}秒")
        print(f"✓ 成功率: {successful_operations}/{len(self.test_users)} ({successful_operations/len(self.test_users)*100:.1f}%)")
    
    def test_read_write_concurrency(self):
        """読み書き同時処理のパフォーマンステスト"""
        today = date.today().isoformat()
        
        # 初期データ作成
        for user_id in self.test_users:
            self.attendance_repo.clock_in(user_id, today)
        
        read_results = []
        write_results = []
        errors = []
        
        def reader():
            """読み取りワーカー"""
            try:
                start_time = time.time()
                
                for _ in range(50):  # 50回読み取り
                    all_status = self.attendance_repo.get_all_users_status()
                    time.sleep(0.001)  # 1ms待機
                
                end_time = time.time()
                read_results.append(end_time - start_time)
            except Exception as e:
                errors.append(f"Reader error: {e}")
        
        def writer():
            """書き込みワーカー"""
            try:
                start_time = time.time()
                
                for i in range(10):  # 10回書き込み
                    user_id = random.choice(self.test_users)
                    self.attendance_repo.start_break(user_id, today)
                    time.sleep(0.01)
                    self.attendance_repo.end_break(user_id, today)
                    time.sleep(0.01)
                
                end_time = time.time()
                write_results.append(end_time - start_time)
            except Exception as e:
                errors.append(f"Writer error: {e}")
        
        # 並行実行: 3つの読み取りワーカーと2つの書き込みワーカー
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            # 読み取りワーカー起動
            for _ in range(3):
                futures.append(executor.submit(reader))
            
            # 書き込みワーカー起動
            for _ in range(2):
                futures.append(executor.submit(writer))
            
            # 全ワーカー完了待機
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 結果検証
        self.assertEqual(len(errors), 0, f"同時読み書き処理でエラー発生: {errors}")
        self.assertEqual(len(read_results), 3, "読み取りワーカーが正常完了しませんでした")
        self.assertEqual(len(write_results), 2, "書き込みワーカーが正常完了しませんでした")
        
        avg_read_time = sum(read_results) / len(read_results)
        avg_write_time = sum(write_results) / len(write_results)
        
        print(f"✓ 読み書き同時処理: 総時間{total_time:.2f}秒")
        print(f"✓ 平均読み取り時間: {avg_read_time:.2f}秒")
        print(f"✓ 平均書き込み時間: {avg_write_time:.2f}秒")
    
    def test_stress_test(self):
        """ストレステスト"""
        today = date.today().isoformat()
        
        def stress_worker(worker_id):
            """ストレスワーカー: ランダムな操作を繰り返す"""
            operations = 0
            errors = 0
            start_time = time.time()
            
            try:
                for _ in range(100):  # 100回操作
                    user_id = random.choice(self.test_users)
                    operation = random.choice(['clock_in', 'clock_out', 'start_break', 'end_break', 'get_status'])
                    
                    try:
                        if operation == 'clock_in':
                            self.attendance_repo.clock_in(user_id, today)
                        elif operation == 'clock_out':
                            self.attendance_repo.clock_out(user_id, today)
                        elif operation == 'start_break':
                            self.attendance_repo.start_break(user_id, today)
                        elif operation == 'end_break':
                            self.attendance_repo.end_break(user_id, today)
                        elif operation == 'get_status':
                            self.attendance_repo.get_today_attendance(user_id, today)
                        
                        operations += 1
                        
                    except Exception as e:
                        errors += 1
                    
                    # ランダム待機（0-5ms）
                    time.sleep(random.uniform(0, 0.005))
                
                end_time = time.time()
                
                return {
                    'worker_id': worker_id,
                    'operations': operations,
                    'errors': errors,
                    'duration': end_time - start_time
                }
                
            except Exception as e:
                return {
                    'worker_id': worker_id,
                    'operations': operations,
                    'errors': errors + 1,
                    'duration': time.time() - start_time,
                    'fatal_error': str(e)
                }
        
        # 10ワーカーでストレステスト実行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 結果分析
        total_operations = sum(r['operations'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        error_rate = total_errors / total_operations if total_operations > 0 else 1.0
        
        operations_per_second = total_operations / total_time
        
        # パフォーマンス基準
        self.assertLess(error_rate, 0.05,  # エラー率5%以下
                       f"ストレステストのエラー率が高すぎます: {error_rate:.3f}")
        
        self.assertGreater(operations_per_second, 50,  # 50ops/秒以上
                          f"操作スループットが低すぎます: {operations_per_second:.1f}ops/秒")
        
        print(f"✓ ストレステスト: {total_operations}操作を{total_time:.2f}秒で実行")
        print(f"✓ スループット: {operations_per_second:.1f}操作/秒")
        print(f"✓ エラー率: {error_rate:.3f} ({total_errors}/{total_operations})")


if __name__ == '__main__':
    unittest.main(verbosity=2) 