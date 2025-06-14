"""
Datetime utilities for Discord Bot Enterprise
"""
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
import pytz


def now_jst() -> datetime:
    """Get current datetime in JST timezone."""
    jst = pytz.timezone('Asia/Tokyo')
    return datetime.now(jst)


def today_jst() -> date:
    """Get current date in JST timezone."""
    return now_jst().date()


def ensure_jst(dt: datetime) -> datetime:
    """Ensure datetime is in JST timezone."""
    if dt.tzinfo is None:
        jst = pytz.timezone('Asia/Tokyo')
        return jst.localize(dt)
    return dt.astimezone(pytz.timezone('Asia/Tokyo'))


def format_time_only(dt: datetime) -> str:
    """Format datetime to show time only (HH:MM)."""
    return dt.strftime('%H:%M')


def format_date_only(dt: datetime) -> str:
    """Format datetime to show date only (YYYY-MM-DD)."""
    return dt.strftime('%Y-%m-%d')


def format_datetime_for_display(dt: datetime) -> str:
    """Format datetime for user display."""
    return dt.strftime('%Y-%m-%d %H:%M')


def parse_date_string(date_str: str) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """Get start and end dates for a given month."""
    start_date = date(year, month, 1)
    
    # Calculate last day of month
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def calculate_work_hours(check_in: datetime, check_out: datetime, 
                        break_start: Optional[datetime] = None, 
                        break_end: Optional[datetime] = None) -> float:
    """Calculate work hours between check in/out times."""
    if not check_out:
        return 0.0
    
    total_hours = (check_out - check_in).total_seconds() / 3600
    
    # Subtract break time if provided
    if break_start and break_end:
        break_hours = (break_end - break_start).total_seconds() / 3600
        total_hours -= break_hours
    
    return max(0.0, total_hours)


def calculate_time_difference(start: datetime, end: datetime) -> float:
    """Calculate time difference in hours."""
    return (end - start).total_seconds() / 3600