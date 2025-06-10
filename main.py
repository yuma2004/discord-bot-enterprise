import discord
from discord.ext import commands
import logging
import asyncio
import os
from config import Config

# データベースの動的選択（Supabase対応）
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    try:
        from database_postgres import postgres_db_manager as db_manager
        DB_TYPE = "PostgreSQL"
    except ImportError:
        from database import db_manager
        DB_TYPE = "SQLite (PostgreSQL libraries not found)"
else:
    from database import db_manager
    DB_TYPE = "SQLite"

# ログ設定
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompanyBot(commands.Bot):
    """企業用Discord Bot"""
    
    def __init__(self):
        # Botインテントの設定
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='企業用ワークフロー支援Bot'
        )
    
    async def on_ready(self):
        """Bot起動時の処理"""
        logger.info(f'{self.user} としてログインしました')
        logger.info(f'Bot ID: {self.user.id}')
        logger.info(f'接続サーバー数: {len(self.guilds)}')
        logger.info(f'データベース: {DB_TYPE}')
        
        # データベースの初期化
        try:
            db_manager.initialize_database()
            logger.info("データベースの初期化が完了しました")
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
        
        # ステータスの設定
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="企業のワークフローを支援中..."
            )
        )
        
        logger.info("Bot が正常に起動しました")
    
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
        else:
            logger.error(f"コマンドエラー: {error}")
            await ctx.send("コマンドの実行中にエラーが発生しました。")
    
    async def setup_hook(self):
        """Bot起動時の初期化処理"""
        logger.info("初期化処理を開始します...")
        
        # コマンドCogをロードする
        try:
            await self.load_extension('bot.commands.daily_report')
            logger.info("日報機能をロードしました")
        except Exception as e:
            logger.error(f"日報機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.commands.task_manager')
            logger.info("タスク管理機能をロードしました")
        except Exception as e:
            logger.error(f"タスク管理機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.commands.attendance')
            logger.info("出退勤管理機能をロードしました")
        except Exception as e:
            logger.error(f"出退勤管理機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.utils.reminder')
            logger.info("リマインド機能をロードしました")
        except Exception as e:
            logger.error(f"リマインド機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.commands.calendar')
            logger.info("カレンダー機能をロードしました")
        except Exception as e:
            logger.error(f"カレンダー機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.commands.admin')
            logger.info("管理者機能をロードしました")
        except Exception as e:
            logger.error(f"管理者機能のロードに失敗: {e}")
        
        try:
            await self.load_extension('bot.commands.help')
            logger.info("ヘルプ機能をロードしました")
        except Exception as e:
            logger.error(f"ヘルプ機能のロードに失敗: {e}")
        
        logger.info("初期化処理が完了しました")

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
        value="• 日報リマインド\n• タスク管理\n• カレンダー連携",
        inline=False
    )
    embed.add_field(
        name="開発者",
        value="社内開発チーム",
        inline=True
    )
    embed.add_field(
        name="バージョン",
        value="1.0.0",
        inline=True
    )
    await ctx.send(embed=embed)

async def main():
    """メイン実行関数"""
    try:
        # 設定の妥当性チェック
        Config.validate_config()
        
        # ヘルスチェック用サーバーの起動（Koyeb用）
        if Config.ENVIRONMENT == "production":
            from flask import Flask
            import threading
            
            health_app = Flask(__name__)
            
            @health_app.route('/health')
            def health_check():
                return {'status': 'healthy', 'service': 'discord-bot', 'version': '1.0.0'}, 200
            
            @health_app.route('/')
            def root():
                return {'message': 'Discord Bot Enterprise is running', 'status': 'online'}, 200
            
            def run_health_server():
                health_app.run(host='0.0.0.0', port=8000, debug=False)
            
            # ヘルスチェックサーバーを別スレッドで起動
            health_thread = threading.Thread(target=run_health_server, daemon=True)
            health_thread.start()
            logger.info("ヘルスチェックサーバーがポート8000で起動しました")
        
        # Botインスタンスの作成
        bot = CompanyBot()
        
        # 基本コマンドの追加
        bot.add_command(ping)
        bot.add_command(info)
        
        # Bot の起動
        logger.info("Bot を起動しています...")
        await bot.start(Config.DISCORD_TOKEN)
        
    except Exception as e:
        logger.error(f"Bot の起動に失敗しました: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot を停止しました")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}") 