"""
Task management commands - Clean TDD implementation
"""
import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict, Any, Optional, List
import re

from src.core.database import get_database_manager
from src.core.logging import get_logger, log_command_execution
from src.core.error_handling import get_error_handler, UserError, SystemError, handle_errors
from src.bot.core import require_registration

logger = get_logger(__name__)


class TaskManagerCog(commands.Cog):
    """タスク管理機能を提供するCog - Clean TDD implementation"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_manager = get_database_manager()
        self.error_handler = get_error_handler()
    
    @commands.command(name='タスク追加', aliases=['task_add', 'add_task'])
    @require_registration
    @handle_errors()
    async def add_task(self, ctx: commands.Context, *, task_info: str) -> None:
        """新しいタスクを追加する
        
        使用例:
        !タスク追加 プロジェクトAの資料作成
        !タスク追加 会議の準備 priority:高 due:2024-02-15
        """
        try:
            # タスク情報を解析
            task_data = self._parse_task_info(task_info)
            
            # タスクを作成
            task_id = await self.db_manager.create_task(
                user_id=ctx.author.id,
                title=task_data['title'],
                description=task_data.get('description'),
                priority=task_data.get('priority', 'medium'),
                due_date=task_data.get('due_date')
            )
            
            # 成功メッセージ
            embed = discord.Embed(
                title="✅ タスクが追加されました",
                description=f"**{task_data['title']}**",
                color=discord.Color.green()
            )
            embed.add_field(name="ID", value=str(task_id), inline=True)
            embed.add_field(name="優先度", value=task_data.get('priority', 'medium'), inline=True)
            
            if task_data.get('due_date'):
                embed.add_field(name="期限", value=task_data['due_date'].strftime('%Y-%m-%d'), inline=True)
            
            await ctx.send(embed=embed)
            
            log_command_execution(
                logger, "add_task", ctx.author.id, ctx.guild.id if ctx.guild else None, True,
                task_id=task_id, title=task_data['title']
            )
            
        except Exception as e:
            error_msg = f"タスクの追加中にエラーが発生しました: {str(e)}"
            await ctx.send(error_msg)
            raise SystemError(f"Failed to add task: {e}") from e
    
    @commands.command(name='タスク一覧', aliases=['task_list', 'tasks'])
    @require_registration
    @handle_errors()
    async def list_tasks(self, ctx: commands.Context, status: Optional[str] = None) -> None:
        """タスク一覧を表示する
        
        使用例:
        !タスク一覧
        !タスク一覧 pending
        !タスク一覧 completed
        """
        try:
            # タスクを取得
            if status:
                tasks = await self.db_manager.list_tasks_by_status(ctx.author.id, status)
            else:
                tasks = await self.db_manager.list_tasks(ctx.author.id)
            
            if not tasks:
                status_msg = f"（{status}）" if status else ""
                await ctx.send(f"タスク{status_msg}がありません。")
                return
            
            # 埋め込みメッセージを作成
            embed = discord.Embed(
                title=f"📋 タスク一覧 {f'({status})' if status else ''}",
                color=discord.Color.blue()
            )
            
            # タスクをステータス別にグループ化
            status_groups = {}
            for task in tasks:
                task_status = task['status']
                if task_status not in status_groups:
                    status_groups[task_status] = []
                status_groups[task_status].append(task)
            
            # ステータス別に表示
            status_emojis = {
                'pending': '⏳',
                'in_progress': '🔄',
                'completed': '✅',
                'cancelled': '❌'
            }
            
            for task_status, task_list in status_groups.items():
                emoji = status_emojis.get(task_status, '📌')
                task_texts = []
                
                for task in task_list[:10]:  # 最大10個まで表示
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '⚪')
                    task_text = f"{priority_emoji} **{task['id']}**: {task['title']}"
                    
                    if task['due_date']:
                        due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                        task_text += f" (期限: {due_date.strftime('%m/%d')})"
                    
                    task_texts.append(task_text)
                
                if len(task_list) > 10:
                    task_texts.append(f"... 他 {len(task_list) - 10} 件")
                
                embed.add_field(
                    name=f"{emoji} {task_status} ({len(task_list)}件)",
                    value="\n".join(task_texts) if task_texts else "なし",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
            log_command_execution(
                logger, "list_tasks", ctx.author.id, ctx.guild.id if ctx.guild else None, True,
                task_count=len(tasks), status_filter=status
            )
            
        except Exception as e:
            error_msg = f"タスク一覧の取得中にエラーが発生しました: {str(e)}"
            await ctx.send(error_msg)
            raise SystemError(f"Failed to list tasks: {e}") from e
    
    @commands.command(name='タスク完了', aliases=['task_done', 'done'])
    @require_registration
    @handle_errors()
    async def complete_task(self, ctx: commands.Context, task_id: int) -> None:
        """タスクを完了にする
        
        使用例:
        !タスク完了 123
        """
        try:
            # タスクの存在確認
            task = await self.db_manager.get_task(task_id)
            if not task:
                await ctx.send(f"ID {task_id} のタスクが見つかりません。")
                return
            
            # ユーザーの所有確認
            if task['user_id'] != ctx.author.id:
                await ctx.send("他のユーザーのタスクは操作できません。")
                return
            
            # タスクを完了
            success = await self.db_manager.complete_task(task_id)
            if success:
                embed = discord.Embed(
                    title="✅ タスク完了",
                    description=f"**{task['title']}** を完了しました！",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
                log_command_execution(
                    logger, "complete_task", ctx.author.id, ctx.guild.id if ctx.guild else None, True,
                    task_id=task_id, title=task['title']
                )
            else:
                await ctx.send("タスクの完了処理に失敗しました。")
            
        except Exception as e:
            error_msg = f"タスクの完了処理中にエラーが発生しました: {str(e)}"
            await ctx.send(error_msg)
            raise SystemError(f"Failed to complete task: {e}") from e
    
    @commands.command(name='タスク削除', aliases=['task_delete', 'delete_task'])
    @require_registration
    @handle_errors()
    async def delete_task(self, ctx: commands.Context, task_id: int) -> None:
        """タスクを削除する
        
        使用例:
        !タスク削除 123
        """
        try:
            # タスクの存在確認
            task = await self.db_manager.get_task(task_id)
            if not task:
                await ctx.send(f"ID {task_id} のタスクが見つかりません。")
                return
            
            # ユーザーの所有確認
            if task['user_id'] != ctx.author.id:
                await ctx.send("他のユーザーのタスクは操作できません。")
                return
            
            # タスクを削除
            success = await self.db_manager.delete_task(task_id)
            if success:
                embed = discord.Embed(
                    title="🗑️ タスク削除",
                    description=f"**{task['title']}** を削除しました。",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                
                log_command_execution(
                    logger, "delete_task", ctx.author.id, ctx.guild.id if ctx.guild else None, True,
                    task_id=task_id, title=task['title']
                )
            else:
                await ctx.send("タスクの削除に失敗しました。")
            
        except Exception as e:
            error_msg = f"タスクの削除中にエラーが発生しました: {str(e)}"
            await ctx.send(error_msg)
            raise SystemError(f"Failed to delete task: {e}") from e
    
    @commands.command(name='タスク進行中', aliases=['task_progress', 'progress'])
    @require_registration
    @handle_errors()
    async def progress_task(self, ctx: commands.Context, task_id: int) -> None:
        """タスクを進行中にする
        
        使用例:
        !タスク進行中 123
        """
        try:
            # タスクの存在確認
            task = await self.db_manager.get_task(task_id)
            if not task:
                await ctx.send(f"ID {task_id} のタスクが見つかりません。")
                return
            
            # ユーザーの所有確認
            if task['user_id'] != ctx.author.id:
                await ctx.send("他のユーザーのタスクは操作できません。")
                return
            
            # タスクを進行中に変更
            success = await self.db_manager.update_task(task_id, status='in_progress')
            if success:
                embed = discord.Embed(
                    title="🔄 タスク進行中",
                    description=f"**{task['title']}** を進行中に変更しました。",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                
                log_command_execution(
                    logger, "progress_task", ctx.author.id, ctx.guild.id if ctx.guild else None, True,
                    task_id=task_id, title=task['title']
                )
            else:
                await ctx.send("タスクの更新に失敗しました。")
            
        except Exception as e:
            error_msg = f"タスクの更新中にエラーが発生しました: {str(e)}"
            await ctx.send(error_msg)
            raise SystemError(f"Failed to update task: {e}") from e
    
    @commands.command(name='タスクヘルプ', aliases=['task_help'])
    async def task_help(self, ctx: commands.Context) -> None:
        """タスク管理コマンドのヘルプを表示する"""
        embed = discord.Embed(
            title="📋 タスク管理ヘルプ",
            description="利用可能なタスク管理コマンド",
            color=discord.Color.blue()
        )
        
        commands_info = [
            ("!タスク追加 <タスク名>", "新しいタスクを追加\n例: `!タスク追加 資料作成 priority:高 due:2024-12-31`"),
            ("!タスク一覧 [ステータス]", "タスク一覧を表示\n例: `!タスク一覧` `!タスク一覧 pending`"),
            ("!タスク完了 <ID>", "タスクを完了にする\n例: `!タスク完了 123`"),
            ("!タスク削除 <ID>", "タスクを削除する\n例: `!タスク削除 123`"),
            ("!タスク進行中 <ID>", "タスクを進行中にする\n例: `!タスク進行中 123`"),
            ("!タスクヘルプ", "このヘルプを表示")
        ]
        
        for command, description in commands_info:
            embed.add_field(name=command, value=description, inline=False)
        
        embed.add_field(
            name="📝 タスク追加のオプション",
            value="• `priority:高/中/低` - 優先度設定\n• `due:YYYY-MM-DD` - 期限設定",
            inline=False
        )
        
        embed.add_field(
            name="📊 タスクステータス",
            value="• `pending` - 未着手\n• `in_progress` - 進行中\n• `completed` - 完了\n• `cancelled` - 中断",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    def _parse_task_info(self, task_info: str) -> Dict[str, Any]:
        """タスク情報を解析する
        
        Args:
            task_info: タスク情報文字列
            
        Returns:
            解析されたタスクデータ
        """
        task_data = {
            'title': '',
            'description': None,
            'priority': 'medium',
            'due_date': None
        }
        
        # オプションを抽出
        priority_match = re.search(r'priority:([高中低high|medium|low]+)', task_info, re.IGNORECASE)
        if priority_match:
            priority_text = priority_match.group(1).lower()
            priority_mapping = {
                '高': 'high', 'high': 'high',
                '中': 'medium', 'medium': 'medium', 
                '低': 'low', 'low': 'low'
            }
            task_data['priority'] = priority_mapping.get(priority_text, 'medium')
            task_info = re.sub(r'priority:[高中低high|medium|low]+', '', task_info, flags=re.IGNORECASE)
        
        # 期限を抽出
        due_match = re.search(r'due:(\d{4}-\d{2}-\d{2})', task_info, re.IGNORECASE)
        if due_match:
            try:
                task_data['due_date'] = datetime.strptime(due_match.group(1), '%Y-%m-%d')
            except ValueError:
                pass  # 無効な日付の場合は無視
            task_info = re.sub(r'due:\d{4}-\d{2}-\d{2}', '', task_info, flags=re.IGNORECASE)
        
        # タイトルを設定（残りの文字列）
        task_data['title'] = task_info.strip()
        
        if not task_data['title']:
            raise UserError("タスクのタイトルが指定されていません。", "タスクのタイトルを入力してください。")
        
        return task_data


async def setup(bot: commands.Bot) -> None:
    """Cogをbotに追加"""
    await bot.add_cog(TaskManagerCog(bot))