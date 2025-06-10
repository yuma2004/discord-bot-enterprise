import discord
from discord.ext import commands
from datetime import datetime, date
import logging
import os
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import user_repo, daily_report_repo
else:
    from database import user_repo, daily_report_repo

logger = logging.getLogger(__name__)

class DailyReportCog(commands.Cog):
    """日報機能を提供するCog"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='日報', aliases=['daily_report', 'nippo'])
    async def submit_daily_report(self, ctx, *, content: str = None):
        """日報を提出する
        
        使用例:
        !日報 今日の作業: プロジェクトA進捗確認\n明日の予定: プロジェクトBのレビュー
        """
        if not content:
            await self._show_daily_report_template(ctx)
            return
        
        # ユーザー情報を取得または作成
        user = user_repo.get_or_create_user(
            str(ctx.author.id),
            ctx.author.name,
            ctx.author.display_name
        )
        
        # 今日の日付を取得
        today = date.today().isoformat()
        
        # 日報内容を解析
        report_data = self._parse_report_content(content)
        
        try:
            # 日報を保存
            daily_report_repo.create_daily_report(
                user['id'],
                today,
                report_data['today_tasks'],
                report_data.get('tomorrow_tasks', ''),
                report_data.get('obstacles', ''),
                report_data.get('comments', '')
            )
            
            # 成功メッセージを送信
            embed = discord.Embed(
                title="📝 日報提出完了",
                description="本日の日報を受け付けました",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="今日の作業",
                value=report_data['today_tasks'][:1000] + ('...' if len(report_data['today_tasks']) > 1000 else ''),
                inline=False
            )
            if report_data.get('tomorrow_tasks'):
                embed.add_field(
                    name="明日の予定",
                    value=report_data['tomorrow_tasks'][:1000] + ('...' if len(report_data['tomorrow_tasks']) > 1000 else ''),
                    inline=False
                )
            embed.set_footer(text=f"提出者: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"日報保存エラー: {e}")
            await ctx.send("日報の保存中にエラーが発生しました。しばらく後にもう一度お試しください。")
    
    @commands.command(name='日報確認', aliases=['show_report'])
    async def show_daily_report(self, ctx, target_date: str = None):
        """自分の日報を確認する
        
        引数:
        target_date: 確認したい日付 (YYYY-MM-DD形式)。省略時は今日
        """
        user = user_repo.get_user_by_discord_id(str(ctx.author.id))
        if not user:
            await ctx.send("まだ日報を提出したことがありません。")
            return
        
        # 日付を設定
        if target_date is None:
            target_date = date.today().isoformat()
        else:
            try:
                # 日付形式の確認
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                await ctx.send("日付の形式が正しくありません。YYYY-MM-DD形式で入力してください。")
                return
        
        # 日報を取得
        report = daily_report_repo.get_daily_report(user['id'], target_date)
        
        if not report:
            await ctx.send(f"{target_date} の日報は見つかりませんでした。")
            return
        
        # 日報を表示
        embed = discord.Embed(
            title=f"📊 日報 - {target_date}",
            color=discord.Color.blue(),
            timestamp=datetime.fromisoformat(report['submitted_at'])
        )
        embed.add_field(
            name="今日の作業",
            value=report['today_tasks'] or "記載なし",
            inline=False
        )
        if report['tomorrow_tasks']:
            embed.add_field(
                name="明日の予定",
                value=report['tomorrow_tasks'],
                inline=False
            )
        if report['obstacles']:
            embed.add_field(
                name="課題・障害",
                value=report['obstacles'],
                inline=False
            )
        if report['comments']:
            embed.add_field(
                name="その他・備考",
                value=report['comments'],
                inline=False
            )
        embed.set_footer(text=f"提出者: {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='日報テンプレート', aliases=['nippo_template'])
    async def daily_report_template(self, ctx):
        """日報のテンプレートを表示する（DMで送信）"""
        await self._show_daily_report_template(ctx)
    
    async def _show_daily_report_template(self, ctx):
        """日報テンプレートを表示（DMで送信）"""
        embed = discord.Embed(
            title="📝 日報テンプレート",
            description="以下のテンプレートを参考に日報を作成してください",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        template = """```
今日の作業:
・プロジェクトAの進捗確認
・会議の準備と資料作成
・バグ修正 (Issue #123)

明日の予定:
・プロジェクトBのレビュー
・新機能の仕様検討

課題・障害:
・特になし

その他・備考:
・来週の予定について確認が必要
```"""
        
        embed.add_field(
            name="📋 テンプレート例",
            value=template,
            inline=False
        )
        
        embed.add_field(
            name="💡 使用方法",
            value="`!日報 [内容]` または `!nippo [内容]`\n"
                  "・このテンプレートをコピーして使用してください\n"
                  "・各項目は必要に応じて編集してください\n"
                  "・DMから直接でも日報提出できます",
            inline=False
        )
        
        embed.add_field(
            name="🚀 クイック日報",
            value="DMで `!日報 今日の作業内容` と送信すれば\n"
                  "サーバーに戻らずに日報提出できます！",
            inline=False
        )
        
        embed.set_footer(text="💌 テンプレートをDMでお送りしました | DMから直接日報提出可能")
        
        try:
            # DMでテンプレートを送信
            await ctx.author.send(embed=embed)
            
            # 元のチャンネルには簡潔な確認メッセージを送信
            if ctx.guild:  # サーバー内からの呼び出しの場合
                confirm_embed = discord.Embed(
                    title="💌 DMを確認してください",
                    description="日報テンプレートをDMでお送りしました\n**DMから直接日報提出も可能です！**",
                    color=discord.Color.green()
                )
                await ctx.send(embed=confirm_embed, delete_after=10)
        except discord.Forbidden:
            # DMが送信できない場合はチャンネルに送信
            embed.set_footer(text="⚠️ DMが送信できないため、こちらに表示しています")
            await ctx.send(embed=embed)
    
    def _parse_report_content(self, content: str) -> dict:
        """日報内容を解析して構造化データに変換"""
        report_data = {
            'today_tasks': '',
            'tomorrow_tasks': '',
            'obstacles': '',
            'comments': ''
        }
        
        # シンプルな解析：セクションキーワードで分割
        sections = {
            '今日の作業': 'today_tasks',
            '今日': 'today_tasks',
            '明日の予定': 'tomorrow_tasks',
            '明日': 'tomorrow_tasks',
            '課題': 'obstacles',
            '障害': 'obstacles',
            '問題': 'obstacles',
            'その他': 'comments',
            '備考': 'comments',
            'コメント': 'comments'
        }
        
        current_section = 'today_tasks'
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # セクションの検出
            found_section = False
            for keyword, section_key in sections.items():
                if keyword in line:
                    current_section = section_key
                    # キーワード以降の内容があれば追加
                    remaining = line.split(keyword, 1)[-1].strip()
                    if remaining and remaining.startswith(':'):
                        remaining = remaining[1:].strip()
                    if remaining:
                        if report_data[current_section]:
                            report_data[current_section] += '\n' + remaining
                        else:
                            report_data[current_section] = remaining
                    found_section = True
                    break
            
            # セクションキーワードが見つからない場合は現在のセクションに追加
            if not found_section:
                if report_data[current_section]:
                    report_data[current_section] += '\n' + line
                else:
                    report_data[current_section] = line
        
        return report_data

async def setup(bot):
    """Cogをbotに追加"""
    await bot.add_cog(DailyReportCog(bot)) 