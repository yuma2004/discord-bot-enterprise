"""
共通ユーティリティモジュール
型安全性とエラーハンドリングを改善
"""
from typing import Any, Optional
import os


class ValidationError(Exception):
    """設定検証エラー"""
    pass


class DatabaseConnectionError(Exception):
    """データベース接続エラー"""
    pass


class BotError(Exception):
    """Botの一般的なエラー"""
    pass


def get_database_repositories():
    """環境に応じてデータベースリポジトリを取得"""
    database_url = os.getenv('DATABASE_URL', '')
    
    if database_url and 'postgres' in database_url:
        try:
            from database_postgres import user_repo, task_repo, attendance_repo, daily_report_repo
            return user_repo, task_repo, attendance_repo, daily_report_repo, 'PostgreSQL'
        except ImportError:
            from database import user_repo, task_repo, attendance_repo, daily_report_repo
            return user_repo, task_repo, attendance_repo, daily_report_repo, 'SQLite (PostgreSQL fallback)'
    else:
        from database import user_repo, task_repo, attendance_repo, daily_report_repo
        return user_repo, task_repo, attendance_repo, daily_report_repo, 'SQLite'


def safe_getenv(key: str, default: Any = None, required: bool = False) -> str:
    """安全な環境変数取得"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValidationError(f"必須の環境変数 '{key}' が設定されていません")
    return value or str(default)


def validate_log_level(level: str) -> str:
    """ログレベルの検証"""
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    level_upper = level.upper()
    if level_upper not in valid_levels:
        raise ValidationError(f"無効なログレベル: {level}. 有効な値: {valid_levels}")
    return level_upper


def create_error_embed(title: str, description: str, error_code: Optional[str] = None) -> dict[str, Any]:
    """エラー用のEmbed情報を作成"""
    embed_data: dict[str, Any] = {
        'title': f"❌ {title}",
        'description': description,
        'color': 0xFF0000  # 赤色
    }
    
    if error_code:
        embed_data['footer'] = {'text': f"エラーコード: {error_code}"}
    
    return embed_data


def create_success_embed(title: str, description: str) -> dict[str, Any]:
    """成功用のEmbed情報を作成"""
    return {
        'title': f"✅ {title}",
        'description': description,
        'color': 0x00FF00  # 緑色
    }


def create_info_embed(title: str, description: str) -> dict[str, Any]:
    """情報用のEmbed情報を作成"""
    return {
        'title': f"ℹ️ {title}",
        'description': description,
        'color': 0x0099FF  # 青色
    }


__all__ = [
    'ValidationError', 'DatabaseConnectionError', 'BotError',
    'get_database_repositories', 'safe_getenv', 'validate_log_level',
    'create_error_embed', 'create_success_embed', 'create_info_embed'
]
