"""
ログ設定の統一管理モジュール
"""
import logging
import sys
import os
from typing import Optional


class LoggerManager:
    """ログ管理の統一クラス"""
    
    @staticmethod
    def setup_logger(name: Optional[str] = None, log_file: str = 'bot.log') -> logging.Logger:
        """統一されたログ設定を適用"""
        logger = logging.getLogger(name)
        
        # 既にハンドラーが設定されている場合はスキップ
        if logger.handlers:
            return logger
        
        # ログレベルの設定
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(log_level)
        
        # フォーマッターの作成
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイルハンドラーの設定
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # コンソールハンドラーの設定
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # ハンドラーの追加
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        """ログインスタンスを取得"""
        return LoggerManager.setup_logger(name)


# メインアプリケーション用のログ設定
def setup_main_logging() -> None:
    """メインアプリケーション用のログを設定"""
    # ルートログの設定
    root_logger = logging.getLogger()
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 新しい設定を適用
    LoggerManager.setup_logger()


__all__ = ['LoggerManager', 'setup_main_logging']
