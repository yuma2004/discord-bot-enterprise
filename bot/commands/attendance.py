import discord
from discord.ext import commands
from datetime import datetime, date
import logging
import os
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
                clock_in = today_record['clock_in_time']
                clock_out = today_record['clock_out_time']
                
                # 文字列の場合は変換（SQLite互換性のため）
                if isinstance(clock_in, str):
                    clock_in = datetime.fromisoformat(clock_in)
                if isinstance(clock_out, str):
                    clock_out = datetime.fromisoformat(clock_out)
                
                embed.add_field(
                    name="出勤時刻",
                    value=clock_in.strftime("%H:%M"),
                    inline=True
                )
                embed.add_field(
                    name="退勤時刻",
                    value=clock_out.strftime("%H:%M"),
                    inline=True
                )
                embed.add_field(
                    name="勤務時間",
                    value=f"{today_record['total_work_hours']:.1f}時間",
                    inline=True
                )
                
                if today_record['overtime_hours'] > 0:
                    embed.add_field(
                        name="残業時間",
                        value=f"{today_record['overtime_hours']:.1f}時間",
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
    
    @commands.command(name='出退勤', aliases=['attendance', 'punch'])
    async def attendance_panel(self, ctx):
        """出退勤管理パネルを表示（常に最新メッセージとして表示）"""
        # 出退勤チャンネルかどうかチェック
        if ctx.channel.name == '出退勤':
            # Botの古いメッセージを削除（最新10件をチェック）
            async for message in ctx.channel.history(limit=10):
                if message.author == self.bot.user and message.embeds:
                    try:
                        embed = message.embeds[0]
                        if embed.title and "出退勤管理システム" in embed.title:
                            await message.delete()
                            logger.info("古い出退勤パネルを削除しました")
                    except discord.errors.NotFound:
                        pass  # メッセージが既に削除されている
                    except Exception as e:
                        logger.warning(f"メッセージ削除エラー: {e}")
        
        embed = discord.Embed(
            title="🕐 出退勤管理システム",
            description="下のボタンを使って出退勤を記録してください",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 使用方法",
            value="🟢 **出勤**: 出勤時に押してください\n"
                  "🔴 **退勤**: 退勤時に押してください\n"
                  "🟡 **休憩開始**: 休憩に入る時に押してください\n"
                  "🟢 **休憩終了**: 休憩から戻った時に押してください",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ 注意事項",
            value="・記録は個人にのみ表示されます\n"
                  "・勤務時間は自動計算されます\n"
                  "・8時間を超えた分は残業時間として記録されます",
            inline=False
        )
        
        embed.set_footer(text="📌 このパネルは常に最新の状態で表示されます")
        
        view = AttendanceView()
        message = await ctx.send(embed=embed, view=view)
        
        # 出退勤チャンネルの場合は情報を保存
        if ctx.channel.name == '出退勤':
            self.attendance_channel_id = ctx.channel.id
            self.last_panel_message = message
            logger.info(f"出退勤パネルを更新しました: {message.id}")
    
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

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(AttendanceCog(bot)) 