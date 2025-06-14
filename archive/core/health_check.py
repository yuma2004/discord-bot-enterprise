"""
ヘルスチェック機能の専用モジュール
本番環境でのKoyebデプロイ時に使用
"""
import threading
import logging
from typing import Optional, Dict, Any, Tuple

try:
    from flask import Flask  # type: ignore
    flask_available = True
except ImportError:
    Flask = None  # type: ignore
    flask_available = False

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """ヘルスチェックサーバーの管理クラス"""
    
    def __init__(self, port: int = 8000) -> None:
        self.port = port
        if flask_available and Flask is not None:
            self.app: Optional[Any] = Flask(__name__)
            self.server_thread: Optional[threading.Thread] = None
            self._setup_routes()
        else:
            self.app = None
            self.server_thread = None
            logger.warning("Flaskが利用できません。ヘルスチェック機能は無効です。")
    
    def _setup_routes(self) -> None:
        """ヘルスチェック用のルートを設定"""
        if self.app is None:            return
            
        @self.app.route('/health')  # type: ignore
        def health_check() -> Tuple[Dict[str, Any], int]:  # type: ignore
            """ヘルスチェックエンドポイント"""
            return {
                'status': 'healthy',
                'service': 'discord-bot-enterprise',
                'version': '1.0.0'
            }, 200
        
        @self.app.route('/')  # type: ignore
        def root() -> Tuple[Dict[str, Any], int]:  # type: ignore
            """ルートエンドポイント"""
            return {
                'message': 'Discord Bot Enterprise is running',
                'status': 'online',
                'endpoints': {
                    'health': '/health'
                }
            }, 200
    
    def start(self) -> None:
        """ヘルスチェックサーバーを開始"""
        if not flask_available or self.app is None:
            logger.warning("Flaskが利用できないため、ヘルスチェックサーバーを開始できません")
            return
            
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("ヘルスチェックサーバーは既に起動しています")
            return
        
        def run_server() -> None:
            """サーバー実行関数"""
            try:
                if self.app:
                    self.app.run(  # type: ignore
                        host='0.0.0.0',
                        port=self.port,
                        debug=False,
                        use_reloader=False
                    )
            except Exception as e:
                logger.error(f"ヘルスチェックサーバーの起動に失敗: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"ヘルスチェックサーバーがポート{self.port}で起動しました")
    
    def stop(self) -> None:
        """ヘルスチェックサーバーを停止"""
        if self.server_thread and self.server_thread.is_alive():
            # Flask serverの適切な停止方法は複雑なため、
            # デーモンスレッドとして起動してメインプロセス終了時に自動終了させる
            logger.info("ヘルスチェックサーバーを停止しました")
    
    @property
    def is_running(self) -> bool:
        """サーバーが実行中かどうかを確認"""
        if self.server_thread is None:
            return False
        return self.server_thread.is_alive()


# グローバルインスタンス
health_server = HealthCheckServer()

__all__ = ['HealthCheckServer', 'health_server']
