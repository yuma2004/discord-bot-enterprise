"""
日時処理のユーティリティモジュール
JST (Japan Standard Time) での日時操作を提供
"""
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
try:
    import pytz
    JST = pytz.timezone('Asia/Tokyo')
    PYTZ_AVAILABLE = True
except ImportError:
    # Fallback when pytz is not available
    from datetime import timezone, timedelta
    JST = timezone(timedelta(hours=9))  # JST is UTC+9
    PYTZ_AVAILABLE = False


def now_jst() -> datetime:
    """現在のJST日時を取得"""
    return datetime.now(JST)


def today_jst() -> date:
    """現在のJST日付を取得"""
    return now_jst().date()


def ensure_jst(dt) -> datetime:
    """datetime オブジェクトがJSTタイムゾーンを持つことを保証"""
    if dt is None:
        return None
    
    # 文字列の場合はdatetimeに変換
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"無効な日時形式です: {dt}")
    
    # 数値など無効な型の場合はエラー
    if not isinstance(dt, datetime):
        raise ValueError(f"datetime型または文字列を期待しましたが、{type(dt)}が渡されました")
    
    if dt.tzinfo is None:
        # タイムゾーン情報がない場合、JSTとして扱う
        if PYTZ_AVAILABLE:
            return JST.localize(dt)
        else:
            return dt.replace(tzinfo=JST)
    elif dt.tzinfo != JST:
        # 異なるタイムゾーンの場合、JSTに変換
        return dt.astimezone(JST)
    return dt


def format_time_only(dt) -> str:
    """時刻のみをフォーマット (HH:MM)"""
    if dt is None:
        return ""
    
    # 文字列の場合はdatetimeに変換
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return ""
    
    if isinstance(dt, datetime):
        return dt.strftime('%H:%M')
    
    return ""


def format_date_only(dt) -> str:
    """日付のみをフォーマット (YYYY-MM-DD)"""
    if dt is None:
        return ""
    
    # 既にYYYY-MM-DD形式の文字列の場合はそのまま返す
    if isinstance(dt, str) and len(dt) == 10 and dt.count('-') == 2:
        return dt
    
    # 文字列の場合はdatetimeに変換
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return ""
    
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d')
    elif isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    
    return ""


def format_datetime_for_display(dt) -> str:
    """日時を表示用にフォーマット"""
    if dt is None:
        return ""
    
    # 文字列の場合はdatetimeに変換
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return ""
    
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return ""


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """指定された年月の開始日と終了日を取得"""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return start_date, end_date


def parse_date_string(date_str: str) -> date:
    """文字列を日付に変換"""
    if not date_str:
        raise ValueError("日付文字列が空です")
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            raise ValueError(f"無効な日付形式です: {date_str} (YYYY-MM-DD形式で入力してください)")


def calculate_time_difference(start_time, end_time) -> float:
    """2つの時刻の差を時間で計算"""
    if not start_time or not end_time:
        return 0.0
    
    # 文字列の場合はdatetimeに変換
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    if end_time <= start_time:
        return 0.0
    
    total_seconds = (end_time - start_time).total_seconds()
    return round(total_seconds / 3600, 2)


def calculate_work_hours(check_in, check_out, break_start=None, break_end=None, break_duration=0.0) -> float:
    """勤務時間を計算 (休憩時間を除く)"""
    if not check_in or not check_out:
        return 0.0
    
    # 文字列の場合はdatetimeに変換
    if isinstance(check_in, str):
        check_in = datetime.fromisoformat(check_in.replace('Z', '+00:00'))
    if isinstance(check_out, str):
        check_out = datetime.fromisoformat(check_out.replace('Z', '+00:00'))
    
    if check_out <= check_in:
        return 0.0
    
    # 総勤務時間
    total_hours = (check_out - check_in).total_seconds() / 3600
    
    # 休憩時間を差し引く
    break_hours = 0.0
    if break_start and break_end:
        break_hours = calculate_time_difference(break_start, break_end)
    elif break_duration > 0:
        break_hours = break_duration
    
    work_hours = max(0.0, total_hours - break_hours)
    return round(work_hours, 2)


def calculate_overtime_hours(work_hours: float, standard_hours: float = 8.0) -> float:
    """残業時間を計算"""
    overtime = max(0.0, work_hours - standard_hours)
    return round(overtime, 2)


def adapt_datetime_for_sqlite(dt: datetime) -> str:
    """SQLite用のdatetime変換"""
    return dt.isoformat()


def convert_datetime_from_sqlite(val: bytes) -> datetime:
    """SQLiteからのdatetime変換"""
    return datetime.fromisoformat(val.decode())


def format_datetime_jst(dt) -> str:
    """JST datetime を文字列にフォーマット"""
    if dt is None:
        return ""
    
    dt_jst = ensure_jst(dt)
    return dt_jst.strftime('%Y-%m-%d %H:%M:%S')


# SQLite用のカスタムアダプター/コンバーター
sqlite3.register_adapter(datetime, adapt_datetime_for_sqlite)
sqlite3.register_converter("datetime", convert_datetime_from_sqlite)