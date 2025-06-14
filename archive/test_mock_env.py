#!/usr/bin/env python3
"""
テスト用の環境セットアップ
外部依存なしでテストを実行するためのモック
"""

import os
import sys
from unittest.mock import MagicMock

# 必要な環境変数を設定
os.environ.setdefault('DISCORD_TOKEN', 'test_token_12345')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_discord_bot.db')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('TIMEZONE', 'Asia/Tokyo')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# dotenvモジュールのモック
class MockDotenv:
    @staticmethod
    def load_dotenv():
        pass

sys.modules['dotenv'] = MockDotenv()

# discord.pyモジュールのモック
class MockDiscord:
    class Intents:
        @staticmethod
        def default():
            return MagicMock()
    
    class commands:
        class Bot:
            def __init__(self, **kwargs):
                pass
        
        class Cog:
            def __init__(self, bot):
                pass

sys.modules['discord'] = MockDiscord()
sys.modules['discord.ext'] = MagicMock()
sys.modules['discord.ext.commands'] = MockDiscord.commands

# Flaskモジュールのモック
class MockFlask:
    def __init__(self, name):
        pass
    
    def route(self, path):
        def decorator(func):
            return func
        return decorator
    
    def run(self, **kwargs):
        pass

sys.modules['flask'] = MagicMock()
sys.modules['Flask'] = MockFlask

# pytzモジュールのモック
class MockPytz:
    @staticmethod
    def timezone(tz_name):
        return MagicMock()

sys.modules['pytz'] = MockPytz()

print("✅ テスト用環境セットアップ完了")