import discord
from discord.ext import commands
import logging
from bot.utils.datetime_utils import now_jst

logger = logging.getLogger(__name__)

class HelpCog(commands.Cog):
    """充実したヘルプ機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='ヘルプ', aliases=['help', 'h'])
    async def show_help(self, ctx, category: str = None):
        """コマンドヘルプを表示"""
        if category is None:
            await self._show_main_help(ctx)
        else:
            await self._show_category_help(ctx, category)
    
    async def _show_main_help(self, ctx):
        """メインヘルプを表示"""
        embed = discord.Embed(
            title="📚 企業用Discord Bot - ヘルプ",
            description="利用可能な機能一覧",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        # 基本情報
        embed.add_field(
            name="🎯 使い方",
            value="コマンドの前に `!` を付けて実行してください\n例: `!日報 今日の作業内容`",
            inline=False
        )
        
        # 機能カテゴリー
        categories = [
            {
                "name": "📝 日報機能",
                "value": "`!ヘルプ 日報` で詳細表示",
                "commands": "!日報, !日報確認, !日報テンプレート"
            },
            {
                "name": "📋 タスク管理",
                "value": "`!ヘルプ タスク` で詳細表示",
                "commands": "!タスク追加, !タスク一覧, !タスク完了"
            },
            {
                "name": "🕐 出退勤管理",
                "value": "`!ヘルプ 出勤` で詳細表示", 
                "commands": "!出勤, !勤怠確認, !月次レポート"
            },
            {
                "name": "📅 カレンダー連携",
                "value": "`!ヘルプ カレンダー` で詳細表示",
                "commands": "!今日の予定, !週間予定, !次の予定"
            },
            {
                "name": "🔧 管理機能",
                "value": "`!ヘルプ 管理` で詳細表示（管理者のみ）",
                "commands": "!admin stats, !admin users"
            }
        ]
        
        for category in categories:
            embed.add_field(
                name=category["name"],
                value=f"{category['value']}\n主なコマンド: {category['commands']}",
                inline=False
            )
        
        # フッター情報
        embed.add_field(
            name="💡 Tips",
            value="• 大部分のコマンドは日本語に対応しています\n"
                  "• ボタン操作も利用できます（出退勤機能）\n"
                  "• 困った時は `!サポート` でお問い合わせ",
            inline=False
        )
        
        embed.set_footer(text="詳細は各カテゴリーのヘルプをご確認ください")
        
        await ctx.send(embed=embed)
    
    async def _show_category_help(self, ctx, category: str):
        """カテゴリー別ヘルプを表示"""
        category_lower = category.lower()
        
        if category_lower in ['日報', 'daily', 'report']:
            await self._show_daily_report_help(ctx)
        elif category_lower in ['タスク', 'task', 'todo']:
            await self._show_task_help(ctx)
        elif category_lower in ['出勤', '出退勤', 'attendance', 'work']:
            await self._show_attendance_help(ctx)
        elif category_lower in ['カレンダー', 'calendar', '予定']:
            await self._show_calendar_help(ctx)
        elif category_lower in ['管理', 'admin', '管理者']:
            await self._show_admin_help(ctx)
        else:
            embed = discord.Embed(
                title="❌ 不明なカテゴリー",
                description=f"'{category}' というカテゴリーは存在しません。\n`!ヘルプ` で利用可能なカテゴリーを確認してください。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    async def _show_daily_report_help(self, ctx):
        """日報機能のヘルプ"""
        embed = discord.Embed(
            title="📝 日報機能ヘルプ",
            description="日報の提出・確認・管理機能",
            color=discord.Color.green(),
            timestamp=now_jst()
        )
        
        commands = [
            {
                "name": "!日報 [内容]",
                "value": "今日の日報を提出します\n例: `!日報 プロジェクトAの設計書を作成しました`"
            },
            {
                "name": "!日報確認 [日付]",
                "value": "指定日の日報を確認します（日付省略時は今日）\n例: `!日報確認 2024-01-15`"
            },
            {
                "name": "!日報テンプレート",
                "value": "日報のテンプレートを表示します"
            },
            {
                "name": "!日報履歴",
                "value": "過去の日報履歴を表示します"
            }
        ]
        
        for cmd in commands:
            embed.add_field(
                name=cmd["name"],
                value=cmd["value"],
                inline=False
            )
        
        # 自動リマインド機能
        embed.add_field(
            name="🔔 自動リマインド",
            value="毎日17:00に未提出者へのリマインドDMが送信されます",
            inline=False
        )
        
        # 日報のコツ
        embed.add_field(
            name="📝 日報記入のコツ",
            value="• 具体的な作業内容を記載\n"
                  "• 課題や困っている点も共有\n"
                  "• 明日の予定も書くと良いです",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _show_task_help(self, ctx):
        """タスク管理機能のヘルプ"""
        embed = discord.Embed(
            title="📋 タスク管理機能ヘルプ",
            description="個人タスクの追加・管理・追跡機能",
            color=discord.Color.orange(),
            timestamp=now_jst()
        )
        
        commands = [
            {
                "name": "!タスク追加 [タイトル] [期限] [優先度]",
                "value": "新しいタスクを追加します\n例: `!タスク追加 レポート作成 2024-01-20 高`"
            },
            {
                "name": "!タスク一覧",
                "value": "自分の未完了タスク一覧を表示します"
            },
            {
                "name": "!タスク完了 [タスクID]",
                "value": "指定したタスクを完了にします\n例: `!タスク完了 3`"
            },
            {
                "name": "!タスク削除 [タスクID]",
                "value": "指定したタスクを削除します\n例: `!タスク削除 5`"
            },
            {
                "name": "!タスク編集 [タスクID] [新しいタイトル]",
                "value": "タスクの内容を編集します"
            }
        ]
        
        for cmd in commands:
            embed.add_field(
                name=cmd["name"],
                value=cmd["value"],
                inline=False
            )
        
        # 優先度について
        embed.add_field(
            name="🎯 優先度設定",
            value="**高** 🔴 - 緊急度の高いタスク\n"
                  "**中** 🟡 - 通常のタスク\n"
                  "**低** 🟢 - 後回しでも良いタスク",
            inline=False
        )
        
        # リマインド機能
        embed.add_field(
            name="⏰ 自動リマインド",
            value="期限1日前に自動でDMリマインドが送信されます",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _show_attendance_help(self, ctx):
        """出退勤管理機能のヘルプ"""
        embed = discord.Embed(
            title="🕐 出退勤管理機能ヘルプ",
            description="出勤・退勤・休憩の記録と勤務時間管理",
            color=discord.Color.purple(),
            timestamp=now_jst()
        )
        
        # ボタン操作の説明
        embed.add_field(
            name="🔘 ボタン操作",
            value="`!出勤` コマンドでボタンパネルを表示\n"
                  "• 出勤ボタン - 出勤時刻を記録\n"
                  "• 退勤ボタン - 退勤時刻を記録\n"
                  "• 休憩開始 - 休憩開始時刻を記録\n"
                  "• 休憩終了 - 休憩終了時刻を記録",
            inline=False
        )
        
        commands = [
            {
                "name": "!出勤",
                "value": "出退勤操作パネルを表示します"
            },
            {
                "name": "!勤怠確認 [日付]",
                "value": "指定日の勤怠記録を確認（日付省略時は今日）\n例: `!勤怠確認 2024-01-15`"
            },
            {
                "name": "!在席状況",
                "value": "現在の全員の在席状況を表示します"
            },
            {
                "name": "!月次レポート [月]",
                "value": "指定月の勤怠レポートを表示\n例: `!月次レポート 2024-01`"
            }
        ]
        
        for cmd in commands:
            embed.add_field(
                name=cmd["name"],
                value=cmd["value"],
                inline=False
            )
        
        # 勤務時間の計算説明
        embed.add_field(
            name="⏱️ 勤務時間計算",
            value="• 基本勤務時間: 8時間\n"
                  "• 8時間超過分は残業時間として計算\n"
                  "• 休憩時間は勤務時間から除外",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _show_calendar_help(self, ctx):
        """カレンダー機能のヘルプ"""
        embed = discord.Embed(
            title="📅 カレンダー機能ヘルプ",
            description="Googleカレンダーとの連携機能",
            color=discord.Color.blue(),
            timestamp=now_jst()
        )
        
        commands = [
            {
                "name": "!今日の予定",
                "value": "今日のカレンダー予定を表示します"
            },
            {
                "name": "!週間予定",
                "value": "今週の予定を日別に表示します"
            },
            {
                "name": "!次の予定",
                "value": "次に控えている予定を表示します"
            }
        ]
        
        for cmd in commands:
            embed.add_field(
                name=cmd["name"],
                value=cmd["value"],
                inline=False
            )
        
        # 自動機能
        embed.add_field(
            name="🔔 自動機能",
            value="• 毎朝8:00に今日の予定をチャンネル投稿\n"
                  "• 会議15分前にリマインドDM送信",
            inline=False
        )
        
        # 設定必要
        embed.add_field(
            name="⚙️ 設定について",
            value="Googleカレンダー連携には管理者による設定が必要です。\n"
                  "詳細は管理者にお問い合わせください。",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _show_admin_help(self, ctx):
        """管理機能のヘルプ"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ 権限不足",
                description="管理者機能のヘルプは管理者のみ閲覧できます。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔧 管理機能ヘルプ",
            description="Bot管理・統計・設定機能（管理者専用）",
            color=discord.Color.gold(),
            timestamp=now_jst()
        )
        
        commands = [
            {
                "name": "!admin stats",
                "value": "システム全体の統計情報を表示"
            },
            {
                "name": "!admin users",
                "value": "登録ユーザー一覧を表示"
            },
            {
                "name": "!admin report [日数]",
                "value": "日報提出率レポートを表示"
            },
            {
                "name": "!admin tasks",
                "value": "全タスク統計を表示"
            },
            {
                "name": "!admin attendance [日数]",
                "value": "出勤統計を表示"
            },
            {
                "name": "!admin backup",
                "value": "データベースバックアップを作成"
            },
            {
                "name": "!admin settings",
                "value": "現在のBot設定を表示"
            }
        ]
        
        for cmd in commands:
            embed.add_field(
                name=cmd["name"],
                value=cmd["value"],
                inline=False
            )
        
        # テスト機能
        embed.add_field(
            name="🧪 テスト機能",
            value="`!リマインドテスト` - リマインド機能のテスト",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='サポート', aliases=['support', 'contact'])
    async def show_support(self, ctx):
        """サポート情報を表示"""
        embed = discord.Embed(
            title="🆘 サポート・お問い合わせ",
            description="Botの使用方法やトラブルについて",
            color=discord.Color.red(),
            timestamp=now_jst()
        )
        
        embed.add_field(
            name="📚 まずはヘルプを確認",
            value="`!ヘルプ` で基本的な使い方を確認してください",
            inline=False
        )
        
        embed.add_field(
            name="🔧 よくある問題",
            value="• コマンドが動かない → `!` を付けているか確認\n"
                  "• 日本語コマンドが使える\n"
                  "• 権限エラー → 管理者にご相談",
            inline=False
        )
        
        embed.add_field(
            name="📞 お問い合わせ",
            value="問題が解決しない場合は、管理者にお問い合わせください。\n"
                  "エラーメッセージがあれば一緒にお伝えください。",
            inline=False
        )
        
        embed.add_field(
            name="🔄 Bot再起動",
            value="重大な問題が発生した場合、管理者がBot再起動を行う場合があります。",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='バージョン', aliases=['version', 'v'])
    async def show_version(self, ctx):
        """Botバージョン情報を表示"""
        embed = discord.Embed(
            title="🤖 企業用Discord Bot",
            description="バージョン情報・機能一覧",
            color=discord.Color.green(),
            timestamp=now_jst()
        )
        
        embed.add_field(
            name="📦 バージョン",
            value="v1.0.0 (2024年版)",
            inline=True
        )
        
        embed.add_field(
            name="🏢 対象",
            value="企業・チーム利用",
            inline=True
        )
        
        embed.add_field(
            name="🌐 言語",
            value="日本語対応",
            inline=True
        )
        
        # 搭載機能
        features = [
            "📝 日報管理",
            "📋 タスク管理", 
            "🕐 出退勤管理",
            "📅 カレンダー連携",
            "🔔 自動リマインド",
            "📊 統計・レポート",
            "🔧 管理者機能"
        ]
        
        embed.add_field(
            name="✨ 搭載機能",
            value=" • ".join(features),
            inline=False
        )
        
        embed.add_field(
            name="🔗 技術スタック",
            value="Python 3.8+, discord.py, SQLite, Google Calendar API",
            inline=False
        )
        
        embed.set_footer(text="開発: AI Assistant | 運用: 社内IT部門")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(HelpCog(bot)) 