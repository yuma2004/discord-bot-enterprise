import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import json
import os

# Google API関連のインポート
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from config import Config

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    """Googleカレンダー連携サービス"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google API ライブラリが利用できません。calendar機能は無効化されます。")
            return
        
        # 認証情報の初期化
        self._init_credentials()
    
    def _init_credentials(self):
        """認証情報を初期化"""
        try:
            # Service Account認証を使用（簡単なセットアップのため）
            if Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET:
                logger.info("Google API認証を初期化中...")
                # 実際の実装では、OAuth2またはService Accountの設定が必要
                # ここでは基本的な構造のみ実装
                pass
            else:
                logger.warning("Google API認証情報が設定されていません")
        except Exception as e:
            logger.error(f"Google API認証初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """Google Calendar APIが利用可能かチェック"""
        return GOOGLE_API_AVAILABLE and self.service is not None
    
    async def get_today_events(self, calendar_id: str = None) -> List[Dict[str, Any]]:
        """今日の予定を取得"""
        if not self.is_available():
            return []
        
        try:
            calendar_id = calendar_id or Config.GOOGLE_CALENDAR_ID or 'primary'
            
            # 今日の開始時刻と終了時刻を設定
            today = date.today()
            start_time = datetime.combine(today, datetime.min.time()).isoformat() + 'Z'
            end_time = datetime.combine(today, datetime.max.time()).isoformat() + 'Z'
            
            # イベントを取得
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # イベント情報を整形
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                formatted_events.append(formatted_event)
            
            logger.info(f"今日の予定を {len(formatted_events)} 件取得しました")
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API エラー: {e}")
            return []
        except Exception as e:
            logger.error(f"今日の予定取得エラー: {e}")
            return []
    
    async def get_week_events(self, calendar_id: str = None) -> List[Dict[str, Any]]:
        """今週の予定を取得"""
        if not self.is_available():
            return []
        
        try:
            calendar_id = calendar_id or Config.GOOGLE_CALENDAR_ID or 'primary'
            
            # 今週の開始日（月曜日）と終了日（日曜日）を計算
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            start_time = datetime.combine(start_of_week, datetime.min.time()).isoformat() + 'Z'
            end_time = datetime.combine(end_of_week, datetime.max.time()).isoformat() + 'Z'
            
            # イベントを取得
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # イベント情報を整形
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                formatted_events.append(formatted_event)
            
            logger.info(f"今週の予定を {len(formatted_events)} 件取得しました")
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API エラー: {e}")
            return []
        except Exception as e:
            logger.error(f"今週の予定取得エラー: {e}")
            return []
    
    async def get_upcoming_events(self, minutes: int = 15) -> List[Dict[str, Any]]:
        """指定した時間内に開始予定のイベントを取得"""
        if not self.is_available():
            return []
        
        try:
            now = datetime.now()
            upcoming_time = now + timedelta(minutes=minutes)
            
            start_time = now.isoformat() + 'Z'
            end_time = upcoming_time.isoformat() + 'Z'
            
            # イベントを取得
            events_result = self.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID or 'primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # イベント情報を整形
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                formatted_events.append(formatted_event)
            
            return formatted_events
            
        except Exception as e:
            logger.error(f"近日予定取得エラー: {e}")
            return []
    
    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """イベント情報を整形"""
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # 日時の解析
        if 'T' in start:  # 時刻あり
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            all_day = False
        else:  # 終日イベント
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            all_day = True
        
        return {
            'id': event['id'],
            'summary': event.get('summary', '(タイトルなし)'),
            'description': event.get('description', ''),
            'start': start_dt,
            'end': end_dt,
            'all_day': all_day,
            'location': event.get('location', ''),
            'attendees': [attendee.get('email', '') for attendee in event.get('attendees', [])],
            'creator': event.get('creator', {}).get('email', ''),
            'html_link': event.get('htmlLink', '')
        }

# Googleカレンダーサービスのシングルトンインスタンス
google_calendar_service = GoogleCalendarService() 