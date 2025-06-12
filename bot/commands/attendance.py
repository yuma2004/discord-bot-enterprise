import discord
from discord.ext import commands
from datetime import datetime, date
import logging
import os
import csv
import io
from config import Config
from bot.utils.datetime_utils import (
    now_jst, today_jst, ensure_jst, format_time_only, 
    format_datetime_for_display, get_month_date_range,
    parse_date_string, calculate_work_hours
)
from bot.utils.database_utils import DatabaseError

# データベースの動的選択
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import user_repo, attendance_repo
else:
    from database import user_repo, attendance_repo

logger = logging.getLogger(__name__)


class AttendanceView(discord.ui.View):
    """出退勤管理用のボタンUI"""
    
    def __init__(self):
        super().__init__(timeout=None)  # タイムアウトなし
    
    @discord.ui.button(label='🟢 出勤', style=discord.ButtonStyle.green, custom_id='clock_in')
    async def clock_in_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """出勤ボタン"""
        await interaction.response.defer()
        
        try:
            # ユーザー情報を取得または作成
            user = user_repo.get_or_create_user(
                str(interaction.user.id),
                interaction.user.name,
                interaction.user.display_name
            )
            
            # 今日の出退勤記録を確認
            today_record = attendance_repo.get_today_attendance(user['id'])
            
            if today_record and today_record['clock_in_time']:
                embed = discord.Embed(
                    title="⚠️ 既に出勤済み",
                    description="本日は既に出勤記録があります",
                    color=discord.Color.orange(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="出勤時刻",
                    value=format_time_only(today_record['clock_in_time']),
                    inline=True
                )
                embed.add_field(
                    name="現在のステータス",
                    value=today_record['status'],
                    inline=True
                )
            else:
                # 出勤記録
                success = attendance_repo.clock_in(user['id'])
                
                if success:
                    embed = discord.Embed(
                        title="🟢 出勤記録完了",
                        description="お疲れ様です！出勤を記録しました",
                        color=discord.Color.green(),
                        timestamp=now_jst()
                    )
                    embed.add_field(
                        name="出勤時刻",
                        value=format_time_only(now_jst()),
                        inline=True
                    )
                    embed.add_field(
                        name="ステータス",
                        value="在席",
                        inline=True
                    )
                else:
                    embed = discord.Embed(
                        title="❌ エラー",
                        description="出勤記録に失敗しました",
                        color=discord.Color.red()
                    )
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"データベースエラー in clock_in_button: {e}")
            embed = discord.Embed(
                title="❌ システムエラー",
                description="データベースエラーが発生しました。管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"予期しないエラー in clock_in_button: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ エラー",
                description="予期しないエラーが発生しました",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🔴 退勤', style=discord.ButtonStyle.red, custom_id='clock_out')
    async def clock_out_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """退勤ボタン"""
        await interaction.response.defer()
        
        try:
            user = user_repo.get_or_create_user(
                str(interaction.user.id),
                interaction.user.name,
                interaction.user.display_name
            )
            
            # 退勤記録
            success = attendance_repo.clock_out(user['id'])
            
            if success:
                # 今日の記録を取得して勤務時間を表示
                today_record = attendance_repo.get_today_attendance(user['id'])
                
                embed = discord.Embed(
                    title="🔴 退勤記録完了",
                    description="お疲れ様でした！退勤を記録しました",
                    color=discord.Color.red(),
                    timestamp=now_jst()
                )
                
                if today_record:
                    clock_in_time = format_time_only(today_record.get('clock_in_time'))
                    clock_out_time = format_time_only(today_record.get('clock_out_time'))
                    
                    if clock_in_time:
                        embed.add_field(
                            name="出勤時刻",
                            value=clock_in_time,
                            inline=True
                        )
                    if clock_out_time:
                        embed.add_field(
                            name="退勤時刻",
                            value=clock_out_time,
                            inline=True
                        )
                    
                    # 勤務時間の表示
                    total_hours = today_record.get('total_work_hours')
                    if total_hours is not None:
                        embed.add_field(
                            name="勤務時間",
                            value=f"{total_hours:.1f}時間",
                            inline=True
                        )
                    
                    # 残業時間の表示
                    overtime_hours = today_record.get('overtime_hours')
                    if overtime_hours is not None and overtime_hours > 0:
                        embed.add_field(
                            name="残業時間",
                            value=f"{overtime_hours:.1f}時間",
                            inline=True
                        )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description="退勤記録に失敗しました。出勤記録がない可能性があります",
                    color=discord.Color.red()
                )
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"データベースエラー in clock_out_button: {e}")
            embed = discord.Embed(
                title="❌ システムエラー",
                description="データベースエラーが発生しました。管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"予期しないエラー in clock_out_button: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ エラー",
                description="予期しないエラーが発生しました",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🟡 休憩開始', style=discord.ButtonStyle.secondary, custom_id='break_start')
    async def break_start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩開始ボタン"""
        await interaction.response.defer()
        
        try:
            user = user_repo.get_or_create_user(
                str(interaction.user.id),
                interaction.user.name,
                interaction.user.display_name
            )
            
            success = attendance_repo.start_break(user['id'])
            
            if success:
                embed = discord.Embed(
                    title="🟡 休憩開始",
                    description="休憩を開始しました",
                    color=discord.Color.gold(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="休憩開始時刻",
                    value=format_time_only(now_jst()),
                    inline=True
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description="休憩開始に失敗しました。出勤記録を確認してください",
                    color=discord.Color.red()
                )
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"エラー in break_start_button: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ エラー",
                description="予期しないエラーが発生しました",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='🟢 休憩終了', style=discord.ButtonStyle.secondary, custom_id='break_end')
    async def break_end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩終了ボタン"""
        await interaction.response.defer()
        
        try:
            user = user_repo.get_or_create_user(
                str(interaction.user.id),
                interaction.user.name,
                interaction.user.display_name
            )
            
            success = attendance_repo.end_break(user['id'])
            
            if success:
                embed = discord.Embed(
                    title="🟢 休憩終了",
                    description="休憩を終了しました",
                    color=discord.Color.green(),
                    timestamp=now_jst()
                )
                embed.add_field(
                    name="休憩終了時刻",
                    value=format_time_only(now_jst()),
                    inline=True
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description="休憩終了に失敗しました。休憩開始記録を確認してください",
                    color=discord.Color.red()
                )
            
            embed.set_footer(text=f"{interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"エラー in break_end_button: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ エラー",
                description="予期しないエラーが発生しました",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class AttendanceCog(commands.Cog):
    """出退勤管理機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.attendance_channel_id = None  # 出退勤チャンネルのID
        self.last_panel_message = None    # 最後のパネルメッセージ
        # 永続的なViewを追加
        bot.add_view(AttendanceView())
    
    @commands.command(name='出退勤', aliases=['attendance', 'punch'])
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
    
    @commands.command(name='勤怠確認', aliases=['attendance_status', 'status'])
    async def check_attendance(self, ctx, target_date: str = None):
        """自分の勤怠状況を確認"""
        try:
            user = user_repo.get_user_by_discord_id(str(ctx.author.id))
            if not user:
                await ctx.send("まだ勤怠記録がありません。")
                return
            
            # 日付を設定
            if target_date is None:
                target_date = today_jst().isoformat()
            else:
                try:
                    parse_date_string(target_date)  # 検証のみ
                except ValueError as e:
                    await ctx.send(str(e))
                    return
            
            # 勤怠記録を取得
            record = attendance_repo.get_today_attendance(user['id'], target_date)
            
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
                
                # ステータス表示
                status_color = {
                    '在席': '🟢',
                    '離席': '⚫',
                    '休憩中': '🟡',
                    '退勤': '🔴'
                }.get(record['status'], '⚪')
                
                embed.add_field(
                    name="現在のステータス",
                    value=f"{status_color} {record['status']}",
                    inline=True
                )
                
                if record['clock_in_time']:
                    embed.add_field(
                        name="出勤時刻",
                        value=format_time_only(record['clock_in_time']),
                        inline=True
                    )
                
                if record['clock_out_time']:
                    embed.add_field(
                        name="退勤時刻",
                        value=format_time_only(record['clock_out_time']),
                        inline=True
                    )
                
                if record['total_work_hours']:
                    embed.add_field(
                        name="勤務時間",
                        value=f"{record['total_work_hours']:.1f}時間",
                        inline=True
                    )
                
                if record['overtime_hours'] and record['overtime_hours'] > 0:
                    embed.add_field(
                        name="残業時間",
                        value=f"{record['overtime_hours']:.1f}時間",
                        inline=True
                    )
                
                if record['break_start_time'] and record['break_end_time']:
                    break_duration = calculate_work_hours(
                        record['break_start_time'], 
                        record['break_end_time']
                    )
                    embed.add_field(
                        name="休憩時間",
                        value=f"{break_duration:.1f}時間",
                        inline=True
                    )
            
            embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"エラー in check_attendance: {e}", exc_info=True)
            await ctx.send("勤怠情報の取得中にエラーが発生しました。")
    
    @commands.command(name='在席状況', aliases=['who_is_here', 'status_all'])
    async def show_all_status(self, ctx):
        """全員の在席状況を表示"""
        try:
            all_status = attendance_repo.get_all_users_status()
            
            if not all_status:
                await ctx.send("在席情報が見つかりませんでした。")
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
                '離席': []
            }
            
            for user_status in all_status:
                status = user_status['status']
                display_name = user_status['display_name'] or user_status['username']
                
                time_info = ""
                if user_status['clock_in_time'] and status != '離席':
                    time_info = f" (出勤: {format_time_only(user_status['clock_in_time'])})"
                
                status_groups[status].append(f"{display_name}{time_info}")
            
            # 各ステータスごとにフィールドを追加
            status_emojis = {
                '在席': '🟢',
                '休憩中': '🟡', 
                '退勤': '🔴',
                '離席': '⚫'
            }
            
            for status, users in status_groups.items():
                if users:
                    emoji = status_emojis.get(status, '⚪')
                    embed.add_field(
                        name=f"{emoji} {status} ({len(users)}名)",
                        value='\n'.join(users[:10]) + ('...' if len(users) > 10 else ''),
                        inline=True
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"エラー in show_all_status: {e}", exc_info=True)
            await ctx.send("在席状況の取得中にエラーが発生しました。")
    
    @commands.command(name='月次勤怠', aliases=['monthly_report'])
    async def monthly_attendance_report(self, ctx, year: int = None, month: int = None):
        """月次勤怠レポートを表示"""
        try:
            user = user_repo.get_user_by_discord_id(str(ctx.author.id))
            if not user:
                await ctx.send("まだ勤怠記録がありません。")
                return
            
            # デフォルト値を設定
            if year is None or month is None:
                now = now_jst()
                year = year or now.year
                month = month or now.month
            
            # 月の妥当性をチェック
            if not (1 <= month <= 12):
                await ctx.send("月は1〜12の範囲で指定してください。")
                return
            
            # 月次勤怠記録を取得
            records = attendance_repo.get_monthly_attendance(user['id'], year, month)
            
            if not records:
                embed = discord.Embed(
                    title="📊 月次勤怠レポート",
                    description=f"{year}年{month}月の勤怠記録はありません",
                    color=discord.Color.orange()
                )
            else:
                # 統計を計算
                total_work_days = len([r for r in records if r['clock_in_time']])
                total_work_hours = sum(r['total_work_hours'] or 0 for r in records)
                total_overtime_hours = sum(r['overtime_hours'] or 0 for r in records)
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
                recent_records = sorted(records, key=lambda x: x['work_date'], reverse=True)[:5]
                details = []
                for record in recent_records:
                    work_date = record['work_date']
                    work_hours = record['total_work_hours'] or 0
                    overtime = record['overtime_hours'] or 0
                    status = record['status'] or '未出勤'
                    
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
            
        except Exception as e:
            logger.error(f"エラー in monthly_attendance_report: {e}", exc_info=True)
            await ctx.send("月次勤怠レポートの取得中にエラーが発生しました。")
    
    @commands.command(name='勤怠CSV', aliases=['attendance_csv', 'export_csv'])
    async def export_attendance_csv(self, ctx, start_date: str = None, end_date: str = None, user_mention: discord.Member = None):
        """勤怠データをCSV形式でエクスポート"""
        try:
            # 日付のデフォルト設定
            if not start_date or not end_date:
                # 今月のデータを出力
                year, month = now_jst().year, now_jst().month
                start_date_obj, end_date_obj = get_month_date_range(year, month)
                start_date = start_date_obj.isoformat()
                end_date = end_date_obj.isoformat()
            else:
                # 日付の妥当性チェック
                try:
                    start_date_obj = parse_date_string(start_date)
                    end_date_obj = parse_date_string(end_date)
                    if start_date_obj > end_date_obj:
                        await ctx.send("開始日は終了日より前である必要があります。")
                        return
                except ValueError as e:
                    await ctx.send(str(e))
                    return
            
            # ユーザーの指定（管理者のみ他ユーザーのデータを取得可能）
            target_user_id = None
            filename_prefix = "attendance"
            
            if user_mention:
                # 管理者権限チェック
                if not ctx.author.guild_permissions.administrator:
                    await ctx.send("他のユーザーのデータを取得するには管理者権限が必要です。")
                    return
                
                user = user_repo.get_user_by_discord_id(str(user_mention.id))
                if user:
                    target_user_id = user['id']
                    filename_prefix = f"attendance_{user_mention.name}"
                else:
                    await ctx.send("指定されたユーザーの勤怠記録が見つかりません。")
                    return
            else:
                # 自分のデータ
                user = user_repo.get_user_by_discord_id(str(ctx.author.id))
                if user:
                    target_user_id = user['id']
                    filename_prefix = f"attendance_{ctx.author.name}"
                else:
                    await ctx.send("勤怠記録が見つかりません。")
                    return
            
            # データ取得
            attendance_data = attendance_repo.get_attendance_range(start_date, end_date, target_user_id)
            
            if not attendance_data:
                await ctx.send(f"{start_date} から {end_date} の期間に勤怠データがありません。")
                return
            
            # CSV作成
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー
            writer.writerow([
                '日付', 'ユーザー名', '表示名', '出勤時刻', '退勤時刻',
                '休憩開始', '休憩終了', '総休憩時間（分）', '総勤務時間（時間）',
                '残業時間（時間）', 'ステータス', '備考'
            ])
            
            # データ行
            for record in attendance_data:
                writer.writerow([
                    record.get('date', ''),
                    record.get('username', ''),
                    record.get('display_name', ''),
                    format_time_only(record.get('clock_in_time')),
                    format_time_only(record.get('clock_out_time')),
                    format_time_only(record.get('break_start_time')),
                    format_time_only(record.get('break_end_time')),
                    record.get('total_break_minutes', 0),
                    f"{record.get('total_work_hours', 0):.1f}",
                    f"{record.get('overtime_hours', 0):.1f}",
                    record.get('status', ''),
                    record.get('notes', '')
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
            
        except Exception as e:
            logger.error(f"エラー in export_attendance_csv: {e}", exc_info=True)
            await ctx.send("CSV出力中にエラーが発生しました。")
    
    @commands.command(name='勤怠CSV使い方', aliases=['csv_help'])
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


async def setup(bot):
    """Cogのセットアップ"""
    await bot.add_cog(AttendanceCog(bot)) 