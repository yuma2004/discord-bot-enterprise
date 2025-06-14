"""
共通エラーハンドリングモジュール
"""
import logging
from typing import Optional, Callable, Any
import discord
from discord.ext import commands


class ErrorHandler:
    """エラーハンドリングの統一管理クラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    async def handle_command_error(self, ctx: commands.Context[commands.Bot], error: Exception) -> None:
        """コマンドエラーの統一処理"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("そのコマンドは存在しません。`!help`でコマンド一覧を確認してください。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"必要な引数が不足しています: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("引数の形式が正しくありません。")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"コマンドはクールダウン中です。{error.retry_after:.2f}秒後に再試行してください。")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドを実行する権限がありません。")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Botに必要な権限がありません。")
        else:
            self.logger.error(f"コマンドエラー: {error}", exc_info=True)
            await ctx.send("コマンドの実行中にエラーが発生しました。")
    
    def safe_execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[bool, Any]:
        """安全な実行ラッパー"""
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            self.logger.error(f"実行エラー: {e}", exc_info=True)
            return False, str(e)
    
    async def safe_send_message(self, ctx: commands.Context[commands.Bot], content: Optional[str] = None, embed: Optional[discord.Embed] = None) -> bool:
        """安全なメッセージ送信"""
        try:
            if embed:
                await ctx.send(content=content, embed=embed)
            else:
                await ctx.send(content)
            return True
        except discord.Forbidden:
            self.logger.warning("メッセージ送信権限がありません")
            return False
        except discord.HTTPException as e:
            self.logger.error(f"メッセージ送信エラー: {e}")
            return False
        except Exception as e:
            self.logger.error(f"予期しないメッセージ送信エラー: {e}")
            return False


# グローバルインスタンス
error_handler = ErrorHandler()

__all__ = ['ErrorHandler', 'error_handler']
