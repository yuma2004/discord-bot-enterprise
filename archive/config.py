"""
アプリケーション設定管理
リファクタリング版 - 型安全性とエラーハンドリング改善
"""
import logging
import os
from typing import Dict, List

# Try to load dotenv if available, but continue without it
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Continue without dotenv
    pass

# Local utility functions to avoid circular imports
def safe_getenv(key: str, default: str = '', required: bool = False) -> str:
    """安全な環境変数取得"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"必須の環境変数 '{key}' が設定されていません")
    return value or default

def validate_log_level(level: str) -> str:
    """ログレベルの検証"""
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    level_upper = level.upper()
    if level_upper not in valid_levels:
        level_upper = 'INFO'  # Fallback to INFO instead of raising error
    return level_upper

class ValidationError(Exception):
    """設定検証エラー"""
    pass

logger = logging.getLogger(__name__)


class Config:
    """アプリケーション設定管理クラス"""
    
    # Discord設定
    DISCORD_TOKEN: str = safe_getenv('DISCORD_TOKEN', '')  # Remove required=True for import
    DISCORD_GUILD_ID: int = int(safe_getenv('DISCORD_GUILD_ID', '0'))
    
    # Google API設定
    GOOGLE_CLIENT_ID: str = safe_getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = safe_getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_CALENDAR_ID: str = safe_getenv('GOOGLE_CALENDAR_ID', '')
    
    # データベース設定
    DATABASE_URL: str = safe_getenv('DATABASE_URL', 'discord_bot.db')
    
    # アプリケーション設定
    ENVIRONMENT: str = safe_getenv('ENVIRONMENT', 'development')
    TIMEZONE: str = safe_getenv('TIMEZONE', 'Asia/Tokyo')
    DAILY_REPORT_TIME: str = safe_getenv('DAILY_REPORT_TIME', '17:00')
    MEETING_REMINDER_MINUTES: int = int(safe_getenv('MEETING_REMINDER_MINUTES', '15'))
    
    # ログ設定
    LOG_LEVEL: str = validate_log_level(safe_getenv('LOG_LEVEL', 'INFO'))
    
    # ヘルスチェック設定
    HEALTH_CHECK_PORT: int = int(safe_getenv('HEALTH_CHECK_PORT', '8000'))
    
    @classmethod
    def validate_config(cls) -> bool:
        """設定の妥当性をチェック"""
        errors: List[str] = []
        
        # 必須設定の確認
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN が設定されていません (main.py実行時に必要)")
        
        if cls.DISCORD_GUILD_ID == 0:
            errors.append("DISCORD_GUILD_ID が設定されていません")
        
        # 環境設定の確認
        valid_environments = ['development', 'staging', 'production']
        if cls.ENVIRONMENT not in valid_environments:
            logger.warning(f"未知の環境設定: {cls.ENVIRONMENT}")
        
        # タイムゾーンの簡易検証
        if cls.TIMEZONE and '/' not in cls.TIMEZONE:
            logger.warning(f"タイムゾーン '{cls.TIMEZONE}' の形式を確認してください")
        
        # 時刻形式の検証
        try:
            hour, minute = cls.DAILY_REPORT_TIME.split(':')
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                errors.append(f"DAILY_REPORT_TIME の形式が無効です: {cls.DAILY_REPORT_TIME}")
        except ValueError:
            errors.append(f"DAILY_REPORT_TIME の形式が無効です: {cls.DAILY_REPORT_TIME}")
        
        if errors:
            error_message = "設定エラーが発見されました:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValidationError(error_message)
        
        logger.info("設定の検証が完了しました")
        return True
    
    @classmethod
    def get_environment_info(cls) -> Dict[str, str]:
        """環境情報を取得"""
        return {
            'environment': cls.ENVIRONMENT,
            'database_type': 'PostgreSQL' if 'postgres' in cls.DATABASE_URL else 'SQLite',
            'timezone': cls.TIMEZONE,
            'log_level': cls.LOG_LEVEL,
            'health_check_enabled': str(cls.ENVIRONMENT == 'production'),
            'google_api_configured': str(bool(cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET))
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """本番環境かどうかを判定"""
        return cls.ENVIRONMENT == 'production'
    
    @classmethod
    def is_development(cls) -> bool:
        """開発環境かどうかを判定"""
        return cls.ENVIRONMENT == 'development'
    
    @classmethod
    def get_database_type(cls) -> str:
        """データベースタイプを取得"""
        return 'PostgreSQL' if 'postgres' in cls.DATABASE_URL else 'SQLite'
