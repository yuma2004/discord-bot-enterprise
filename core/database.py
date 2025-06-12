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
            except (ImportError, ModuleNotFoundError) as e:
                logger.warning(f"PostgreSQL ライブラリが見つかりません: {e}")
                logger.info("SQLite データベースマネージャーにフォールバックします")
                try:
                    from database import db_manager
                    return db_manager, "SQLite (PostgreSQL libraries not found)"
                except (ImportError, ModuleNotFoundError) as e:
                    logger.error(f"データベースマネージャーの読み込みに失敗: {e}")
                    return None, "Failed to load database manager"
        else:
            try:
                from database import db_manager
                logger.info("SQLite データベースマネージャーを使用します")
                return db_manager, "SQLite"
            except (ImportError, ModuleNotFoundError) as e:
                logger.error(f"SQLite データベースマネージャーの読み込みに失敗: {e}")
                return None, "Failed to load SQLite database manager"

# グローバルなデータベースマネージャーのインスタンス
db_manager, DB_TYPE = DatabaseManager.get_db_manager()

__all__ = ['db_manager', 'DB_TYPE', 'DatabaseManager']
