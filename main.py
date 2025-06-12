"""
企業用Discord Bot - メインアプリケーション
リファクタリング版 v2.0.0
"""
import discord
from discord.ext import commands
import asyncio
import sys
from pathlib import Path

# アプリケーション設定とコアモジュール
from config import Config
from core.database import db_manager, DB_TYPE
from core.logging import LoggerManager
from core.health_check import health_server

# ログの初期化
logger = LoggerManager.get_logger(__name__)


class CompanyBot(commands.Bot):
    """企業用Discord Bot"""
    
    def __init__(self):
        """Botの初期化"""
        # Botインテントの設定
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='企業用ワークフロー支援Bot'
        )
        
        self.initial_extensions = [
            'bot.commands.task_manager',
            'bot.commands.attendance', 
            'bot.commands.calendar',
            'bot.commands.admin',
            'bot.commands.help'
        ]
    
    async def on_ready(self):
        """Bot起動時の処理"""
        logger.info(f'{self.user} としてログインしました')
        logger.info(f'Bot ID: {self.user.id}')
        logger.info(f'接続サーバー数: {len(self.guilds)}')
        logger.info(f'データベース: {DB_TYPE}')
        
        # データベースの初期化
        await self._initialize_database()
        
        # Botステータスの設定
        await self._set_bot_presence()
        
        logger.info("Bot が正常に起動しました")
    
    async def _initialize_database(self):
        """データベースの初期化"""
        try:
            db_manager.initialize_database()
            logger.info("データベースの初期化が完了しました")
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise
    
    async def _set_bot_presence(self):
        """Botのプレゼンスを設定"""
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="企業のワークフローを支援中..."
                )
            )
        except Exception as e:
            logger.warning(f"プレゼンス設定に失敗: {e}")
    
    async def on_message(self, message):
        """メッセージ受信時の処理"""
        # Bot自身のメッセージは無視
        if message.author == self.user:
            return
        
        # コマンドの処理
        await self.process_commands(message)
    
    async def on_command_error(self, ctx, error):
        """コマンドエラー時の処理"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("そのコマンドは存在しません。`!help`でコマンド一覧を確認してください。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"必要な引数が不足しています: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("引数の形式が正しくありません。")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"コマンドはクールダウン中です。{error.retry_after:.2f}秒後に再試行してください。")
        else:
            logger.error(f"コマンドエラー: {error}", exc_info=True)
            await ctx.send("コマンドの実行中にエラーが発生しました。")
    
    async def setup_hook(self):
        """Bot起動時の初期化処理"""
        logger.info("拡張機能の読み込みを開始します...")
        
        # 拡張機能の読み込み
        await self._load_extensions()
        
        logger.info("初期化処理が完了しました")
    
    async def _load_extensions(self):
        """拡張機能を読み込む"""
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"拡張機能をロードしました: {extension}")
            except Exception as e:
                logger.error(f"拡張機能のロードに失敗: {extension} - {e}")


# 基本的なコマンドを追加
@commands.command(name='ping')
async def ping(ctx):
    """Bot の応答速度をチェック"""
    latency = round(ctx.bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"レイテンシ: {latency}ms",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@commands.command(name='info')
async def info(ctx):
    """Bot の情報を表示"""
    embed = discord.Embed(
        title="🤖 企業用ワークフロー支援Bot",
        description="企業の生産性向上をサポートするDiscord Botです",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="主な機能",
        value="• タスク管理\n• 出退勤管理\n• カレンダー連携\n• 管理機能",
        inline=False
    )
    embed.add_field(
        name="開発者",
        value="社内開発チーム",
        inline=True
    )
    embed.add_field(
        name="バージョン",
        value="2.0.0",
        inline=True
    )
    embed.add_field(
        name="環境",
        value=Config.ENVIRONMENT,
        inline=True
    )
    await ctx.send(embed=embed)


async def main():
    """メイン実行関数"""
    try:
        # 設定の妥当性チェック
        Config.validate_config()
        
        # 環境情報の表示
        env_info = Config.get_environment_info()
        logger.info(f"環境情報: {env_info}")
        
        # 本番環境でヘルスチェックサーバーを起動
        if Config.ENVIRONMENT == "production":
            health_server.start()
        
        # Botインスタンスの作成
        bot = CompanyBot()
        
        # 基本コマンドの追加
        bot.add_command(ping)
        bot.add_command(info)
        
        # Bot の起動
        logger.info("Bot を起動しています...")
        await bot.start(Config.DISCORD_TOKEN)
        
    except Exception as e:
        logger.error(f"Bot の起動に失敗しました: {e}", exc_info=True)
        raise


def setup_signal_handlers():
    """シグナルハンドラーの設定"""
    import signal
    
    def signal_handler(signum, frame):
        logger.info("シャットダウンシグナルを受信しました")
        if health_server.is_running:
            health_server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    try:
        setup_signal_handlers()
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot を停止しました")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)
