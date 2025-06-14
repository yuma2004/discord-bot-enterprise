import discord
from discord.ext import commands, tasks
from datetime import datetime, time, date, timedelta
import logging
from bot.utils.google_api import google_calendar_service
from bot.utils.datetime_utils import now_jst

logger = logging.getLogger(__name__)

class CalendarCog(commands.Cog):
    """Googleカレンダー連携機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 定期実行タスクを開始
        if google_calendar_service.is_available():
            self.meeting_reminder.start()
            self.daily_schedule_share.start()
            logger.info("カレンダーリマインド機能を開始しました")
        else:
            logger.warning("Googleカレンダー機能は利用できません")
    
    @commands.command(name='今日の予定', aliases=['today_schedule', 'today'])
    async def show_today_schedule(self, ctx):
        """今日の予定を表示"""
        if not google_calendar_service.is_available():
            embed = discord.Embed(
                title="❌ カレンダー機能無効",
                description="Googleカレンダー連携が設定されていません。\n管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # 今日の予定を取得
            events = await google_calendar_service.get_today_events()
            
            embed = discord.Embed(
                title=f"📅 今日の予定 ({date.today().strftime('%Y-%m-%d')})",
                color=discord.Color.blue(),
                timestamp=now_jst()
            )
            
            if not events:
                embed.description = "今日の予定はありません"
            else:
                # 予定を時系列で表示
                schedule_text = []
                for event in events:
                    if event['all_day']:
                        time_str = "終日"
                    else:
                        start_time = event['start'].strftime("%H:%M")
                        end_time = event['end'].strftime("%H:%M")
                        time_str = f"{start_time}-{end_time}"
                    
                    location_str = f" @{event['location']}" if event['location'] else ""
                    
                    schedule_text.append(f"🕐 **{time_str}** {event['summary']}{location_str}")
                
                # 長すぎる場合は分割
                if len(schedule_text) > 10:
                    embed.add_field(
                        name="午前の予定",
                        value='\n'.join(schedule_text[:5]),
                        inline=False
                    )
                    embed.add_field(
                        name="午後の予定",
                        value='\n'.join(schedule_text[5:10]),
                        inline=False
                    )
                    if len(schedule_text) > 10:
                        embed.add_field(
                            name="その他",
                            value=f"他 {len(schedule_text) - 10} 件の予定があります",
                            inline=False
                        )
                else:
                    embed.description = '\n'.join(schedule_text)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"今日の予定表示エラー: {e}")
            await ctx.send("予定の取得中にエラーが発生しました。")
    
    @commands.command(name='週間予定', aliases=['week_schedule', 'week'])
    async def show_week_schedule(self, ctx):
        """今週の予定を表示"""
        if not google_calendar_service.is_available():
            embed = discord.Embed(
                title="❌ カレンダー機能無効",
                description="Googleカレンダー連携が設定されていません。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # 今週の予定を取得
            events = await google_calendar_service.get_week_events()
            
            # 今週の開始日と終了日を計算
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            embed = discord.Embed(
                title=f"📅 週間予定 ({start_of_week.strftime('%m/%d')} - {end_of_week.strftime('%m/%d')})",
                color=discord.Color.blue(),
                timestamp=now_jst()
            )
            
            if not events:
                embed.description = "今週の予定はありません"
            else:
                # 日付別に予定をグループ化
                daily_events = {}
                for event in events:
                    event_date = event['start'].date()
                    if event_date not in daily_events:
                        daily_events[event_date] = []
                    daily_events[event_date].append(event)
                
                # 日付順にソート
                sorted_dates = sorted(daily_events.keys())
                
                for event_date in sorted_dates:
                    day_events = daily_events[event_date]
                    
                    # 曜日を取得
                    weekday_names = ['月', '火', '水', '木', '金', '土', '日']
                    weekday = weekday_names[event_date.weekday()]
                    
                    # その日の予定リストを作成
                    event_texts = []
                    for event in day_events[:3]:  # 最大3件まで表示
                        if event['all_day']:
                            time_str = "終日"
                        else:
                            time_str = event['start'].strftime("%H:%M")
                        
                        event_texts.append(f"• {time_str} {event['summary']}")
                    
                    if len(day_events) > 3:
                        event_texts.append(f"• 他 {len(day_events) - 3} 件")
                    
                    embed.add_field(
                        name=f"{event_date.strftime('%m/%d')}({weekday})",
                        value='\n'.join(event_texts) if event_texts else "予定なし",
                        inline=True
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"週間予定表示エラー: {e}")
            await ctx.send("予定の取得中にエラーが発生しました。")
    
    @commands.command(name='次の予定', aliases=['next_meeting', 'next'])
    async def show_next_meeting(self, ctx):
        """次の予定を表示"""
        if not google_calendar_service.is_available():
            await ctx.send("Googleカレンダー機能が利用できません。")
            return
        
        try:
            # 今後24時間以内の予定を取得
            events = await google_calendar_service.get_upcoming_events(minutes=1440)  # 24時間
            
            if not events:
                embed = discord.Embed(
                    title="📅 次の予定",
                    description="今後24時間以内に予定はありません",
                    color=discord.Color.blue()
                )
            else:
                next_event = events[0]  # 最初の予定が次の予定
                
                embed = discord.Embed(
                    title="📅 次の予定",
                    color=discord.Color.green(),
                    timestamp=now_jst()
                )
                
                embed.add_field(
                    name="会議名",
                    value=next_event['summary'],
                    inline=False
                )
                
                if next_event['all_day']:
                    time_str = next_event['start'].strftime('%Y-%m-%d') + " (終日)"
                else:
                    time_str = next_event['start'].strftime('%Y-%m-%d %H:%M')
                    
                    # 開始までの時間を計算
                    now = datetime.now()
                    time_until = next_event['start'] - now
                    if time_until.total_seconds() > 0:
                        hours = int(time_until.total_seconds() // 3600)
                        minutes = int((time_until.total_seconds() % 3600) // 60)
                        time_str += f" (あと{hours}時間{minutes}分)"
                
                embed.add_field(
                    name="開始時刻",
                    value=time_str,
                    inline=True
                )
                
                if next_event['location']:
                    embed.add_field(
                        name="場所",
                        value=next_event['location'],
                        inline=True
                    )
                
                if next_event['description']:
                    # 説明が長い場合は省略
                    description = next_event['description'][:200]
                    if len(next_event['description']) > 200:
                        description += "..."
                    embed.add_field(
                        name="詳細",
                        value=description,
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"次の予定表示エラー: {e}")
            await ctx.send("予定の取得中にエラーが発生しました。")
    
    @tasks.loop(minutes=5)  # 5分ごとに実行
    async def meeting_reminder(self):
        """会議15分前リマインド"""
        try:
            # 15分後に開始予定のイベントを取得
            upcoming_events = await google_calendar_service.get_upcoming_events(minutes=15)
            
            if not upcoming_events:
                return
            
            # 各予定について参加者にリマインドを送信
            for event in upcoming_events:
                try:
                    await self._send_meeting_reminder(event)
                except Exception as e:
                    logger.error(f"会議リマインド送信エラー: {e}")
            
        except Exception as e:
            logger.error(f"会議リマインド処理エラー: {e}")
    
    @tasks.loop(time=time(8, 0))  # 毎朝8:00に実行
    async def daily_schedule_share(self):
        """定期スケジュール共有"""
        try:
            # 今日の予定を取得
            events = await google_calendar_service.get_today_events()
            
            # メインチャンネルに今日の予定を投稿
            # 注意: 実際の実装では設定でチャンネルIDを指定する必要があります
            channel_id = None  # 設定から取得する予定
            
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    embed = self._create_daily_schedule_embed(events)
                    await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"定期スケジュール共有エラー: {e}")
    
    async def _send_meeting_reminder(self, event):
        """会議リマインドを送信"""
        # 参加者にDMでリマインドを送信
        # 実際の実装では、カレンダーの参加者とDiscordユーザーの紐づけが必要
        pass
    
    def _create_daily_schedule_embed(self, events):
        """日次スケジュール用のEmbedを作成"""
        embed = discord.Embed(
            title=f"📅 今日の予定 ({date.today().strftime('%Y-%m-%d')})",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        if not events:
            embed.description = "今日の予定はありません"
        else:
            schedule_text = []
            for event in events[:10]:  # 最大10件
                if event['all_day']:
                    time_str = "終日"
                else:
                    start_time = event['start'].strftime("%H:%M")
                    end_time = event['end'].strftime("%H:%M")
                    time_str = f"{start_time}-{end_time}"
                
                location_str = f" @{event['location']}" if event['location'] else ""
                schedule_text.append(f"🕐 **{time_str}** {event['summary']}{location_str}")
            
            embed.description = '\n'.join(schedule_text)
            
            if len(events) > 10:
                embed.add_field(
                    name="その他",
                    value=f"他 {len(events) - 10} 件の予定があります",
                    inline=False
                )
        
        embed.set_footer(text="企業用Discord Bot - 日次スケジュール")
        return embed
    
    @meeting_reminder.before_loop
    async def before_meeting_reminder(self):
        """会議リマインドタスク開始前の処理"""
        await self.bot.wait_until_ready()
    
    @daily_schedule_share.before_loop
    async def before_daily_schedule_share(self):
        """日次スケジュール共有タスク開始前の処理"""
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        """Cog終了時の処理"""
        if hasattr(self, 'meeting_reminder'):
            self.meeting_reminder.cancel()
        if hasattr(self, 'daily_schedule_share'):
            self.daily_schedule_share.cancel()

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(CalendarCog(bot)) 