import asyncio
import logging
from datetime import datetime, time, date
import pytz
import discord
from discord.ext import commands, tasks
import os
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import user_repo, daily_report_repo, task_repo
else:
    from database import user_repo, daily_report_repo, task_repo
from config import Config

logger = logging.getLogger(__name__)

class ReminderService:
    """リマインド機能を提供するサービス"""
    
    def __init__(self, bot):
        self.bot = bot
        self.timezone = pytz.timezone(Config.TIMEZONE)
        
        # 定期実行タスクを開始
        self.daily_report_reminder.start()
        self.task_reminder.start()
        logger.info("リマインドサービスを開始しました")
    
    @tasks.loop(time=time(17, 0))  # 毎日17:00に実行
    async def daily_report_reminder(self):
        """日報リマインドを送信"""
        try:
            logger.info("日報リマインドを開始します")
            
            # 今日の日付を取得
            today = date.today().isoformat()
            
            # 日報未提出者を取得
            users_without_report = daily_report_repo.get_users_without_report(today)
            
            if not users_without_report:
                logger.info("日報未提出者はいません")
                return
            
            # 各未提出者にDMを送信
            sent_count = 0
            for user_data in users_without_report:
                try:
                    discord_user = await self.bot.fetch_user(int(user_data['discord_id']))
                    if discord_user:
                        embed = self._create_daily_report_reminder_embed()
                        await discord_user.send(embed=embed)
                        sent_count += 1
                        logger.info(f"日報リマインドを送信: {user_data['username']}")
                        
                        # レート制限対策
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"日報リマインド送信エラー ({user_data['username']}): {e}")
            
            logger.info(f"日報リマインドを {sent_count}/{len(users_without_report)} 名に送信しました")
            
            # 管理チャンネルがあれば統計を送信
            await self._send_daily_report_stats(today, users_without_report)
            
        except Exception as e:
            logger.error(f"日報リマインド処理エラー: {e}")
    
    @tasks.loop(time=time(9, 0))  # 毎日9:00に実行
    async def task_reminder(self):
        """期限が近いタスクのリマインドを送信"""
        try:
            logger.info("タスクリマインドを開始します")
            
            # 期限が近いタスクを取得（1日以内）
            due_tasks = task_repo.get_tasks_due_soon(days=1)
            
            if not due_tasks:
                logger.info("期限が近いタスクはありません")
                return
            
            # ユーザー別にタスクをグループ化
            user_tasks = {}
            for task in due_tasks:
                discord_id = task['discord_id']
                if discord_id not in user_tasks:
                    user_tasks[discord_id] = []
                user_tasks[discord_id].append(task)
            
            # 各ユーザーにタスクリマインドを送信
            sent_count = 0
            for discord_id, tasks in user_tasks.items():
                try:
                    discord_user = await self.bot.fetch_user(int(discord_id))
                    if discord_user:
                        embed = self._create_task_reminder_embed(tasks)
                        await discord_user.send(embed=embed)
                        sent_count += 1
                        logger.info(f"タスクリマインドを送信: {discord_user.name} ({len(tasks)}件)")
                        
                        # レート制限対策
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"タスクリマインド送信エラー ({discord_id}): {e}")
            
            logger.info(f"タスクリマインドを {sent_count}/{len(user_tasks)} 名に送信しました")
            
        except Exception as e:
            logger.error(f"タスクリマインド処理エラー: {e}")
    
    def _create_daily_report_reminder_embed(self):
        """日報リマインドのEmbedを作成"""
        
        embed = discord.Embed(
            title="📝 日報提出リマインド",
            description="本日の日報をまだ提出されていません。\n忘れずに提出をお願いいたします。",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="提出方法",
            value="`!日報 [内容]` コマンドで提出できます",
            inline=False
        )
        
        embed.add_field(
            name="テンプレート",
            value="`!日報テンプレート` でテンプレートを確認できます",
            inline=False
        )
        
        embed.set_footer(text="企業用Discord Bot - 日報リマインド")
        
        return embed
    
    def _create_task_reminder_embed(self, tasks):
        """タスクリマインドのEmbedを作成"""
        
        embed = discord.Embed(
            title="⏰ タスク期限リマインド",
            description=f"期限が近いタスクが {len(tasks)} 件あります。",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # 期限別にタスクを分類
        today_tasks = []
        tomorrow_tasks = []
        overdue_tasks = []
        
        today = date.today()
        
        for task in tasks:
            if task['due_date']:
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                if due_date < today:
                    overdue_tasks.append(task)
                elif due_date == today:
                    today_tasks.append(task)
                else:
                    tomorrow_tasks.append(task)
        
        # 各カテゴリーのタスクを表示
        if overdue_tasks:
            task_list = []
            for task in overdue_tasks[:5]:  # 最大5件
                priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(task['priority'], '⚪')
                task_list.append(f"{priority_emoji} {task['title']} (期限: {task['due_date']})")
            
            embed.add_field(
                name="🚨 期限超過",
                value='\n'.join(task_list) + ('...' if len(overdue_tasks) > 5 else ''),
                inline=False
            )
        
        if today_tasks:
            task_list = []
            for task in today_tasks[:5]:  # 最大5件
                priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(task['priority'], '⚪')
                task_list.append(f"{priority_emoji} {task['title']}")
            
            embed.add_field(
                name="📅 今日が期限",
                value='\n'.join(task_list) + ('...' if len(today_tasks) > 5 else ''),
                inline=False
            )
        
        if tomorrow_tasks:
            task_list = []
            for task in tomorrow_tasks[:5]:  # 最大5件
                priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(task['priority'], '⚪')
                task_list.append(f"{priority_emoji} {task['title']}")
            
            embed.add_field(
                name="⏰ 明日が期限",
                value='\n'.join(task_list) + ('...' if len(tomorrow_tasks) > 5 else ''),
                inline=False
            )
        
        embed.add_field(
            name="確認方法",
            value="`!タスク一覧` でタスク一覧を確認できます",
            inline=False
        )
        
        embed.set_footer(text="企業用Discord Bot - タスクリマインド")
        
        return embed
    
    async def _send_daily_report_stats(self, today, users_without_report):
        """日報統計を管理チャンネルに送信"""
        try:
            # 設定で管理チャンネルが指定されている場合のみ送信
            # ここでは実装をスキップし、将来的に設定機能で対応
            pass
        except Exception as e:
            logger.error(f"日報統計送信エラー: {e}")
    
    @daily_report_reminder.before_loop
    async def before_daily_report_reminder(self):
        """日報リマインドタスク開始前の処理"""
        await self.bot.wait_until_ready()
        logger.info("日報リマインドタスクの準備が完了しました")
    
    @task_reminder.before_loop
    async def before_task_reminder(self):
        """タスクリマインドタスク開始前の処理"""
        await self.bot.wait_until_ready()
        logger.info("タスクリマインドタスクの準備が完了しました")
    
    def stop_reminders(self):
        """リマインドサービスを停止"""
        self.daily_report_reminder.cancel()
        self.task_reminder.cancel()
        logger.info("リマインドサービスを停止しました")

class ReminderCog(commands.Cog):
    """リマインド機能のCog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reminder_service = ReminderService(bot)
    
    @commands.command(name='リマインドテスト', aliases=['test_reminder'])
    @commands.has_permissions(administrator=True)
    async def test_reminder(self, ctx, reminder_type: str = "日報"):
        """リマインドのテスト送信（管理者のみ）"""
        if reminder_type == "日報":
            embed = self.reminder_service._create_daily_report_reminder_embed()
            await ctx.author.send(embed=embed)
            await ctx.send("日報リマインドのテストを送信しました（DM確認）")
        elif reminder_type == "タスク":
            # テスト用のダミータスクを作成
            dummy_tasks = [
                {
                    'title': 'プロジェクトAの進捗報告',
                    'due_date': date.today().isoformat(),
                    'priority': '高'
                },
                {
                    'title': '会議資料の準備',
                    'due_date': date.today().isoformat(),
                    'priority': '中'
                }
            ]
            embed = self.reminder_service._create_task_reminder_embed(dummy_tasks)
            await ctx.author.send(embed=embed)
            await ctx.send("タスクリマインドのテストを送信しました（DM確認）")
        else:
            await ctx.send("リマインドタイプは '日報' または 'タスク' を指定してください")
    
    @commands.command(name='リマインド設定', aliases=['reminder_settings'])
    @commands.has_permissions(administrator=True)
    async def reminder_settings(self, ctx):
        """リマインド設定の表示"""
        embed = discord.Embed(
            title="⚙️ リマインド設定",
            description="現在のリマインド設定",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="日報リマインド",
            value=f"毎日 {Config.DAILY_REPORT_TIME} に実行",
            inline=False
        )
        
        embed.add_field(
            name="タスクリマインド",
            value="毎日 09:00 に実行（期限1日以内のタスク）",
            inline=False
        )
        
        embed.add_field(
            name="タイムゾーン",
            value=Config.TIMEZONE,
            inline=True
        )
        
        embed.add_field(
            name="ステータス",
            value="🟢 稼働中" if self.reminder_service.daily_report_reminder.is_running() else "🔴 停止中",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    def cog_unload(self):
        """Cog終了時の処理"""
        self.reminder_service.stop_reminders()

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(ReminderCog(bot)) 