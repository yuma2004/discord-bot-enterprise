"""Attendance management commands - Clean TDD implementation"""
import discord
from discord.ext import commands
from datetime import datetime, date
import csv
import io
from typing import Optional, Dict, Any, List

from src.core.database import get_database_manager, DatabaseError
from src.core.error_handling import (
    get_error_handler, handle_errors, UserError, SystemError,
    ErrorContext
)
from src.core.logging import get_logger, log_command_execution, log_user_action
from src.utils.datetime_utils import (
    now_jst, today_jst, ensure_jst, format_time_only, 
    format_datetime_for_display, get_month_date_range,
    parse_date_string, calculate_work_hours, calculate_time_difference,
    format_date_only
)
from src.bot.core import require_registration, admin_only

logger = get_logger(__name__)


class AttendanceView(discord.ui.View):
    """出退勤管理用のボタンUI"""
    
    def __init__(self):
        super().__init__(timeout=None)  # タイムアウトなし
        self.error_handler = get_error_handler()
    
    @discord.ui.button(label='🟢 出勤', style=discord.ButtonStyle.green, custom_id='clock_in')
    async def clock_in_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """出勤ボタン"""
        await interaction.response.defer()
        
        context = ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command="attendance_clock_in"
        )
        
        try:
            db_manager = get_database_manager()
            
            # ユーザー情報を取得または作成
            user = await db_manager.get_user(interaction.user.id)
            if not user:
                user_id = await db_manager.create_user(
                    discord_id=interaction.user.id,
                    username=interaction.user.name,
                    display_name=interaction.user.display_name
                )
                user = {'id': user_id, 'discord_id': interaction.user.id}
            
            today_date = format_date_only(today_jst())
            
            # 今日の出退勤記録を確認
            today_record = await db_manager.get_attendance_record(user['discord_id'], today_date)
            
            if today_record and today_record.get('check_in'):
                embed = discord.Embed(
                    title="⚠️ 既に出勤済み",
                    description="本日は既に出勤記録があります",
                    color=discord.Color.orange(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="出勤時刻",
                    value=format_time_only(today_record['check_in']),
                    inline=True
                )
                embed.add_field(
                    name="現在のステータス",
                    value="在席",
                    inline=True
                )
            else:
                # 出勤記録
                check_in_time = now_jst()
                if today_record:
                    # 既存レコードを更新
                    success = await db_manager.update_attendance_record(
                        user['discord_id'], today_date, check_in=check_in_time
                    )
                else:
                    # 新規レコード作成
                    await db_manager.create_attendance_record(
                        user['discord_id'], today_date, check_in_time
                    )
                    success = True
                
                if success:
                    embed = discord.Embed(
                        title="🟢 出勤記録完了",
                        description="お疲れ様です！出勤を記録しました",
                        color=discord.Color.green(),
                        timestamp=now_jst()
                    )
                    embed.add_field(
                        name="出勤時刻",
                        value=format_time_only(check_in_time),
                        inline=True
                    )
                    embed.add_field(
                        name="ステータス",
                        value="在席",
                        inline=True
                    )
                    
                    log_user_action(
                        logger, interaction.user.id, "clock_in",
                        time=check_in_time.isoformat()
                    )
                else:
                    raise SystemError("Failed to create attendance record", error_code="ATTENDANCE_CREATE_FAILED")
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            result = await self.error_handler.handle_error_async(e, context)
            if result.should_notify_user:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=result.user_message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🔴 退勤', style=discord.ButtonStyle.red, custom_id='clock_out')
    async def clock_out_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """退勤ボタン"""
        await interaction.response.defer()
        
        context = ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command="attendance_clock_out"
        )
        
        try:
            db_manager = get_database_manager()
            
            # ユーザー情報を取得
            user = await db_manager.get_user(interaction.user.id)
            if not user:
                raise UserError(
                    "User not found",
                    "出勤記録が見つかりません。まず出勤してください。",
                    error_code="USER_NOT_FOUND"
                )
            
            today_date = format_date_only(today_jst())
            today_record = await db_manager.get_attendance_record(user['discord_id'], today_date)
            
            if not today_record or not today_record.get('check_in'):
                raise UserError(
                    "No check-in record found",
                    "出勤記録がありません。まず出勤してください。",
                    error_code="NO_CHECK_IN"
                )
            
            if today_record.get('check_out'):
                raise UserError(
                    "Already checked out",
                    "既に退勤済みです。",
                    error_code="ALREADY_CHECKED_OUT"
                )
            
            # 退勤記録
            check_out_time = now_jst()
            check_in_time = today_record['check_in']
            
            # 勤務時間を計算
            work_hours = calculate_work_hours(
                check_in_time, check_out_time,
                today_record.get('break_start'), today_record.get('break_end')
            )
            overtime_hours = max(0.0, work_hours - 8.0)  # 8時間を標準勤務時間とする
            
            success = await db_manager.update_attendance_record(
                user['discord_id'], today_date,
                check_out=check_out_time,
                work_hours=work_hours,
                overtime_hours=overtime_hours
            )
            
            if success:
                embed = discord.Embed(
                    title="🔴 退勤記録完了",
                    description="お疲れ様でした！退勤を記録しました",
                    color=discord.Color.red(),
                    timestamp=now_jst()
                )
                
                embed.add_field(
                    name="出勤時刻",
                    value=format_time_only(check_in_time),
                    inline=True
                )
                embed.add_field(
                    name="退勤時刻",
                    value=format_time_only(check_out_time),
                    inline=True
                )
                embed.add_field(
                    name="勤務時間",
                    value=f"{work_hours:.1f}時間",
                    inline=True
                )
                
                if overtime_hours > 0:
                    embed.add_field(
                        name="残業時間",
                        value=f"{overtime_hours:.1f}時間",
                        inline=True
                    )
                
                log_user_action(
                    logger, interaction.user.id, "clock_out",
                    time=check_out_time.isoformat(),
                    work_hours=work_hours,
                    overtime_hours=overtime_hours
                )
            else:
                raise SystemError("Failed to update attendance record", error_code="ATTENDANCE_UPDATE_FAILED")
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            result = await self.error_handler.handle_error_async(e, context)
            if result.should_notify_user:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=result.user_message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🟡 休憩開始', style=discord.ButtonStyle.secondary, custom_id='break_start')
    async def break_start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩開始ボタン"""
        await interaction.response.defer()
        
        context = ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command="attendance_break_start"
        )
        
        try:
            db_manager = get_database_manager()
            
            # ユーザー情報を取得
            user = await db_manager.get_user(interaction.user.id)
            if not user:
                raise UserError(
                    "User not found",
                    "出勤記録が見つかりません。まず出勤してください。",
                    error_code="USER_NOT_FOUND"
                )
            
            today_date = format_date_only(today_jst())
            today_record = await db_manager.get_attendance_record(user['discord_id'], today_date)
            
            if not today_record or not today_record.get('check_in'):
                raise UserError(
                    "No check-in record found",
                    "出勤記録がありません。まず出勤してください。",
                    error_code="NO_CHECK_IN"
                )
            
            if today_record.get('break_start') and not today_record.get('break_end'):
                raise UserError(
                    "Already on break",
                    "既に休憩中です。",
                    error_code="ALREADY_ON_BREAK"
                )
            
            # 休憩開始記録
            break_start_time = now_jst()
            success = await db_manager.update_attendance_record(
                user['discord_id'], today_date, break_start=break_start_time
            )
            
            if success:
                embed = discord.Embed(
                    title="🟡 休憩開始",
                    description="休憩を開始しました",
                    color=discord.Color.gold(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="休憩開始時刻",
                    value=format_time_only(break_start_time),
                    inline=True
                )
                
                log_user_action(
                    logger, interaction.user.id, "break_start",
                    time=break_start_time.isoformat()
                )
            else:
                raise SystemError("Failed to start break", error_code="BREAK_START_FAILED")
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            result = await self.error_handler.handle_error_async(e, context)
            if result.should_notify_user:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=result.user_message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🟢 休憩終了', style=discord.ButtonStyle.secondary, custom_id='break_end')
    async def break_end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩終了ボタン"""
        await interaction.response.defer()
        
        context = ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command="attendance_break_end"
        )
        
        try:
            db_manager = get_database_manager()
            
            # ユーザー情報を取得
            user = await db_manager.get_user(interaction.user.id)
            if not user:
                raise UserError(
                    "User not found",
                    "出勤記録が見つかりません。まず出勤してください。",
                    error_code="USER_NOT_FOUND"
                )
            
            today_date = format_date_only(today_jst())
            today_record = await db_manager.get_attendance_record(user['discord_id'], today_date)
            
            if not today_record or not today_record.get('check_in'):
                raise UserError(
                    "No check-in record found",
                    "出勤記録がありません。まず出勤してください。",
                    error_code="NO_CHECK_IN"
                )
            
            if not today_record.get('break_start'):
                raise UserError(
                    "No break started",
                    "休憩を開始していません。",
                    error_code="NO_BREAK_STARTED"
                )
            
            if today_record.get('break_end'):
                raise UserError(
                    "Break already ended",
                    "既に休憩を終了しています。",
                    error_code="BREAK_ALREADY_ENDED"
                )
            
            # 休憩終了記録
            break_end_time = now_jst()
            break_duration = calculate_time_difference(
                today_record['break_start'], break_end_time
            )
            
            success = await db_manager.update_attendance_record(
                user['discord_id'], today_date, break_end=break_end_time
            )
            
            if success:
                embed = discord.Embed(
                    title="🟢 休憩終了",
                    description="休憩を終了しました",
                    color=discord.Color.green(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="休憩終了時刻",
                    value=format_time_only(break_end_time),
                    inline=True
                )
                embed.add_field(
                    name="休憩時間",
                    value=f"{break_duration:.1f}時間",
                    inline=True
                )
                
                log_user_action(
                    logger, interaction.user.id, "break_end",
                    time=break_end_time.isoformat(),
                    break_duration=break_duration
                )
            else:
                raise SystemError("Failed to end break", error_code="BREAK_END_FAILED")
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            result = await self.error_handler.handle_error_async(e, context)
            if result.should_notify_user:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=result.user_message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)


class AttendanceCog(commands.Cog):
    """出退勤管理機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = get_error_handler()
        # 永続的なViewを追加
        bot.add_view(AttendanceView())
    
    @commands.command(name='出退勤', aliases=['attendance', 'punch'])
    @handle_errors()
    async def attendance_panel(self, ctx):
        """出退勤管理パネルを表示"""
        embed = discord.Embed(
            title="🏢 出退勤管理システム",
            description="以下のボタンで出退勤を記録してください",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        embed.add_field(
            name="🟢 出勤",
            value="勤務開始時にクリック",
            inline=True
        )
        embed.add_field(
            name="🔴 退勤", 
            value="勤務終了時にクリック",
            inline=True
        )
        embed.add_field(
            name="🟡 休憩",
            value="休憩の開始・終了時にクリック",
            inline=True
        )
        
        embed.add_field(
            name="📊 勤怠確認",
            value="`!勤怠確認` コマンドで個人の勤怠を確認",
            inline=False
        )
        embed.add_field(
            name="📈 月次勤怠",
            value="`!月次勤怠` コマンドで月次レポートを確認",
            inline=False
        )
        embed.add_field(
            name="📋 CSV出力",
            value="`!勤怠CSV` コマンドで勤怠データをCSVでダウンロード",
            inline=False
        )
        
        embed.set_footer(text="企業用Discord Bot - 出退勤管理")
        
        view = AttendanceView()
        await ctx.send(embed=embed, view=view)
        
        log_command_execution(
            logger, "attendance_panel", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )
    
    @commands.command(name='勤怠確認', aliases=['attendance_status', 'status'])
    @require_registration
    @handle_errors()
    async def check_attendance(self, ctx, target_date: str = None):
        """自分の勤怠状況を確認"""
        db_manager = get_database_manager()
        
        # 日付を設定
        if target_date is None:
            target_date = format_date_only(today_jst())
        else:
            try:
                parse_date_string(target_date)  # 検証のみ
            except ValueError as e:
                raise UserError(str(e), str(e), error_code="INVALID_DATE_FORMAT")
        
        # 勤怠記録を取得
        record = await db_manager.get_attendance_record(ctx.author.id, target_date)
        
        if not record:
            embed = discord.Embed(
                title="📊 勤怠状況",
                description=f"{target_date} の勤怠記録はありません",
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title=f"📊 勤怠状況 - {target_date}",
                color=discord.Color.blue(),
                timestamp=now_jst()
            )
            
            # ステータスを判定
            status = "未出勤"
            status_emoji = "⚪"
            
            if record.get('check_in'):
                if record.get('check_out'):
                    status = "退勤"
                    status_emoji = "🔴"
                elif record.get('break_start') and not record.get('break_end'):
                    status = "休憩中"
                    status_emoji = "🟡"
                else:
                    status = "在席"
                    status_emoji = "🟢"
            
            embed.add_field(
                name="現在のステータス",
                value=f"{status_emoji} {status}",
                inline=True
            )
            
            if record.get('check_in'):
                embed.add_field(
                    name="出勤時刻",
                    value=format_time_only(record['check_in']),
                    inline=True
                )
            
            if record.get('check_out'):
                embed.add_field(
                    name="退勤時刻",
                    value=format_time_only(record['check_out']),
                    inline=True
                )
            
            if record.get('work_hours'):
                embed.add_field(
                    name="勤務時間",
                    value=f"{record['work_hours']:.1f}時間",
                    inline=True
                )
            
            if record.get('overtime_hours') and record['overtime_hours'] > 0:
                embed.add_field(
                    name="残業時間",
                    value=f"{record['overtime_hours']:.1f}時間",
                    inline=True
                )
            
            if record.get('break_start') and record.get('break_end'):
                break_duration = calculate_time_difference(
                    record['break_start'], 
                    record['break_end']
                )
                embed.add_field(
                    name="休憩時間",
                    value=f"{break_duration:.1f}時間",
                    inline=True
                )
        
        embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "check_attendance", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True,
            target_date=target_date
        )
    
    @commands.command(name='在席状況', aliases=['who_is_here', 'status_all'])
    @handle_errors()
    async def show_all_status(self, ctx):
        """全員の在席状況を表示"""
        db_manager = get_database_manager()
        
        # 今日の日付
        today_date = format_date_only(today_jst())
        
        # 全ユーザーを取得
        users = await db_manager.list_users()
        
        if not users:
            await ctx.send("登録されているユーザーが見つかりませんでした。")
            return
        
        embed = discord.Embed(
            title="👥 在席状況一覧",
            description=f"現在の時刻: {format_time_only(now_jst())}",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        # ステータス別にユーザーを分類
        status_groups = {
            '在席': [],
            '休憩中': [],
            '退勤': [],
            '未出勤': []
        }
        
        for user in users:
            display_name = user['display_name'] or user['username']
            
            # 今日の出勤記録を取得
            record = await db_manager.get_attendance_record(user['discord_id'], today_date)
            
            if not record or not record.get('check_in'):
                status = '未出勤'
                time_info = ""
            elif record.get('check_out'):
                status = '退勤'
                time_info = f" (出勤: {format_time_only(record['check_in'])})"
            elif record.get('break_start') and not record.get('break_end'):
                status = '休憩中'
                time_info = f" (出勤: {format_time_only(record['check_in'])})"
            else:
                status = '在席'
                time_info = f" (出勤: {format_time_only(record['check_in'])})"
            
            status_groups[status].append(f"{display_name}{time_info}")
        
        # 各ステータスごとにフィールドを追加
        status_emojis = {
            '在席': '🟢',
            '休憩中': '🟡', 
            '退勤': '🔴',
            '未出勤': '⚫'
        }
        
        for status, users_list in status_groups.items():
            if users_list:
                emoji = status_emojis.get(status, '⚪')
                embed.add_field(
                    name=f"{emoji} {status} ({len(users_list)}名)",
                    value='\n'.join(users_list[:10]) + ('...' if len(users_list) > 10 else ''),
                    inline=True
                )
        
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "show_all_status", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )
    
    @commands.command(name='月次勤怠', aliases=['monthly_report'])
    @require_registration
    @handle_errors()
    async def monthly_attendance_report(self, ctx, year: int = None, month: int = None):
        """月次勤怠レポートを表示"""
        db_manager = get_database_manager()
        
        # デフォルト値を設定
        if year is None or month is None:
            now = now_jst()
            year = year or now.year
            month = month or now.month
        
        # 月の妥当性をチェック
        if not (1 <= month <= 12):
            raise UserError(
                "Invalid month",
                "月は1〜12の範囲で指定してください。",
                error_code="INVALID_MONTH"
            )
        
        # 月の日付範囲を取得
        start_date, end_date = get_month_date_range(year, month)
        start_date_str = format_date_only(start_date)
        end_date_str = format_date_only(end_date)
        
        # 月次勤怠記録を取得
        records = await db_manager.get_attendance_by_date_range(
            ctx.author.id, start_date_str, end_date_str
        )
        
        if not records:
            embed = discord.Embed(
                title="📊 月次勤怠レポート",
                description=f"{year}年{month}月の勤怠記録はありません",
                color=discord.Color.orange()
            )
        else:
            # 統計を計算
            total_work_days = len([r for r in records if r.get('check_in')])
            total_work_hours = sum(r.get('work_hours', 0) for r in records)
            total_overtime_hours = sum(r.get('overtime_hours', 0) for r in records)
            avg_work_hours = total_work_hours / total_work_days if total_work_days > 0 else 0
            
            embed = discord.Embed(
                title=f"📊 月次勤怠レポート - {year}年{month}月",
                color=discord.Color.blue(),
                timestamp=now_jst()
            )
            
            embed.add_field(
                name="出勤日数",
                value=f"{total_work_days}日",
                inline=True
            )
            embed.add_field(
                name="総勤務時間",
                value=f"{total_work_hours:.1f}時間",
                inline=True
            )
            embed.add_field(
                name="総残業時間",
                value=f"{total_overtime_hours:.1f}時間",
                inline=True
            )
            embed.add_field(
                name="平均勤務時間",
                value=f"{avg_work_hours:.1f}時間/日",
                inline=True
            )
            
            # 詳細情報（最新5件）
            recent_records = sorted(records, key=lambda x: x['date'], reverse=True)[:5]
            details = []
            for record in recent_records:
                work_date = record['date']
                work_hours = record.get('work_hours', 0)
                overtime = record.get('overtime_hours', 0)
                
                # ステータスを判定
                if record.get('check_out'):
                    status = "退勤"
                elif record.get('check_in'):
                    status = "出勤中"
                else:
                    status = "未出勤"
                
                detail = f"**{work_date}**: {work_hours:.1f}h"
                if overtime > 0:
                    detail += f" (残業 {overtime:.1f}h)"
                detail += f" - {status}"
                details.append(detail)
            
            if details:
                embed.add_field(
                    name="最近の勤怠記録",
                    value='\n'.join(details),
                    inline=False
                )
        
        embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "monthly_attendance_report", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True,
            year=year, month=month
        )
    
    @commands.command(name='勤怠CSV', aliases=['attendance_csv', 'export_csv'])
    @require_registration
    @handle_errors()
    async def export_attendance_csv(self, ctx, start_date: str = None, end_date: str = None, user_mention: discord.Member = None):
        """勤怠データをCSV形式でエクスポート"""
        db_manager = get_database_manager()
        
        # 日付のデフォルト設定
        if not start_date or not end_date:
            # 今月のデータを出力
            year, month = now_jst().year, now_jst().month
            start_date_obj, end_date_obj = get_month_date_range(year, month)
            start_date = format_date_only(start_date_obj)
            end_date = format_date_only(end_date_obj)
        else:
            # 日付の妥当性チェック
            try:
                start_date_obj = parse_date_string(start_date)
                end_date_obj = parse_date_string(end_date)
                if start_date_obj > end_date_obj:
                    raise UserError(
                        "Invalid date range",
                        "開始日は終了日より前である必要があります。",
                        error_code="INVALID_DATE_RANGE"
                    )
            except ValueError as e:
                raise UserError(str(e), str(e), error_code="INVALID_DATE_FORMAT")
        
        # ユーザーの指定（管理者のみ他ユーザーのデータを取得可能）
        target_user_id = ctx.author.id
        filename_prefix = f"attendance_{ctx.author.name}"
        
        if user_mention:
            # 管理者権限チェック
            if not ctx.author.guild_permissions.administrator:
                raise UserError(
                    "Permission denied",
                    "他のユーザーのデータを取得するには管理者権限が必要です。",
                    error_code="PERMISSION_DENIED"
                )
            
            user = await db_manager.get_user(user_mention.id)
            if not user:
                raise UserError(
                    "User not found",
                    "指定されたユーザーの勤怠記録が見つかりません。",
                    error_code="USER_NOT_FOUND"
                )
            
            target_user_id = user_mention.id
            filename_prefix = f"attendance_{user_mention.name}"
        
        # データ取得
        attendance_data = await db_manager.get_attendance_by_date_range(
            target_user_id, start_date, end_date
        )
        
        if not attendance_data:
            raise UserError(
                "No data found",
                f"{start_date} から {end_date} の期間に勤怠データがありません。",
                error_code="NO_DATA_FOUND"
            )
        
        # CSV作成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            '日付', 'ユーザー名', '表示名', '出勤時刻', '退勤時刻',
            '休憩開始', '休憩終了', '総勤務時間（時間）', '残業時間（時間）', 'ステータス'
        ])
        
        # ユーザー情報を取得
        user_info = await db_manager.get_user(target_user_id)
        user_name = user_info['username'] if user_info else "Unknown"
        display_name = user_info['display_name'] if user_info else "Unknown"
        
        # データ行
        for record in attendance_data:
            # ステータスを判定
            if record.get('check_out'):
                status = "退勤"
            elif record.get('check_in'):
                status = "出勤中"
            else:
                status = "未出勤"
            
            writer.writerow([
                record.get('date', ''),
                user_name,
                display_name,
                format_time_only(record.get('check_in')),
                format_time_only(record.get('check_out')),
                format_time_only(record.get('break_start')),
                format_time_only(record.get('break_end')),
                f"{record.get('work_hours', 0):.1f}",
                f"{record.get('overtime_hours', 0):.1f}",
                status
            ])
        
        # ファイルとして送信
        output.seek(0)
        filename = f"{filename_prefix}_{start_date}_to_{end_date}.csv"
        
        # UTF-8 BOM付きで送信（Excelでの文字化け対策）
        bom = '\ufeff'
        csv_content = bom + output.getvalue()
        file = discord.File(io.BytesIO(csv_content.encode('utf-8')), filename=filename)
        
        embed = discord.Embed(
            title="📊 勤怠データエクスポート完了",
            description=f"期間: {start_date} から {end_date}",
            color=discord.Color.green(),
            timestamp=now_jst()
        )
        embed.add_field(
            name="レコード数",
            value=f"{len(attendance_data)}件",
            inline=True
        )
        
        await ctx.send(embed=embed, file=file)
        
        log_command_execution(
            logger, "export_attendance_csv", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True,
            start_date=start_date, end_date=end_date,
            target_user=user_mention.name if user_mention else "self"
        )
    
    @commands.command(name='勤怠CSV使い方', aliases=['csv_help'])
    @handle_errors()
    async def csv_help(self, ctx):
        """勤怠CSV出力の使い方を表示"""
        embed = discord.Embed(
            title="📋 勤怠CSV出力の使い方",
            description="勤怠データをCSV形式でダウンロードする方法",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="基本的な使い方",
            value="`!勤怠CSV` - 今月の自分の勤怠データを出力",
            inline=False
        )
        
        embed.add_field(
            name="期間を指定",
            value="`!勤怠CSV 2023-11-01 2023-11-30` - 指定期間のデータを出力",
            inline=False
        )
        
        embed.add_field(
            name="他のユーザーのデータ（管理者のみ）",
            value="`!勤怠CSV 2023-11-01 2023-11-30 @ユーザー名`",
            inline=False
        )
        
        embed.add_field(
            name="注意事項",
            value="• 日付はYYYY-MM-DD形式で指定\n• CSVファイルはUTF-8（BOM付き）で出力\n• Excelで開く際の文字化けを防止",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        log_command_execution(
            logger, "csv_help", ctx.author.id, 
            ctx.guild.id if ctx.guild else None, True
        )


async def setup(bot):
    """Cogのセットアップ"""
    await bot.add_cog(AttendanceCog(bot)) 