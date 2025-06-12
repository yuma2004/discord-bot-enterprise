"""
共通のデータベース管理モジュール
SQLiteとPostgreSQL（Supabase）の両方に対応
"""
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース管理の共通インターface"""
    
    @staticmethod
    def get_db_manager():
        """環境に応じて適切なデータベースマネージャーを返す"""
        database_url = os.getenv('DATABASE_URL', '')
        
        if database_url and 'postgres' in database_url:
            try:
                from database_postgres import db_manager
                logger.info("PostgreSQL データベースマネージャーを使用します")
                return db_manager, "PostgreSQL"
            except ImportError as e:
                logger.warning(f"PostgreSQL ライブラリが見つかりません: {e}")
                logger.info("SQLite データベースマネージャーにフォールバックします")
                from database import db_manager
                return db_manager, "SQLite (PostgreSQL libraries not found)"
        else:
            from database import db_manager
            logger.info("SQLite データベースマネージャーを使用します")
            return db_manager, "SQLite"

# グローバルなデータベースマネージャーのインスタンス
db_manager, DB_TYPE = DatabaseManager.get_db_manager()

__all__ = ['db_manager', 'DB_TYPE', 'DatabaseManager']
