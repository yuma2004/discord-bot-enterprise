import discord
from discord.ext import commands
from core.logging import LoggerManager
from core.database import db_manager
from bot.utils.datetime_utils import now_jst
import os
import shutil
from typing import Dict, Any, List

# データベースリポジトリの動的インポート
database_url = os.getenv('DATABASE_URL', '')
if database_url and 'postgres' in database_url:
    try:
        from database_postgres import task_repo  # type: ignore
    except ImportError:
        from database import task_repo  # type: ignore
else:
    from database import task_repo  # type: ignore

logger = LoggerManager.get_logger(__name__)

class AdminCog(commands.Cog):
    """管理者機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.group(name='admin', aliases=['管理'])
    @commands.has_permissions(administrator=True)
    async def admin_group(self, ctx: commands.Context[commands.Bot]) -> None:
        """管理者コマンドグループ"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🔧 管理者機能",
                description="利用可能な管理者コマンド",
                color=discord.Color.gold()
            )
            
            commands_info = [
                ("!admin stats", "統計情報を表示"),
                ("!admin users", "ユーザー一覧を表示"),
                ("!admin backup", "データベースバックアップ"),
                ("!admin settings", "Bot設定を表示"),
                ("!admin tasks", "全タスク統計"),
                ("!admin attendance", "出勤統計")
            ]
            
            for command, description in commands_info:
                embed.add_field(
                    name=command,
                    value=description,
                    inline=False
                )
            
            await ctx.send(embed=embed)
    
    @admin_group.command(name='stats', aliases=['統計'])
    async def show_stats(self, ctx: commands.Context[commands.Bot]) -> None:
        """システム統計を表示"""
        try:
            if db_manager is None:
                await ctx.send("データベースに接続できません。")
                return
                
            stats = self._get_system_stats()
            
            embed = discord.Embed(
                title="📊 システム統計",
                color=discord.Color.blue(),
                timestamp=now_jst()
            )
            
            embed.add_field(name="登録ユーザー数", value=f"{stats['total_users']}人", inline=True)
            embed.add_field(name="総タスク数", value=f"{stats['total_tasks']}件", inline=True)
            embed.add_field(name="未完了タスク", value=f"{stats['pending_tasks']}件", inline=True)
            embed.add_field(name="期限切れタスク", value=f"{stats['overdue_tasks']}件", inline=True)
            embed.add_field(name="今日の出勤", value=f"{stats['today_attendance']}人", inline=True)
            embed.add_field(name="現在出勤中", value=f"{stats['current_present']}人", inline=True)
            embed.add_field(name="稼働時間", value=stats['uptime'], inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            await ctx.send("統計情報の取得中にエラーが発生しました。")
    
    @admin_group.command(name='users', aliases=['ユーザー'])
    async def show_users(self, ctx: commands.Context[commands.Bot]) -> None:
        """ユーザー一覧を表示"""
        try:
            if db_manager is None:
                await ctx.send("データベースに接続できません。")
                return
                
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT discord_id, username, display_name, is_admin, created_at
                    FROM users ORDER BY created_at DESC
                """)
                users = cursor.fetchall()
            
            if not users:
                await ctx.send("登録されているユーザーがいません。")
                return            
            embed = discord.Embed(
                title="👥 ユーザー一覧",
                color=discord.Color.green(),
                timestamp=now_jst()
            )
            
            user_list: List[str] = []
            for i, user in enumerate(users, 1):
                _, _, display_name, is_admin, created_at = user
                admin_mark = " [管理者]" if is_admin else ""
                created_date = created_at.strftime("%Y-%m-%d") if created_at else "不明"
                user_list.append(f"{i}. {display_name}{admin_mark} (登録: {created_date})")
            
            embed.description = '\n'.join(user_list)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"ユーザー一覧取得エラー: {e}")
            await ctx.send("ユーザー一覧の取得中にエラーが発生しました。")
    
    @admin_group.command(name='tasks', aliases=['タスク'])
    async def show_task_stats(self, ctx: commands.Context[commands.Bot]) -> None:
        """タスク統計を表示"""
        try:
            if db_manager is None:
                await ctx.send("データベースに接続できません。")
                return
                
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # ステータス別統計
                cursor.execute("""
                    SELECT status, COUNT(*) FROM tasks GROUP BY status
                """)
                status_stats = cursor.fetchall()
                
                # 優先度別統計
                cursor.execute("""
                    SELECT priority, COUNT(*) FROM tasks GROUP BY priority
                """)
                priority_data = cursor.fetchall()
                
                # ユーザー別統計（上位5名）
                cursor.execute("""
                    SELECT u.username, COUNT(t.id) as task_count
                    FROM users u LEFT JOIN tasks t ON u.id = t.user_id
                    GROUP BY u.id, u.username
                    ORDER BY task_count DESC LIMIT 5
                """)
                user_stats = cursor.fetchall()
            
            embed = discord.Embed(
                title="📋 タスク統計",
                color=discord.Color.orange(),
                timestamp=now_jst()
            )
            
            # ステータス別
            status_text = '\n'.join([f"{status}: {count}件" 
                                   for status, count in status_stats])
            embed.add_field(
                name="ステータス別",
                value=status_text if status_text else "データなし",
                inline=True
            )
            
            # 優先度別
            priority_stats: List[str] = []
            for priority, count in priority_data:
                priority_stats.append(f"{priority}: {count}件")
            
            embed.add_field(
                name="優先度別",
                value='\n'.join(priority_stats) if priority_stats else "データなし",
                inline=True
            )
            
            # ユーザー別（上位5名）
            if user_stats:
                user_list: List[str] = []
                for user_stat in user_stats:
                    user_list.append(f"{user_stat[0]}: {user_stat[1]}件")
                
                embed.add_field(
                    name="ユーザー別タスク数（上位5名）",
                    value='\n'.join(user_list),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク統計取得エラー: {e}")
            await ctx.send("タスク統計の取得中にエラーが発生しました。")
    
    @admin_group.command(name='attendance', aliases=['出勤'])
    async def show_attendance_stats(self, ctx: commands.Context[commands.Bot], days: int = 7) -> None:
        """出勤統計を表示"""
        try:
            if db_manager is None:
                await ctx.send("データベースに接続できません。")
                return
                
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 日別出勤率
                cursor.execute(f"""
                    SELECT DATE(clock_in_time) as date,
                           COUNT(DISTINCT user_id) as attendance_count
                    FROM attendance
                    WHERE clock_in_time >= date('now', '-{days} days')
                    GROUP BY DATE(clock_in_time)
                    ORDER BY date DESC
                """)
                daily_attendance = cursor.fetchall()
                  # 総ユーザー数
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                total_users = result[0] if result else 0
            
            embed = discord.Embed(
                title=f"📅 出勤統計（過去{days}日間）",
                color=discord.Color.purple(),
                timestamp=now_jst()
            )
            
            if daily_attendance and total_users > 0:
                daily_rates: List[str] = []
                for date_str, count in daily_attendance:
                    rate = (count / total_users) * 100 if total_users > 0 else 0
                    rate_emoji = "🟢" if rate >= 80 else "🟡" if rate >= 50 else "🔴"
                    daily_rates.append(f"{date_str}: {rate_emoji} {rate:.1f}%")
                
                embed.add_field(
                    name="日別出勤率",
                    value='\n'.join(daily_rates[-7:]) if daily_rates else "データなし",
                    inline=False
                )
            else:
                embed.add_field(
                    name="出勤データ",
                    value="データが不足しています",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"出勤統計取得エラー: {e}")
            await ctx.send("出勤統計の取得中にエラーが発生しました。")
    
    @admin_group.command(name='backup', aliases=['バックアップ'])
    async def create_backup(self, ctx: commands.Context[commands.Bot]) -> None:
        """データベースバックアップを作成"""
        try:
            if db_manager is None:
                await ctx.send("データベースに接続できません。")
                return
                
            timestamp = now_jst().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
              # SQLiteの場合のみバックアップ実行
            try:
                if hasattr(db_manager, 'db_path'):
                    db_path = getattr(db_manager, 'db_path', None)
                    if db_path:
                        shutil.copy2(db_path, backup_filename)
                        
                        embed = discord.Embed(
                            title="💾 バックアップ完了",
                            description=f"バックアップファイル: {backup_filename}",
                            color=discord.Color.green(),
                            timestamp=now_jst()
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ バックアップエラー",
                            description="データベースパスが見つかりません",
                            color=discord.Color.red()
                        )
                else:
                    embed = discord.Embed(
                        title="❌ バックアップエラー",
                        description="PostgreSQLのバックアップは手動で実行してください",
                        color=discord.Color.red()
                    )
            except Exception as backup_error:
                logger.error(f"バックアップ実行エラー: {backup_error}")
                embed = discord.Embed(
                    title="❌ バックアップエラー",
                    description="バックアップファイルの作成に失敗しました",
                    color=discord.Color.red()
                )
            
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {e}")
            embed = discord.Embed(
                title="❌ バックアップエラー",
                description="バックアップの作成中にエラーが発生しました",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    @admin_group.command(name='settings', aliases=['設定'])
    async def show_settings(self, ctx: commands.Context[commands.Bot]) -> None:
        """Bot設定を表示"""
        embed = discord.Embed(
            title="⚙️ Bot設定",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        settings = {
            "データベース": "PostgreSQL" if os.getenv('DATABASE_URL') else "SQLite",
            "環境": "本番" if os.getenv('ENVIRONMENT') == 'production' else "開発",
            "ログレベル": os.getenv('LOG_LEVEL', 'INFO'),
            "Discord Guild ID": os.getenv('DISCORD_GUILD_ID', '未設定'),
        }
        
        for key, value in settings.items():
            embed.add_field(name=key, value=value, inline=True)
        
        await ctx.send(embed=embed)
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """システム統計を取得"""
        stats: Dict[str, Any] = {
            'total_users': 0,
            'total_tasks': 0,
            'pending_tasks': 0,
            'overdue_tasks': 0,
            'today_attendance': 0,
            'current_present': 0,
            'uptime': "計算中"
        }
        
        try:
            if db_manager is None:
                return stats
                
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 各統計を取得
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                if result:
                    stats['total_users'] = result[0]
                
                cursor.execute("SELECT COUNT(*) FROM tasks")
                result = cursor.fetchone()
                if result:
                    stats['total_tasks'] = result[0]
                
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != '完了'")
                result = cursor.fetchone()
                if result:
                    stats['pending_tasks'] = result[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE due_date < date('now') AND status != '完了'
                """)
                result = cursor.fetchone()
                if result:
                    stats['overdue_tasks'] = result[0]
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM attendance 
                    WHERE DATE(clock_in_time) = DATE('now')
                """)
                result = cursor.fetchone()
                if result:
                    stats['today_attendance'] = result[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM attendance 
                    WHERE DATE(clock_in_time) = DATE('now') AND clock_out_time IS NULL
                """)
                result = cursor.fetchone()
                if result:
                    stats['current_present'] = result[0]
        
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
        
        return stats

async def setup(bot: commands.Bot) -> None:
    """Cogをbotに追加"""
    await bot.add_cog(AdminCog(bot))
