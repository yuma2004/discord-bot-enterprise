"""
Attendance tracking service - Clean TDD implementation
"""
import csv
import io
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, NamedTuple
import pytz

from src.core.database import get_database_manager
from src.core.logging import get_logger, log_user_action
from src.core.error_handling import handle_database_error, SystemError


class AttendanceResult(NamedTuple):
    """Result of attendance operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class AttendanceRecord:
    """Attendance record data model."""
    user_id: int
    date: str
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    work_hours: float = 0.0
    overtime_hours: float = 0.0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "user_id": self.user_id,
            "date": self.date,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "break_start": self.break_start.isoformat() if self.break_start else None,
            "break_end": self.break_end.isoformat() if self.break_end else None,
            "work_hours": self.work_hours,
            "overtime_hours": self.overtime_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttendanceRecord':
        """Create record from dictionary."""
        def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if dt_str:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return None
        
        return cls(
            user_id=data["user_id"],
            date=data["date"],
            check_in=parse_datetime(data.get("check_in")),
            check_out=parse_datetime(data.get("check_out")),
            break_start=parse_datetime(data.get("break_start")),
            break_end=parse_datetime(data.get("break_end")),
            work_hours=float(data.get("work_hours", 0.0)),
            overtime_hours=float(data.get("overtime_hours", 0.0)),
            created_at=parse_datetime(data.get("created_at"))
        )


class AttendanceCalculator:
    """Calculator for attendance-related calculations."""
    
    def __init__(self, standard_hours: float = 8.0, standard_start_time: str = "09:00", standard_end_time: str = "18:00"):
        self.standard_hours = standard_hours
        self.standard_start_time = standard_start_time
        self.standard_end_time = standard_end_time
    
    def calculate_work_hours(self, check_in: datetime, check_out: datetime, 
                           break_start: Optional[datetime] = None, 
                           break_end: Optional[datetime] = None) -> float:
        """Calculate total work hours."""
        if not check_in or not check_out:
            return 0.0
        
        # Calculate total time
        total_time = check_out - check_in
        work_hours = total_time.total_seconds() / 3600
        
        # Subtract break time if both break_start and break_end are provided
        if break_start and break_end:
            break_duration = self.calculate_break_duration(break_start, break_end)
            work_hours -= break_duration
        
        return max(0.0, work_hours)
    
    def calculate_break_duration(self, break_start: datetime, break_end: datetime) -> float:
        """Calculate break duration in hours."""
        if not break_start or not break_end:
            return 0.0
        
        if break_end <= break_start:
            return 0.0
        
        duration = break_end - break_start
        return duration.total_seconds() / 3600
    
    def calculate_overtime(self, work_hours: float) -> float:
        """Calculate overtime hours."""
        return max(0.0, work_hours - self.standard_hours)
    
    def is_late(self, check_in: datetime, grace_minutes: int = 5) -> bool:
        """Check if user is late for work."""
        standard_time = datetime.strptime(self.standard_start_time, "%H:%M").time()
        check_in_time = check_in.time()
        
        # Add grace period
        grace_time = (datetime.combine(datetime.today(), standard_time) + 
                     timedelta(minutes=grace_minutes)).time()
        
        return check_in_time > grace_time
    
    def is_early_departure(self, check_out: datetime) -> bool:
        """Check if user left early."""
        standard_time = datetime.strptime(self.standard_end_time, "%H:%M").time()
        check_out_time = check_out.time()
        
        return check_out_time < standard_time


class AttendanceService:
    """Main attendance service."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.calculator = AttendanceCalculator()
        
        # Set timezone
        try:
            self.timezone = pytz.timezone('Asia/Tokyo')
        except:
            self.timezone = timezone(timedelta(hours=9))  # JST fallback
    
    def _get_current_time(self) -> datetime:
        """Get current time in JST."""
        now = datetime.now(self.timezone)
        return now
    
    def _get_date_string(self, dt: datetime) -> str:
        """Get date string in YYYY-MM-DD format."""
        return dt.strftime("%Y-%m-%d")
    
    async def check_in(self, user_id: int, check_in_time: Optional[datetime] = None) -> AttendanceResult:
        """Check in user for work."""
        if not check_in_time:
            check_in_time = self._get_current_time()
        
        date_str = self._get_date_string(check_in_time)
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                # Check if user already checked in today
                cursor = await conn.execute(
                    "SELECT check_in, check_out FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, date_str)
                )
                existing = await cursor.fetchone()
                
                if existing and existing[0] and not existing[1]:  # Already checked in, not checked out
                    return AttendanceResult(
                        success=False,
                        message="You are already checked in for today."
                    )
                
                # Create or update attendance record
                if existing:
                    # Update existing record
                    await conn.execute(
                        "UPDATE attendance SET check_in = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND date = ?",
                        (check_in_time.isoformat(), user_id, date_str)
                    )
                else:
                    # Create new record
                    await conn.execute(
                        "INSERT INTO attendance (user_id, date, check_in) VALUES (?, ?, ?)",
                        (user_id, date_str, check_in_time.isoformat())
                    )
                
                await conn.commit()
                
                # Log user action
                log_user_action(
                    self.logger,
                    user_id=user_id,
                    action="check_in",
                    check_in_time=check_in_time.isoformat(),
                    date=date_str
                )
                
                # Check if late
                is_late = self.calculator.is_late(check_in_time)
                late_message = " (Late arrival)" if is_late else ""
                
                return AttendanceResult(
                    success=True,
                    message=f"Successfully checked in at {check_in_time.strftime('%H:%M')}{late_message}",
                    data={"check_in_time": check_in_time.isoformat(), "is_late": is_late}
                )
        
        except Exception as e:
            self.logger.error(f"Check-in failed for user {user_id}: {e}")
            return AttendanceResult(
                success=False,
                message="Failed to check in. Please try again later."
            )
    
    async def check_out(self, user_id: int, check_out_time: Optional[datetime] = None) -> AttendanceResult:
        """Check out user from work."""
        if not check_out_time:
            check_out_time = self._get_current_time()
        
        date_str = self._get_date_string(check_out_time)
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                # Get today's attendance record
                cursor = await conn.execute(
                    "SELECT check_in, check_out, break_start, break_end FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, date_str)
                )
                record = await cursor.fetchone()
                
                if not record or not record[0]:  # No check-in record
                    return AttendanceResult(
                        success=False,
                        message="You are not checked in for today."
                    )
                
                if record[1]:  # Already checked out
                    return AttendanceResult(
                        success=False,
                        message="You have already checked out for today."
                    )
                
                # Parse times
                check_in = datetime.fromisoformat(record[0])
                break_start = datetime.fromisoformat(record[2]) if record[2] else None
                break_end = datetime.fromisoformat(record[3]) if record[3] else None
                
                # Calculate work hours
                work_hours = self.calculator.calculate_work_hours(
                    check_in, check_out_time, break_start, break_end
                )
                overtime_hours = self.calculator.calculate_overtime(work_hours)
                
                # Update record
                await conn.execute(
                    """UPDATE attendance 
                       SET check_out = ?, work_hours = ?, overtime_hours = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE user_id = ? AND date = ?""",
                    (check_out_time.isoformat(), work_hours, overtime_hours, user_id, date_str)
                )
                await conn.commit()
                
                # Log user action
                log_user_action(
                    self.logger,
                    user_id=user_id,
                    action="check_out",
                    check_out_time=check_out_time.isoformat(),
                    work_hours=work_hours,
                    overtime_hours=overtime_hours
                )
                
                # Check if early departure
                is_early = self.calculator.is_early_departure(check_out_time)
                early_message = " (Early departure)" if is_early else ""
                
                return AttendanceResult(
                    success=True,
                    message=f"Successfully checked out at {check_out_time.strftime('%H:%M')}{early_message}. Work hours: {work_hours:.1f}h",
                    data={
                        "check_out_time": check_out_time.isoformat(),
                        "work_hours": work_hours,
                        "overtime_hours": overtime_hours,
                        "is_early": is_early
                    }
                )
        
        except Exception as e:
            self.logger.error(f"Check-out failed for user {user_id}: {e}")
            return AttendanceResult(
                success=False,
                message="Failed to check out. Please try again later."
            )
    
    async def start_break(self, user_id: int, break_start_time: Optional[datetime] = None) -> AttendanceResult:
        """Start break for user."""
        if not break_start_time:
            break_start_time = self._get_current_time()
        
        date_str = self._get_date_string(break_start_time)
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                # Check current status
                cursor = await conn.execute(
                    "SELECT check_in, check_out, break_start, break_end FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, date_str)
                )
                record = await cursor.fetchone()
                
                if not record or not record[0]:
                    return AttendanceResult(
                        success=False,
                        message="You must check in before starting a break."
                    )
                
                if record[1]:  # Already checked out
                    return AttendanceResult(
                        success=False,
                        message="You have already checked out for today."
                    )
                
                if record[2] and not record[3]:  # Already on break
                    return AttendanceResult(
                        success=False,
                        message="You are already on break."
                    )
                
                # Update break start time
                await conn.execute(
                    "UPDATE attendance SET break_start = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND date = ?",
                    (break_start_time.isoformat(), user_id, date_str)
                )
                await conn.commit()
                
                log_user_action(
                    self.logger,
                    user_id=user_id,
                    action="start_break",
                    break_start_time=break_start_time.isoformat()
                )
                
                return AttendanceResult(
                    success=True,
                    message=f"Break started at {break_start_time.strftime('%H:%M')}",
                    data={"break_start_time": break_start_time.isoformat()}
                )
        
        except Exception as e:
            self.logger.error(f"Start break failed for user {user_id}: {e}")
            return AttendanceResult(
                success=False,
                message="Failed to start break. Please try again later."
            )
    
    async def end_break(self, user_id: int, break_end_time: Optional[datetime] = None) -> AttendanceResult:
        """End break for user."""
        if not break_end_time:
            break_end_time = self._get_current_time()
        
        date_str = self._get_date_string(break_end_time)
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                # Check current status
                cursor = await conn.execute(
                    "SELECT check_in, check_out, break_start, break_end FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, date_str)
                )
                record = await cursor.fetchone()
                
                if not record or not record[0]:
                    return AttendanceResult(
                        success=False,
                        message="You must check in first."
                    )
                
                if not record[2]:  # No break started
                    return AttendanceResult(
                        success=False,
                        message="You are not on break."
                    )
                
                if record[3]:  # Break already ended
                    return AttendanceResult(
                        success=False,
                        message="Break has already ended."
                    )
                
                # Validate break end time
                break_start = datetime.fromisoformat(record[2])
                if break_end_time <= break_start:
                    return AttendanceResult(
                        success=False,
                        message="Break end time must be after break start time."
                    )
                
                # Calculate break duration
                break_duration = self.calculator.calculate_break_duration(break_start, break_end_time)
                
                # Update break end time
                await conn.execute(
                    "UPDATE attendance SET break_end = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND date = ?",
                    (break_end_time.isoformat(), user_id, date_str)
                )
                await conn.commit()
                
                log_user_action(
                    self.logger,
                    user_id=user_id,
                    action="end_break",
                    break_end_time=break_end_time.isoformat(),
                    break_duration=break_duration
                )
                
                return AttendanceResult(
                    success=True,
                    message=f"Break ended at {break_end_time.strftime('%H:%M')}. Duration: {break_duration:.1f}h",
                    data={
                        "break_end_time": break_end_time.isoformat(),
                        "break_duration": break_duration
                    }
                )
        
        except Exception as e:
            self.logger.error(f"End break failed for user {user_id}: {e}")
            return AttendanceResult(
                success=False,
                message="Failed to end break. Please try again later."
            )
    
    async def get_current_status(self, user_id: int) -> Dict[str, Any]:
        """Get current attendance status for user."""
        today = self._get_date_string(self._get_current_time())
        
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT check_in, check_out, break_start, break_end FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, today)
                )
                record = await cursor.fetchone()
                
                if not record:
                    return {
                        "status": "not_checked_in",
                        "check_in": None,
                        "check_out": None,
                        "on_break": False,
                        "message": "Not checked in"
                    }
                
                check_in = record[0]
                check_out = record[1]
                break_start = record[2]
                break_end = record[3]
                
                if check_out:
                    return {
                        "status": "checked_out",
                        "check_in": check_in,
                        "check_out": check_out,
                        "on_break": False,
                        "message": "Checked out"
                    }
                elif break_start and not break_end:
                    return {
                        "status": "on_break",
                        "check_in": check_in,
                        "check_out": None,
                        "on_break": True,
                        "break_start": break_start,
                        "message": "On break"
                    }
                elif check_in:
                    return {
                        "status": "checked_in",
                        "check_in": check_in,
                        "check_out": None,
                        "on_break": False,
                        "message": "Checked in"
                    }
                else:
                    return {
                        "status": "not_checked_in",
                        "check_in": None,
                        "check_out": None,
                        "on_break": False,
                        "message": "Not checked in"
                    }
        
        except Exception as e:
            self.logger.error(f"Get status failed for user {user_id}: {e}")
            return {
                "status": "error",
                "message": "Failed to get status"
            }
    
    async def get_daily_record(self, user_id: int, date: str) -> Optional[AttendanceRecord]:
        """Get daily attendance record."""
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM attendance WHERE user_id = ? AND date = ?",
                    (user_id, date)
                )
                record = await cursor.fetchone()
                
                if record:
                    return AttendanceRecord.from_dict(dict(record))
                return None
        
        except Exception as e:
            self.logger.error(f"Get daily record failed for user {user_id}, date {date}: {e}")
            return None
    
    async def get_weekly_summary(self, user_id: int, week_start: str) -> Dict[str, Any]:
        """Get weekly attendance summary."""
        try:
            # Calculate week end date
            start_date = datetime.strptime(week_start, "%Y-%m-%d")
            end_date = start_date + timedelta(days=6)
            week_end = end_date.strftime("%Y-%m-%d")
            
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """SELECT date, work_hours, overtime_hours 
                       FROM attendance 
                       WHERE user_id = ? AND date BETWEEN ? AND ?
                       ORDER BY date""",
                    (user_id, week_start, week_end)
                )
                records = await cursor.fetchall()
                
                total_work_hours = sum(record[1] or 0 for record in records)
                total_overtime_hours = sum(record[2] or 0 for record in records)
                days_worked = len([r for r in records if r[1] and r[1] > 0])
                
                return {
                    "week_start": week_start,
                    "week_end": week_end,
                    "total_work_hours": total_work_hours,
                    "total_overtime_hours": total_overtime_hours,
                    "days_worked": days_worked,
                    "average_work_hours": total_work_hours / max(days_worked, 1),
                    "records": [dict(record) for record in records]
                }
        
        except Exception as e:
            self.logger.error(f"Get weekly summary failed for user {user_id}: {e}")
            return {}
    
    async def get_monthly_summary(self, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Get monthly attendance summary."""
        try:
            # Calculate month start and end
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"
            
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """SELECT date, work_hours, overtime_hours 
                       FROM attendance 
                       WHERE user_id = ? AND date >= ? AND date < ?
                       ORDER BY date""",
                    (user_id, start_date, end_date)
                )
                records = await cursor.fetchall()
                
                total_work_hours = sum(record[1] or 0 for record in records)
                total_overtime_hours = sum(record[2] or 0 for record in records)
                days_worked = len([r for r in records if r[1] and r[1] > 0])
                
                return {
                    "year": year,
                    "month": month,
                    "total_work_hours": total_work_hours,
                    "total_overtime_hours": total_overtime_hours,
                    "days_worked": days_worked,
                    "average_work_hours": total_work_hours / max(days_worked, 1),
                    "records": [dict(record) for record in records]
                }
        
        except Exception as e:
            self.logger.error(f"Get monthly summary failed for user {user_id}: {e}")
            return {}
    
    async def export_csv(self, user_id: int, start_date: str, end_date: str) -> str:
        """Export attendance data to CSV format."""
        try:
            db_manager = get_database_manager()
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """SELECT date, check_in, check_out, break_start, break_end, work_hours, overtime_hours
                       FROM attendance 
                       WHERE user_id = ? AND date BETWEEN ? AND ?
                       ORDER BY date""",
                    (user_id, start_date, end_date)
                )
                records = await cursor.fetchall()
                
                # Create CSV content
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    "Date", "Check In", "Check Out", "Break Start", "Break End", 
                    "Work Hours", "Overtime Hours"
                ])
                
                # Write data
                for record in records:
                    writer.writerow([
                        record[0],  # date
                        record[1][:16] if record[1] else "",  # check_in (remove seconds)
                        record[2][:16] if record[2] else "",  # check_out
                        record[3][:16] if record[3] else "",  # break_start
                        record[4][:16] if record[4] else "",  # break_end
                        f"{record[5]:.1f}" if record[5] else "0.0",  # work_hours
                        f"{record[6]:.1f}" if record[6] else "0.0"   # overtime_hours
                    ])
                
                return output.getvalue()
        
        except Exception as e:
            self.logger.error(f"Export CSV failed for user {user_id}: {e}")
            return ""


# Global service instance
_attendance_service: Optional[AttendanceService] = None


def get_attendance_service() -> AttendanceService:
    """Get global attendance service instance."""
    global _attendance_service
    if _attendance_service is None:
        _attendance_service = AttendanceService()
    return _attendance_service