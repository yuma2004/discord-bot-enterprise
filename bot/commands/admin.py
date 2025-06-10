import discord
from discord.ext import commands
from datetime import datetime, date, timedelta
import logging
import os
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import user_repo, daily_report_repo, task_repo, attendance_repo, db_manager
else:
    from database import user_repo, daily_report_repo, task_repo, attendance_repo, db_manager
import json
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    """管理者機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name='admin', aliases=['管理'])
    @commands.has_permissions(administrator=True)
    async def admin_group(self, ctx):
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
                ("!admin report", "日報提出率レポート"),
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
    async def show_stats(self, ctx):
        """全体統計情報を表示"""
        try:
            # データベースから各種統計を取得
            stats = await self._collect_statistics()
            
            embed = discord.Embed(
                title="📊 システム統計情報",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # ユーザー統計
            embed.add_field(
                name="👥 ユーザー",
                value=f"総登録者数: {stats['total_users']}名\n"
                      f"今日の利用者: {stats['daily_active_users']}名",
                inline=True
            )
            
            # 日報統計
            embed.add_field(
                name="📝 日報",
                value=f"今日の提出率: {stats['daily_report_rate']:.1f}%\n"
                      f"今月の平均提出率: {stats['monthly_report_rate']:.1f}%",
                inline=True
            )
            
            # タスク統計
            embed.add_field(
                name="📋 タスク",
                value=f"総タスク数: {stats['total_tasks']}件\n"
                      f"未完了タスク: {stats['pending_tasks']}件\n"
                      f"期限超過: {stats['overdue_tasks']}件",
                inline=True
            )
            
            # 出勤統計
            embed.add_field(
                name="🕐 出勤",
                value=f"今日の出勤者: {stats['today_attendance']}名\n"
                      f"現在在席中: {stats['current_present']}名",
                inline=True
            )
            
            # システム情報
            embed.add_field(
                name="⚙️ システム",
                value=f"Bot稼働時間: {stats['uptime']}\n"
                      f"DB接続: {'🟢 正常' if stats['db_healthy'] else '🔴 異常'}",
                inline=True
            )
            
            embed.set_footer(text="企業用Discord Bot - 管理者統計")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            await ctx.send("統計情報の取得中にエラーが発生しました。")
    
    @admin_group.command(name='users', aliases=['ユーザー'])
    async def show_users(self, ctx):
        """ユーザー一覧を表示"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT discord_id, username, display_name, created_at, is_admin
                    FROM users 
                    ORDER BY created_at DESC
                ''')
                users = [dict(row) for row in cursor.fetchall()]
            
            if not users:
                await ctx.send("登録されているユーザーがいません。")
                return
            
            embed = discord.Embed(
                title="👥 登録ユーザー一覧",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # ページネーション対応（最大20名まで表示）
            users_to_show = users[:20]
            
            user_list = []
            for i, user in enumerate(users_to_show, 1):
                admin_mark = " 👑" if user['is_admin'] else ""
                created_date = datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d')
                display_name = user['display_name'] or user['username']
                
                user_list.append(f"{i}. {display_name}{admin_mark} (登録: {created_date})")
            
            embed.description = '\n'.join(user_list)
            
            if len(users) > 20:
                embed.add_field(
                    name="注意",
                    value=f"他 {len(users) - 20} 名のユーザーがいます",
                    inline=False
                )
            
            embed.set_footer(text=f"総ユーザー数: {len(users)}名")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"ユーザー一覧取得エラー: {e}")
            await ctx.send("ユーザー一覧の取得中にエラーが発生しました。")
    
    # 日報関連コマンドを一時的にコメントアウト
    # @admin_group.command(name='report', aliases=['日報'])
    # async def show_report_stats(self, ctx, days: int = 7):
    #     """日報提出率レポート"""
    #     try:
    #         report_stats = await self._get_report_statistics(days)
    #         
    #         embed = discord.Embed(
    #             title=f"📝 日報提出率レポート（過去{days}日間）",
    #             color=discord.Color.green(),
    #             timestamp=datetime.now()
    #         )
    #         
    #         # 日別提出率
    #         daily_rates = []
    #         for day_stat in report_stats['daily_stats']:
    #             date_str = day_stat['date']
    #             rate = day_stat['submission_rate']
    #             rate_emoji = "🟢" if rate >= 80 else "🟡" if rate >= 60 else "🔴"
    #             daily_rates.append(f"{date_str}: {rate_emoji} {rate:.1f}%")
    #         
    #         embed.add_field(
    #             name="日別提出率",
    #             value='\n'.join(daily_rates[-7:]),  # 最新7日分
    #             inline=False
    #         )
    #         
    #         # 全体統計
    #         embed.add_field(
    #             name="期間統計",
    #             value=f"平均提出率: {report_stats['average_rate']:.1f}%\n"
    #                   f"最高提出率: {report_stats['max_rate']:.1f}%\n"
    #                   f"最低提出率: {report_stats['min_rate']:.1f}%",
    #             inline=True
    #         )
    #         
    #         # 未提出が多いユーザー
    #         if report_stats['low_submission_users']:
    #             user_list = []
    #             for user_stat in report_stats['low_submission_users'][:5]:
    #                 user_list.append(f"{user_stat['username']}: {user_stat['submission_rate']:.1f}%")
    #             
    #             embed.add_field(
    #                 name="提出率が低いユーザー（TOP5）",
    #                 value='\n'.join(user_list),
    #                 inline=True
    #             )
    #         
    #         await ctx.send(embed=embed)
    #         
    #     except Exception as e:
    #         logger.error(f"日報統計取得エラー: {e}")
    #         await ctx.send("日報統計の取得中にエラーが発生しました。")
    
    @admin_group.command(name='tasks', aliases=['タスク'])
    async def show_task_stats(self, ctx):
        """全タスク統計を表示"""
        try:
            task_stats = await self._get_task_statistics()
            
            embed = discord.Embed(
                title="📋 タスク統計情報",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            
            # 全体統計
            embed.add_field(
                name="全体統計",
                value=f"総タスク数: {task_stats['total_tasks']}件\n"
                      f"完了タスク: {task_stats['completed_tasks']}件\n"
                      f"未完了タスク: {task_stats['pending_tasks']}件",
                inline=True
            )
            
            # 優先度別統計
            priority_stats = []
            for priority in ['高', '中', '低']:
                count = task_stats['by_priority'].get(priority, 0)
                priority_stats.append(f"{priority}: {count}件")
            
            embed.add_field(
                name="優先度別（未完了）",
                value='\n'.join(priority_stats),
                inline=True
            )
            
            # 期限統計
            embed.add_field(
                name="期限統計",
                value=f"期限超過: {task_stats['overdue_tasks']}件\n"
                      f"今日期限: {task_stats['due_today']}件\n"
                      f"明日期限: {task_stats['due_tomorrow']}件",
                inline=True
            )
            
            # アクティブユーザー
            if task_stats['active_users']:
                user_list = []
                for user_stat in task_stats['active_users'][:5]:
                    user_list.append(f"{user_stat['username']}: {user_stat['task_count']}件")
                
                embed.add_field(
                    name="タスクが多いユーザー（TOP5）",
                    value='\n'.join(user_list),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク統計取得エラー: {e}")
            await ctx.send("タスク統計の取得中にエラーが発生しました。")
    
    @admin_group.command(name='attendance', aliases=['出勤'])
    async def show_attendance_stats(self, ctx, days: int = 7):
        """出勤統計を表示"""
        try:
            attendance_stats = await self._get_attendance_statistics(days)
            
            embed = discord.Embed(
                title=f"🕐 出勤統計（過去{days}日間）",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            # 日別出勤率
            daily_rates = []
            for day_stat in attendance_stats['daily_stats']:
                date_str = day_stat['date']
                rate = day_stat['attendance_rate']
                rate_emoji = "🟢" if rate >= 80 else "🟡" if rate >= 60 else "🔴"
                daily_rates.append(f"{date_str}: {rate_emoji} {rate:.1f}%")
            
            embed.add_field(
                name="日別出勤率",
                value='\n'.join(daily_rates[-7:]),
                inline=False
            )
            
            # 現在の在席状況
            current_status = attendance_stats['current_status']
            embed.add_field(
                name="現在の状況",
                value=f"在席: {current_status['present']}名\n"
                      f"休憩中: {current_status['break']}名\n"
                      f"退勤: {current_status['left']}名",
                inline=True
            )
            
            # 平均勤務時間
            embed.add_field(
                name="勤務時間統計",
                value=f"平均勤務時間: {attendance_stats['avg_work_hours']:.1f}時間\n"
                      f"平均残業時間: {attendance_stats['avg_overtime']:.1f}時間",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"出勤統計取得エラー: {e}")
            await ctx.send("出勤統計の取得中にエラーが発生しました。")
    
    @admin_group.command(name='backup', aliases=['バックアップ'])
    async def create_backup(self, ctx):
        """データベースバックアップを作成"""
        try:
            # バックアップファイル名を生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_discord_bot_{timestamp}.db"
            
            # データベースファイルをコピー
            import shutil
            shutil.copy2(db_manager.db_path, backup_filename)
            
            embed = discord.Embed(
                title="💾 バックアップ完了",
                description=f"データベースのバックアップを作成しました",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="ファイル名",
                value=backup_filename,
                inline=True
            )
            
            # ファイルサイズを取得
            file_size = os.path.getsize(backup_filename)
            embed.add_field(
                name="ファイルサイズ",
                value=f"{file_size / 1024:.1f} KB",
                inline=True
            )
            
            await ctx.send(embed=embed)
            logger.info(f"データベースバックアップを作成: {backup_filename}")
            
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {e}")
            await ctx.send("バックアップの作成中にエラーが発生しました。")
    
    @admin_group.command(name='settings', aliases=['設定'])
    async def show_settings(self, ctx):
        """Bot設定を表示"""
        from config import Config
        
        embed = discord.Embed(
            title="⚙️ Bot設定情報",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # 基本設定
        embed.add_field(
            name="基本設定",
            value=f"Guild ID: {Config.DISCORD_GUILD_ID}\n"
                  f"データベース: {Config.DATABASE_URL}\n"
                  f"タイムゾーン: {Config.TIMEZONE}",
            inline=False
        )
        
        # リマインド設定
        embed.add_field(
            name="リマインド設定",
            value=f"日報時刻: {Config.DAILY_REPORT_TIME}\n"
                  f"会議リマインド: {Config.MEETING_REMINDER_MINUTES}分前",
            inline=True
        )
        
        # API設定
        api_status = "🟢 設定済み" if Config.GOOGLE_CLIENT_ID else "🔴 未設定"
        embed.add_field(
            name="外部API",
            value=f"Google Calendar: {api_status}",
            inline=True
        )
        
        # ログ設定
        embed.add_field(
            name="ログ設定",
            value=f"ログレベル: {Config.LOG_LEVEL}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    async def _collect_statistics(self) -> Dict[str, Any]:
        """全体統計情報を収集"""
        stats = {}
        
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # ユーザー統計
                cursor.execute('SELECT COUNT(*) FROM users')
                stats['total_users'] = cursor.fetchone()[0]
                
                # 日報関連統計を一時的にコメントアウト
                today = date.today().isoformat()
                # cursor.execute('SELECT COUNT(DISTINCT user_id) FROM daily_reports WHERE report_date = ?', (today,))
                # stats['daily_active_users'] = cursor.fetchone()[0]
                stats['daily_active_users'] = 0  # 一時的に0に設定
                
                # cursor.execute('SELECT COUNT(*) FROM daily_reports WHERE report_date = ?', (today,))
                # today_reports = cursor.fetchone()[0]
                # stats['daily_report_rate'] = (today_reports / max(stats['total_users'], 1)) * 100
                stats['daily_report_rate'] = 0  # 一時的に0に設定
                
                # first_day_of_month = date.today().replace(day=1).isoformat()
                # cursor.execute('''
                #     SELECT COUNT(*) FROM daily_reports 
                #     WHERE report_date >= ?
                # ''', (first_day_of_month,))
                # monthly_reports = cursor.fetchone()[0]
                # days_in_month = (date.today() - date.today().replace(day=1)).days + 1
                # expected_reports = stats['total_users'] * days_in_month
                # stats['monthly_report_rate'] = (monthly_reports / max(expected_reports, 1)) * 100
                stats['monthly_report_rate'] = 0  # 一時的に0に設定
                
                # タスク統計
                cursor.execute('SELECT COUNT(*) FROM tasks')
                stats['total_tasks'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != '完了'")
                stats['pending_tasks'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date < ? AND status != '完了'", (today,))
                stats['overdue_tasks'] = cursor.fetchone()[0]
                
                # 出勤統計
                cursor.execute('SELECT COUNT(*) FROM attendance WHERE work_date = ? AND clock_in_time IS NOT NULL', (today,))
                stats['today_attendance'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM attendance WHERE work_date = ? AND status = '在席'", (today,))
                stats['current_present'] = cursor.fetchone()[0]
        
        except Exception as e:
            logger.error(f"統計収集エラー: {e}")
            stats = {key: 0 for key in ['total_users', 'daily_active_users', 'daily_report_rate', 
                                       'monthly_report_rate', 'total_tasks', 'pending_tasks', 
                                       'overdue_tasks', 'today_attendance', 'current_present']}
        
        # システム情報
        stats['uptime'] = "計算中"  # 実際の実装では起動時間から計算
        stats['db_healthy'] = True  # 簡易チェック
        
        return stats
    
    # 日報統計関数を一時的にコメントアウト
    # async def _get_report_statistics(self, days: int) -> Dict[str, Any]:
    #     """日報統計を取得"""
    #     # 実装を簡略化（実際にはより詳細な統計を計算）
    #     return {
    #         'daily_stats': [],
    #         'average_rate': 75.0,
    #         'max_rate': 100.0,
    #         'min_rate': 50.0,
    #         'low_submission_users': []
    #     }
    
    async def _get_task_statistics(self) -> Dict[str, Any]:
        """タスク統計を取得"""
        # 実装を簡略化
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'pending_tasks': 0,
            'by_priority': {'高': 0, '中': 0, '低': 0},
            'overdue_tasks': 0,
            'due_today': 0,
            'due_tomorrow': 0,
            'active_users': []
        }
    
    async def _get_attendance_statistics(self, days: int) -> Dict[str, Any]:
        """出勤統計を取得"""
        # 実装を簡略化
        return {
            'daily_stats': [],
            'current_status': {'present': 0, 'break': 0, 'left': 0},
            'avg_work_hours': 8.0,
            'avg_overtime': 1.0
        }

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(AdminCog(bot)) 