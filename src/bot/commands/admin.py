"""Admin commands - Clean TDD implementation"""
import discord
from discord.ext import commands
import os
import shutil
from typing import Dict, Any, List, Optional

from src.core.database import get_database_manager, DatabaseError
from src.core.error_handling import (
    get_error_handler, handle_errors, UserError, SystemError,
    ErrorContext
)
from src.core.logging import get_logger, log_command_execution
from src.utils.datetime_utils import now_jst, format_date_only
from src.bot.core import require_registration, admin_only

logger = get_logger(__name__)

class AdminCog(commands.Cog):
    """管理者機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.error_handler = get_error_handler()
    
    @commands.group(name='admin', aliases=['管理'])
    @commands.has_permissions(administrator=True)
    @handle_errors()
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
            
            log_command_execution(
                logger, "admin_group", ctx.author.id, 
                ctx.guild.id if ctx.guild else None, True
            )
    
    @admin_group.command(name='stats', aliases=['統計'])
    @admin_only
    @handle_errors()
    async def show_stats(self, ctx: commands.Context[commands.Bot]) -> None:
        """システム統計を表示"""
        stats = await self._get_system_stats()
        
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
        
        log_command_execution(
            logger, "admin_stats", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )
    
    @admin_group.command(name='users', aliases=['ユーザー'])
    @admin_only
    @handle_errors()
    async def show_users(self, ctx: commands.Context[commands.Bot]) -> None:
        """ユーザー一覧を表示"""
        db_manager = get_database_manager()
        
        users = await db_manager.list_users()
        
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
            display_name = user['display_name']
            is_admin = user.get('is_admin', False)
            created_at = user.get('created_at')
            
            admin_mark = " [管理者]" if is_admin else ""
            if created_at:
                # Handle different datetime formats
                if hasattr(created_at, 'strftime'):
                    created_date = created_at.strftime("%Y-%m-%d")
                else:
                    created_date = str(created_at)[:10]  # Assume ISO format
            else:
                created_date = "不明"
            
            user_list.append(f"{i}. {display_name}{admin_mark} (登録: {created_date})")
        
        embed.description = '\n'.join(user_list)
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "admin_users", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )
    
    @admin_group.command(name='tasks', aliases=['タスク'])
    @admin_only
    @handle_errors()
    async def show_task_stats(self, ctx: commands.Context[commands.Bot]) -> None:
        """タスク統計を表示"""
        db_manager = get_database_manager()
        
        # Get all users and their tasks
        users = await db_manager.list_users()
        
        # Collect statistics
        status_counts = {'pending': 0, 'in_progress': 0, 'completed': 0, 'cancelled': 0}
        priority_counts = {'low': 0, 'medium': 0, 'high': 0}
        user_task_counts = []
        
        for user in users:
            user_tasks = await db_manager.list_tasks(user['discord_id'])
            task_count = len(user_tasks)
            
            if task_count > 0:
                user_task_counts.append((user['username'], task_count))
            
            for task in user_tasks:
                status = task.get('status', 'pending')
                priority = task.get('priority', 'medium')
                
                if status in status_counts:
                    status_counts[status] += 1
                if priority in priority_counts:
                    priority_counts[priority] += 1
        
        embed = discord.Embed(
            title="📋 タスク統計",
            color=discord.Color.orange(),
            timestamp=now_jst()
        )
        
        # ステータス別
        status_text = '\n'.join([f"{status}: {count}件" 
                               for status, count in status_counts.items() if count > 0])
        embed.add_field(
            name="ステータス別",
            value=status_text if status_text else "データなし",
            inline=True
        )
        
        # 優先度別
        priority_text = '\n'.join([f"{priority}: {count}件" 
                                 for priority, count in priority_counts.items() if count > 0])
        embed.add_field(
            name="優先度別",
            value=priority_text if priority_text else "データなし",
            inline=True
        )
        
        # ユーザー別（上位5名）
        if user_task_counts:
            user_task_counts.sort(key=lambda x: x[1], reverse=True)
            top_users = user_task_counts[:5]
            user_list = [f"{username}: {count}件" for username, count in top_users]
            
            embed.add_field(
                name="ユーザー別タスク数（上位5名）",
                value='\n'.join(user_list),
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "admin_tasks", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )
    
    @admin_group.command(name='attendance', aliases=['出勤'])
    @admin_only
    @handle_errors()
    async def show_attendance_stats(self, ctx: commands.Context[commands.Bot], days: int = 7) -> None:
        """出勤統計を表示"""
        db_manager = get_database_manager()
        
        # Get all users
        users = await db_manager.list_users()
        total_users = len(users)
        
        if total_users == 0:
            await ctx.send("登録されているユーザーがいません。")
            return
        
        # Get attendance data for the past days
        from datetime import timedelta
        today = now_jst().date()
        date_counts = {}
        
        for i in range(days):
            check_date = today - timedelta(days=i)
            date_str = format_date_only(check_date)
            
            attendance_count = 0
            for user in users:
                record = await db_manager.get_attendance_record(user['discord_id'], date_str)
                if record and record.get('check_in'):
                    attendance_count += 1
            
            date_counts[date_str] = attendance_count
        
        embed = discord.Embed(
            title=f"📅 出勤統計（過去{days}日間）",
            color=discord.Color.purple(),
            timestamp=now_jst()
        )
        
        if date_counts:
            daily_rates: List[str] = []
            # Sort dates in descending order
            sorted_dates = sorted(date_counts.keys(), reverse=True)
            
            for date_str in sorted_dates[:7]:  # Show last 7 days
                count = date_counts[date_str]
                rate = (count / total_users) * 100 if total_users > 0 else 0
                rate_emoji = "🟢" if rate >= 80 else "🟡" if rate >= 50 else "🔴"
                daily_rates.append(f"{date_str}: {rate_emoji} {rate:.1f}% ({count}/{total_users})")
            
            embed.add_field(
                name="日別出勤率",
                value='\n'.join(daily_rates) if daily_rates else "データなし",
                inline=False
            )
        else:
            embed.add_field(
                name="出勤データ",
                value="データが不足しています",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "admin_attendance", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True,
            days=days
        )
    
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
    
    async def _get_system_stats(self) -> Dict[str, Any]:
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
            db_manager = get_database_manager()
            
            # Get all users
            users = await db_manager.list_users()
            stats['total_users'] = len(users)
            
            # Get task statistics
            total_tasks = 0
            pending_tasks = 0
            overdue_tasks = 0
            
            today_str = format_date_only(now_jst())
            now_dt = now_jst()
            
            for user in users:
                user_tasks = await db_manager.list_tasks(user['discord_id'])
                total_tasks += len(user_tasks)
                
                for task in user_tasks:
                    if task.get('status') != 'completed':
                        pending_tasks += 1
                        
                        # Check if overdue
                        due_date = task.get('due_date')
                        if due_date and due_date < now_dt:
                            overdue_tasks += 1
            
            stats['total_tasks'] = total_tasks
            stats['pending_tasks'] = pending_tasks
            stats['overdue_tasks'] = overdue_tasks
            
            # Get attendance statistics
            today_attendance = 0
            current_present = 0
            
            for user in users:
                record = await db_manager.get_attendance_record(user['discord_id'], today_str)
                if record and record.get('check_in'):
                    today_attendance += 1
                    
                    # Check if currently present (not checked out)
                    if not record.get('check_out'):
                        current_present += 1
            
            stats['today_attendance'] = today_attendance
            stats['current_present'] = current_present
            
            # Calculate uptime
            if hasattr(self.bot, 'start_time'):
                uptime_delta = now_jst() - self.bot.start_time
                days = uptime_delta.days
                hours, remainder = divmod(uptime_delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                if days > 0:
                    stats['uptime'] = f"{days}日 {hours}時間 {minutes}分"
                elif hours > 0:
                    stats['uptime'] = f"{hours}時間 {minutes}分"
                else:
                    stats['uptime'] = f"{minutes}分"
        
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
        
        return stats

async def setup(bot: commands.Bot) -> None:
    """Cogをbotに追加"""
    await bot.add_cog(AdminCog(bot))
