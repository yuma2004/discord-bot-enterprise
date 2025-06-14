#!/usr/bin/env python3
"""
安全なテスト実行スクリプト
依存関係の問題を回避してテストを実行
"""

import sys
import os
import unittest
import importlib.util
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath('.'))

# 環境変数設定
os.environ.setdefault('DISCORD_TOKEN', 'test_token_12345')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('TIMEZONE', 'Asia/Tokyo')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# 外部依存のモック設定
def setup_mocks():
    """外部依存モジュールのモック設定"""
    
    # dotenv モック
    dotenv_mock = MagicMock()
    dotenv_mock.load_dotenv = MagicMock()
    sys.modules['dotenv'] = dotenv_mock
    
    # discord.py モック
    discord_mock = MagicMock()
    discord_mock.Intents.default.return_value = MagicMock()
    sys.modules['discord'] = discord_mock
    sys.modules['discord.ext'] = MagicMock()
    sys.modules['discord.ext.commands'] = MagicMock()
    
    # Flask モック
    flask_mock = MagicMock()
    sys.modules['flask'] = flask_mock
    sys.modules['Flask'] = MagicMock()
    
    # pytz モック
    import datetime
    
    class MockTimezone:
        def localize(self, dt):
            return dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        
        def __call__(self, *args):
            return datetime.timezone(datetime.timedelta(hours=9))
    
    pytz_mock = MagicMock()
    pytz_mock.timezone.return_value = MockTimezone()
    sys.modules['pytz'] = pytz_mock
    
    # google-api モック
    sys.modules['googleapiclient'] = MagicMock()
    sys.modules['google.auth'] = MagicMock()

def run_test_module(test_file):
    """指定されたテストモジュールを実行"""
    try:
        # モジュールをインポート
        spec = importlib.util.spec_from_file_location("test_module", test_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # テストスイートを作成
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # テストを実行
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 安全なテスト実行開始")
    
    # モック設定
    setup_mocks()
    
    # テストファイルリスト
    test_files = [
        "tests/test_basic.py",
        "tests/test_database_integration.py", 
        "tests/test_attendance.py",
        "tests/test_error_handling.py"
    ]
    
    # 各テストを実行
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n{'='*60}")
            print(f"🧪 実行中: {test_file}")
            print(f"{'='*60}")
            
            result = run_test_module(test_file)
            
            if result:
                print(f"✅ {test_file}: {result.testsRun}個のテスト実行")
                if result.failures:
                    print(f"❌ 失敗: {len(result.failures)}個")
                if result.errors:
                    print(f"🔥 エラー: {len(result.errors)}個") 
            else:
                print(f"❌ {test_file}: 実行失敗")
        else:
            print(f"⚠️ {test_file}: ファイルが見つかりません")
    
    print(f"\n🏁 テスト実行完了")