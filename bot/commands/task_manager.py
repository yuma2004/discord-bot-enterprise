import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict, Any, Optional, List
from core.logging import LoggerManager

# データベースリポジトリの動的インポート
import os

database_url = os.getenv('DATABASE_URL', '')
if database_url and 'postgres' in database_url:
    try:
        from database_postgres import user_repo, task_repo
    except ImportError:
        from database import user_repo, task_repo
else:
    from database import user_repo, task_repo

logger = LoggerManager.get_logger(__name__)

class TaskManagerCog(commands.Cog):
    """タスク管理機能を提供するCog"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.command(name='タスク追加', aliases=['task_add', 'add_task'])
    async def add_task(self, ctx: commands.Context[commands.Bot], *, task_info: str) -> None:
        """新しいタスクを追加する
        
        使用例:
        !タスク追加 プロジェクトAの資料作成
        !タスク追加 会議の準備 priority:高 due:2024-02-15
        """
        try:
            # ユーザー情報を取得または作成
            if user_repo is None:
                await ctx.send("データベースに接続できません。")
                return
                
            user = user_repo.get_or_create_user(
                str(ctx.author.id),
                ctx.author.name,
                ctx.author.display_name
            )
            
            # タスク情報を解析
            task_data = self._parse_task_info(task_info)
            
            # タスクを作成
            if task_repo is None:
                await ctx.send("タスクリポジトリに接続できません。")
                return
                
            task_id = task_repo.create_task(
                user['id'],
                task_data['title'],
                task_data.get('description', ''),
                task_data.get('priority', '中'),
                task_data.get('due_date', '')
            )
            
            # 成功メッセージを送信
            embed = discord.Embed(
                title="✅ タスク追加完了",
                description=f"タスクID: {task_id}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="タスク名", value=task_data['title'], inline=False)
            if task_data.get('description'):
                embed.add_field(name="詳細", value=task_data['description'], inline=False)
            embed.add_field(name="優先度", value=task_data.get('priority', '中'), inline=True)
            if task_data.get('due_date'):
                embed.add_field(name="期限", value=task_data['due_date'], inline=True)
            embed.set_footer(text=f"作成者: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク追加エラー: {e}")
            await ctx.send("タスクの追加中にエラーが発生しました。")
    
    @commands.command(name='タスク一覧', aliases=['task_list', 'tasks'])
    async def list_tasks(self, ctx: commands.Context[commands.Bot], status: Optional[str] = None) -> None:
        """タスク一覧を表示する
        
        引数:
        status: 表示したいタスクのステータス (未着手/進行中/完了/中断)
        """
        try:
            if user_repo is None:
                await ctx.send("データベースに接続できません。")
                return
                
            user = user_repo.get_user_by_discord_id(str(ctx.author.id))
            if not user:
                await ctx.send("まだタスクが登録されていません。")
                return
            
            if task_repo is None:
                await ctx.send("タスクリポジトリに接続できません。")
                return
                  # タスク一覧を取得
            tasks = task_repo.get_user_tasks(user['id'], status or '')
            
            if not tasks:
                status_text = f" ({status})" if status else ""
                await ctx.send(f"タスク{status_text}が見つかりませんでした。")
                return
            
            # タスク一覧を表示
            title = f"📋 タスク一覧 ({status})" if status else "📋 タスク一覧"
            embed = discord.Embed(
                title=title,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # ステータス別にタスクを分類
            status_groups: Dict[str, List[Dict[str, Any]]] = {}
            for task in tasks:
                task_status = task['status']
                if task_status not in status_groups:
                    status_groups[task_status] = []
                status_groups[task_status].append(task)
            
            # 各ステータスごとにフィールドを作成
            for task_status, task_list in status_groups.items():
                show_more = False
                if len(task_list) > 5:  # 5個以上の場合は省略
                    task_list = task_list[:5]
                    show_more = True
                
                status_emoji = {
                    '未着手': '⏳',
                    '進行中': '🔄', 
                    '完了': '✅',
                    '中断': '⏸️'
                }.get(task_status, '📝')
                
                task_texts: List[str] = []
                for task in task_list:
                    priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(task['priority'], '⚪')
                    due_text = f" (期限: {task['due_date']})" if task['due_date'] else ""
                    task_texts.append(f"{priority_emoji} [ID:{task['id']}] {task['title']}{due_text}")
                
                if show_more:
                    task_texts.append("... (他にもあります)")
                
                embed.add_field(
                    name=f"{status_emoji} {task_status} ({len(status_groups[task_status])}件)",
                    value='\n'.join(task_texts) if task_texts else "なし",
                    inline=False
                )
            
            embed.set_footer(text=f"ユーザー: {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク一覧表示エラー: {e}")
            await ctx.send("タスク一覧の表示中にエラーが発生しました。")
    
    @commands.command(name='タスク完了', aliases=['task_done', 'done'])
    async def complete_task(self, ctx: commands.Context[commands.Bot], task_id: int) -> None:
        """タスクを完了にする
        
        引数:
        task_id: 完了するタスクのID
        """
        try:
            if task_repo is None:
                await ctx.send("タスクリポジトリに接続できません。")
                return
                
            success = task_repo.update_task_status(task_id, '完了')
            
            if success:
                embed = discord.Embed(
                    title="🎉 タスク完了",
                    description=f"タスクID {task_id} を完了にしました",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=f"タスクID {task_id} が見つからないか、更新に失敗しました",
                    color=discord.Color.red()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク完了エラー: {e}")
            await ctx.send("タスクの完了処理中にエラーが発生しました。")
    
    @commands.command(name='タスク削除', aliases=['task_delete', 'delete_task'])
    async def delete_task(self, ctx: commands.Context[commands.Bot], task_id: int) -> None:
        """タスクを削除する
        
        引数:
        task_id: 削除するタスクのID
        """
        try:
            if task_repo is None:
                await ctx.send("タスクリポジトリに接続できません。")
                return
                
            success = task_repo.delete_task(task_id)
            
            if success:
                embed = discord.Embed(
                    title="🗑️ タスク削除",
                    description=f"タスクID {task_id} を削除しました",
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=f"タスクID {task_id} が見つからないか、削除に失敗しました",
                    color=discord.Color.red()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク削除エラー: {e}")
            await ctx.send("タスクの削除処理中にエラーが発生しました。")
    
    @commands.command(name='タスク進行中', aliases=['task_progress', 'progress'])
    async def progress_task(self, ctx: commands.Context[commands.Bot], task_id: int) -> None:
        """タスクを進行中にする
        
        引数:
        task_id: 進行中にするタスクのID
        """
        try:
            if task_repo is None:
                await ctx.send("タスクリポジトリに接続できません。")
                return
                
            success = task_repo.update_task_status(task_id, '進行中')
            
            if success:
                embed = discord.Embed(
                    title="🔄 タスク更新",
                    description=f"タスクID {task_id} を進行中にしました",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=f"タスクID {task_id} が見つからないか、更新に失敗しました",
                    color=discord.Color.red()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"タスク進行中更新エラー: {e}")
            await ctx.send("タスクの更新処理中にエラーが発生しました。")
    
    @commands.command(name='タスクヘルプ', aliases=['task_help'])
    async def task_help(self, ctx: commands.Context[commands.Bot]) -> None:
        """タスク管理機能のヘルプを表示"""
        embed = discord.Embed(
            title="📋 タスク管理機能ヘルプ",
            description="利用可能なタスク管理コマンド一覧",
            color=discord.Color.blue()
        )
        
        commands_info = [
            ("!タスク追加 [タスク名]", "新しいタスクを追加"),
            ("!タスク一覧 [ステータス]", "タスク一覧を表示"),
            ("!タスク完了 [ID]", "タスクを完了にする"),
            ("!タスク削除 [ID]", "タスクを削除する"),
            ("!タスク進行中 [ID]", "タスクを進行中にする"),
        ]
        
        for command, description in commands_info:
            embed.add_field(
                name=command,
                value=description,
                inline=False
            )
        
        embed.add_field(
            name="タスク追加の詳細オプション",
            value="```\n!タスク追加 会議の準備 priority:高 due:2024-02-15\n\n"
                  "priority: 高/中/低\n"
                  "due: YYYY-MM-DD形式\n```",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    def _parse_task_info(self, task_info: str) -> Dict[str, Any]:
        """タスク情報を解析する"""
        task_data: Dict[str, Any] = {
            'title': '',
            'description': '',
            'priority': '中',
            'due_date': None
        }
        
        # オプションを抽出
        parts = task_info.split()
        title_parts: List[str] = []
        
        for part in parts:
            if 'priority:' in part:
                priority = part.split('priority:')[1]
                if priority in ['高', '中', '低']:
                    task_data['priority'] = priority
            elif 'due:' in part:
                due_date = part.split('due:')[1]
                try:
                    # 日付形式の確認
                    datetime.strptime(due_date, '%Y-%m-%d')
                    task_data['due_date'] = due_date
                except ValueError:
                    pass  # 無効な日付は無視
            else:
                title_parts.append(part)
        
        task_data['title'] = ' '.join(title_parts)
        
        return task_data

async def setup(bot: commands.Bot) -> None:
    """Cogをbotに追加"""
    await bot.add_cog(TaskManagerCog(bot))
