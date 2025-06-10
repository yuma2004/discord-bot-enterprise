import discord
from discord.ext import commands
from datetime import datetime, date
import logging
import os
import csv
import io
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
                color=discord.Color.orange()
            )
            clock_in_time = today_record['clock_in_time']
            if isinstance(clock_in_time, str):
                clock_in_time = datetime.fromisoformat(clock_in_time)
            embed.add_field(
                name="出勤時刻",
                value=clock_in_time.strftime("%H:%M"),
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
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="出勤時刻",
                    value=datetime.now().strftime("%H:%M"),
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
    
    @discord.ui.button(label='🔴 退勤', style=discord.ButtonStyle.red, custom_id='clock_out')
    async def clock_out_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """退勤ボタン"""
        await interaction.response.defer()
        
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
                timestamp=datetime.now()
            )
            
            if today_record:
                # PostgreSQLでは既にdatetimeオブジェクトで返される
                clock_in = today_record.get('clock_in_time')
                clock_out = today_record.get('clock_out_time')
                
                # 安全な日時変換
                try:
                    if clock_in:
                        if isinstance(clock_in, str):
                            clock_in = datetime.fromisoformat(clock_in)
                    if clock_out:
                        if isinstance(clock_out, str):
                            clock_out = datetime.fromisoformat(clock_out)
                except (ValueError, TypeError) as e:
                    logger.error(f"日時変換エラー: {e}")
                    clock_in = None
                    clock_out = None
                
                if clock_in:
                    embed.add_field(
                        name="出勤時刻",
                        value=clock_in.strftime("%H:%M"),
                        inline=True
                    )
                if clock_out:
                    embed.add_field(
                        name="退勤時刻",
                        value=clock_out.strftime("%H:%M"),
                        inline=True
                    )
                
                # 勤務時間の安全な表示
                total_hours = today_record.get('total_work_hours')
                if total_hours is not None:
                    embed.add_field(
                        name="勤務時間",
                        value=f"{total_hours:.1f}時間",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="勤務時間",
                        value="計算中...",
                        inline=True
                    )
                
                # 残業時間の安全な表示
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
    
    @discord.ui.button(label='🟡 休憩開始', style=discord.ButtonStyle.secondary, custom_id='break_start')
    async def break_start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩開始ボタン"""
        await interaction.response.defer()
        
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
                timestamp=datetime.now()
            )
            embed.add_field(
                name="休憩開始時刻",
                value=datetime.now().strftime("%H:%M"),
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
    
    @discord.ui.button(label='🟢 休憩終了', style=discord.ButtonStyle.secondary, custom_id='break_end')
    async def break_end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """休憩終了ボタン"""
        await interaction.response.defer()
        
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
                timestamp=datetime.now()
            )
            embed.add_field(
                name="休憩終了時刻",
                value=datetime.now().strftime("%H:%M"),
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
            color=discord.Color.blue()
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
        user = user_repo.get_user_by_discord_id(str(ctx.author.id))
        if not user:
            await ctx.send("まだ勤怠記録がありません。")
            return
        
        # 日付を設定
        if target_date is None:
            target_date = date.today().isoformat()
        else:
            try:
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                await ctx.send("日付の形式が正しくありません。YYYY-MM-DD形式で入力してください。")
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
                timestamp=datetime.now()
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
                clock_in = record['clock_in_time']
                if isinstance(clock_in, str):
                    clock_in = datetime.fromisoformat(clock_in)
                embed.add_field(
                    name="出勤時刻",
                    value=clock_in.strftime("%H:%M"),
                    inline=True
                )
            
            if record['clock_out_time']:
                clock_out = record['clock_out_time']
                if isinstance(clock_out, str):
                    clock_out = datetime.fromisoformat(clock_out)
                embed.add_field(
                    name="退勤時刻",
                    value=clock_out.strftime("%H:%M"),
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
                break_start = record['break_start_time']
                break_end = record['break_end_time']
                if isinstance(break_start, str):
                    break_start = datetime.fromisoformat(break_start)
                if isinstance(break_end, str):
                    break_end = datetime.fromisoformat(break_end)
                break_duration = (break_end - break_start).total_seconds() / 3600
                embed.add_field(
                    name="休憩時間",
                    value=f"{break_duration:.1f}時間",
                    inline=True
                )
        
        embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='在席状況', aliases=['who_is_here', 'status_all'])
    async def show_all_status(self, ctx):
        """全員の在席状況を表示"""
        all_status = attendance_repo.get_all_users_status()
        
        if not all_status:
            await ctx.send("在席情報が見つかりませんでした。")
            return
        
        embed = discord.Embed(
            title="👥 在席状況一覧",
            description=f"現在の時刻: {datetime.now().strftime('%H:%M')}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
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
                clock_in = user_status['clock_in_time']
                if isinstance(clock_in, str):
                    clock_in = datetime.fromisoformat(clock_in)
                time_info = f" (出勤: {clock_in.strftime('%H:%M')})"
            
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
    
    @commands.command(name='月次勤怠', aliases=['monthly_report'])
    async def monthly_attendance_report(self, ctx, year: int = None, month: int = None):
        """月次勤怠レポートを表示"""
        user = user_repo.get_user_by_discord_id(str(ctx.author.id))
        if not user:
            await ctx.send("まだ勤怠記録がありません。")
            return
        
        # デフォルト値を設定
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
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
                timestamp=datetime.now()
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
                name="平均勤務時間",
                value=f"{avg_work_hours:.1f}時間/日",
                inline=True
            )
            embed.add_field(
                name="総残業時間",
                value=f"{total_overtime_hours:.1f}時間",
                inline=True
            )
            
            # 最近の勤怠記録（最大5日分）
            recent_records = records[-5:]
            if recent_records:
                recent_text = []
                for record in recent_records:
                    date_str = record['work_date']
                    if record['clock_in_time'] and record['clock_out_time']:
                        clock_in = datetime.fromisoformat(record['clock_in_time'])
                        clock_out = datetime.fromisoformat(record['clock_out_time'])
                        work_hours = record['total_work_hours'] or 0
                        recent_text.append(
                            f"{date_str}: {clock_in.strftime('%H:%M')}-{clock_out.strftime('%H:%M')} "
                            f"({work_hours:.1f}h)"
                        )
                
                if recent_text:
                    embed.add_field(
                        name="最近の勤怠記録",
                        value='\n'.join(recent_text),
                        inline=False
                    )
        
        embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name='勤怠CSV', aliases=['attendance_csv', 'export_csv'])
    async def export_attendance_csv(self, ctx, start_date: str = None, end_date: str = None, user_mention: discord.Member = None):
        """
        勤怠データをCSV形式でエクスポート
        
        使用例:
        !勤怠CSV - 今月の全員分
        !勤怠CSV 2024-01-01 2024-01-31 - 指定期間の全員分
        !勤怠CSV 2024-01-01 2024-01-31 @ユーザー - 指定期間の特定ユーザー分
        """
        await ctx.defer()
        
        try:
            # デフォルトは今月
            if not start_date or not end_date:
                now = datetime.now()
                start_date = f"{now.year}-{now.month:02d}-01"
                # 今月末日を計算
                if now.month == 12:
                    next_month = datetime(now.year + 1, 1, 1)
                else:
                    next_month = datetime(now.year, now.month + 1, 1)
                import calendar
                last_day = calendar.monthrange(now.year, now.month)[1]
                end_date = f"{now.year}-{now.month:02d}-{last_day:02d}"
            
            # 日付の妥当性チェック
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                embed = discord.Embed(
                    title="❌ 日付形式エラー",
                    description="日付は YYYY-MM-DD 形式で入力してください",
                    color=discord.Color.red()
                )
                await ctx.followup.send(embed=embed)
                return
            
            if start_dt > end_dt:
                embed = discord.Embed(
                    title="❌ 日付範囲エラー",
                    description="開始日は終了日より前の日付を指定してください",
                    color=discord.Color.red()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # 特定ユーザー指定の場合
            target_user_id = None
            if user_mention:
                target_user = user_repo.get_or_create_user(
                    str(user_mention.id),
                    user_mention.name,
                    user_mention.display_name
                )
                target_user_id = target_user['id']
            
            # 勤怠データを取得
            attendance_data = attendance_repo.get_attendance_range(
                start_date, end_date, target_user_id
            )
            
            if not attendance_data:
                embed = discord.Embed(
                    title="📄 データなし",
                    description="指定された条件の勤怠データが見つかりませんでした",
                    color=discord.Color.orange()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # CSVファイルを作成
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)
            
            # ヘッダー行
            csv_writer.writerow([
                '日付', 'ユーザー名', '表示名', '出勤時刻', '退勤時刻',
                '休憩開始', '休憩終了', '総休憩時間（分）', '総勤務時間（時間）',
                '残業時間（時間）', 'ステータス', '備考'
            ])
            
            # データ行
            for record in attendance_data:
                # 時刻のフォーマット
                def format_time(time_str):
                    if not time_str:
                        return ''
                    try:
                        if isinstance(time_str, str):
                            dt = datetime.fromisoformat(time_str)
                        else:
                            dt = time_str
                        return dt.strftime('%H:%M')
                    except (ValueError, TypeError):
                        return str(time_str) if time_str else ''
                
                csv_writer.writerow([
                    record.get('date', ''),
                    record.get('username', ''),
                    record.get('display_name', ''),
                    format_time(record.get('clock_in_time')),
                    format_time(record.get('clock_out_time')),
                    format_time(record.get('break_start_time')),
                    format_time(record.get('break_end_time')),
                    record.get('total_break_minutes', 0),
                    f"{record.get('total_work_hours', 0):.1f}",
                    f"{record.get('overtime_hours', 0):.1f}",
                    record.get('status', ''),
                    record.get('notes', '')
                ])
            
            # CSVファイルをDiscordファイルとして送信
            csv_buffer.seek(0)
            csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig'))  # BOM付きUTF-8
            
            # ファイル名を生成
            user_suffix = f"_{user_mention.display_name}" if user_mention else "_全員"
            filename = f"勤怠記録_{start_date}_to_{end_date}{user_suffix}.csv"
            
            file = discord.File(csv_bytes, filename=filename)
            
            # 結果をEmbed
            embed = discord.Embed(
                title="📊 勤怠データCSVエクスポート完了",
                description=f"勤怠データをCSVファイルで出力しました",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📅 対象期間",
                value=f"{start_date} ～ {end_date}",
                inline=True
            )
            
            if user_mention:
                embed.add_field(
                    name="👤 対象ユーザー",
                    value=user_mention.display_name,
                    inline=True
                )
            else:
                embed.add_field(
                    name="👥 対象ユーザー",
                    value="全員",
                    inline=True
                )
            
            embed.add_field(
                name="📋 レコード数",
                value=f"{len(attendance_data)}件",
                inline=True
            )
            
            embed.add_field(
                name="💾 ファイル形式",
                value="CSV (UTF-8 BOM付き)",
                inline=False
            )
            
            embed.add_field(
                name="📝 使用方法",
                value="• Excel で開く場合：そのまま開けます\n• Googleスプレッドシート：インポート機能を使用",
                inline=False
            )
            
            embed.set_footer(text=f"出力者: {ctx.author.display_name}")
            
            await ctx.followup.send(embed=embed, file=file)
            
            logger.info(f"勤怠CSVエクスポート完了: {ctx.author.name}, 期間: {start_date}-{end_date}, レコード数: {len(attendance_data)}")
            
        except Exception as e:
            logger.error(f"勤怠CSVエクスポートエラー: {e}")
            embed = discord.Embed(
                title="❌ エラー",
                description="CSVエクスポート中にエラーが発生しました",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed)

    @commands.command(name='勤怠CSV使い方', aliases=['csv_help'])
    async def csv_help(self, ctx):
        """勤怠CSVコマンドの使い方を説明"""
        embed = discord.Embed(
            title="📊 勤怠CSV出力 - 使い方ガイド",
            description="勤怠データをCSV形式でエクスポートする方法を説明します",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔸 基本使用法",
            value="`!勤怠CSV` - 今月の全員分を出力",
            inline=False
        )
        
        embed.add_field(
            name="🔸 期間指定",
            value="`!勤怠CSV 2024-01-01 2024-01-31` - 指定期間の全員分",
            inline=False
        )
        
        embed.add_field(
            name="🔸 ユーザー指定",
            value="`!勤怠CSV 2024-01-01 2024-01-31 @ユーザー名` - 特定ユーザーのみ",
            inline=False
        )
        
        embed.add_field(
            name="📋 CSVの項目",
            value="• 日付\n• ユーザー名・表示名\n• 出勤・退勤時刻\n• 休憩時間\n• 総勤務時間\n• 残業時間\n• ステータス",
            inline=False
        )
        
        embed.add_field(
            name="💡 ヒント",
            value="• CSV形式はUTF-8 BOM付きで出力されます\n• Excelで直接開くことができます\n• 管理者権限は不要です",
            inline=False
        )
        
        embed.set_footer(text="企業用Discord Bot - 勤怠管理")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(AttendanceCog(bot)) 