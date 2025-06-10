import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:
    """アプリケーション設定管理クラス"""
    
    # Discord設定
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    DISCORD_GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 0))
    
    # Google API設定
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
    
    # データベース設定
    DATABASE_URL = os.getenv('DATABASE_URL', 'discord_bot.db')
    
    # アプリケーション設定
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tokyo')
    DAILY_REPORT_TIME = os.getenv('DAILY_REPORT_TIME', '17:00')
    MEETING_REMINDER_MINUTES = int(os.getenv('MEETING_REMINDER_MINUTES', 15))
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_config(cls):
        """設定の妥当性をチェック"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN が設定されていません")
        
        if cls.DISCORD_GUILD_ID == 0:
            raise ValueError("DISCORD_GUILD_ID が設定されていません")
        
        print("設定の検証が完了しました")
        return True 