import unittest
import asyncio
import sys
import os

# テスト用環境変数を設定（他のインポートより前に設定）
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager, UserRepository, TaskRepository
from config import Config

class TestDatabaseBasic(unittest.TestCase):
    """データベース基本機能のテスト"""
    
    def setUp(self):
        """テスト前のセットアップ"""
        # 一意なテスト用データベースを使用
        import time
        import random
        self.test_db_path = f'test_discord_bot_{int(time.time())}_{random.randint(1000, 9999)}.db'
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.db_manager.init_database()
        
        self.user_repo = UserRepository(self.db_manager)
        self.task_repo = TaskRepository(self.db_manager)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # データベース接続を確実に閉じる
        if hasattr(self, 'db_manager'):
            # すべての接続を閉じる
            del self.db_manager
        
        # ファイルを削除
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except PermissionError:
            # Windowsで削除できない場合は少し待ってから再試行
            import time
            time.sleep(0.1)
            try:
                if os.path.exists(self.test_db_path):
                    os.remove(self.test_db_path)
            except:
                pass  # 削除できなくても続行
    
    def test_user_operations(self):
        """ユーザー操作のテスト"""
        # ユーザー作成
        user_id = self.user_repo.create_user(
            discord_id="123456789",
            username="testuser",
            display_name="Test User"
        )
        self.assertIsNotNone(user_id)
        
        # ユーザー取得
        user = self.user_repo.get_user_by_discord_id("123456789")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        
        # ユーザー更新
        success = self.user_repo.update_user("123456789", username="newuser", display_name="New User")
        self.assertTrue(success)
        
        # 更新確認
        user = self.user_repo.get_user_by_discord_id("123456789")
        self.assertEqual(user['username'], "newuser")
    
    def test_task_operations(self):
        """タスク操作のテスト"""
        # ユーザー作成
        self.user_repo.create_user(
            discord_id="123456789",
            username="testuser"
        )
        
        # タスク作成
        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        task_id = self.task_repo.create_task(
            user_id=1,
            title="テストタスク",
            due_date=tomorrow,
            priority="高"
        )
        self.assertIsNotNone(task_id)
        
        # タスク取得
        tasks = self.task_repo.get_user_tasks(1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['title'], "テストタスク")
        
        # タスク完了
        success = self.task_repo.update_task_status(task_id, "完了")
        self.assertTrue(success)

class TestConfig(unittest.TestCase):
    """設定のテスト"""
    
    def test_config_loading(self):
        """設定読み込みのテスト"""
        # 基本設定が読み込まれているかチェック
        self.assertIsNotNone(Config.DATABASE_URL)
        self.assertIsNotNone(Config.TIMEZONE)
        self.assertIsNotNone(Config.LOG_LEVEL)

class TestBotCommands(unittest.TestCase):
    """Botコマンドの基本テスト"""
    
    def test_command_imports(self):
        """コマンドモジュールがインポートできるかテスト"""
        try:
            from bot.commands import task_manager, attendance, admin, help
            from bot.utils import google_api
            # インポートが成功すれば合格
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"コマンドモジュールのインポートに失敗: {e}")

def run_tests():
    """テストの実行"""
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestBotCommands))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 