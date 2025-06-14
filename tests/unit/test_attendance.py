"""
Test attendance tracking system - TDD approach
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from src.bot.services.attendance import AttendanceService, AttendanceCalculator, AttendanceRecord


class TestAttendanceRecord:
    """Test attendance record data model."""
    
    def test_record_creation(self):
        """Test creating attendance record."""
        record = AttendanceRecord(
            user_id=123456,
            date="2024-01-15",
            check_in=datetime(2024, 1, 15, 9, 0, 0),
            check_out=datetime(2024, 1, 15, 18, 0, 0)
        )
        
        assert record.user_id == 123456
        assert record.date == "2024-01-15"
        assert record.check_in.hour == 9
        assert record.check_out.hour == 18
    
    def test_record_with_breaks(self):
        """Test attendance record with break times."""
        record = AttendanceRecord(
            user_id=123456,
            date="2024-01-15",
            check_in=datetime(2024, 1, 15, 9, 0, 0),
            check_out=datetime(2024, 1, 15, 18, 0, 0),
            break_start=datetime(2024, 1, 15, 12, 0, 0),
            break_end=datetime(2024, 1, 15, 13, 0, 0)
        )
        
        assert record.break_start.hour == 12
        assert record.break_end.hour == 13
    
    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        record = AttendanceRecord(
            user_id=123456,
            date="2024-01-15",
            check_in=datetime(2024, 1, 15, 9, 0, 0),
            check_out=datetime(2024, 1, 15, 18, 0, 0)
        )
        
        data = record.to_dict()
        assert isinstance(data, dict)
        assert data["user_id"] == 123456
        assert data["date"] == "2024-01-15"
    
    def test_record_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            "user_id": 123456,
            "date": "2024-01-15",
            "check_in": "2024-01-15T09:00:00+09:00",
            "check_out": "2024-01-15T18:00:00+09:00"
        }
        
        record = AttendanceRecord.from_dict(data)
        assert record.user_id == 123456
        assert record.check_in.hour == 9


class TestAttendanceCalculator:
    """Test attendance calculations."""
    
    def test_calculate_work_hours_basic(self):
        """Test basic work hours calculation."""
        calculator = AttendanceCalculator()
        
        check_in = datetime(2024, 1, 15, 9, 0, 0)
        check_out = datetime(2024, 1, 15, 18, 0, 0)
        
        work_hours = calculator.calculate_work_hours(check_in, check_out)
        assert work_hours == 9.0
    
    def test_calculate_work_hours_with_break(self):
        """Test work hours calculation with break."""
        calculator = AttendanceCalculator()
        
        check_in = datetime(2024, 1, 15, 9, 0, 0)
        check_out = datetime(2024, 1, 15, 18, 0, 0)
        break_start = datetime(2024, 1, 15, 12, 0, 0)
        break_end = datetime(2024, 1, 15, 13, 0, 0)
        
        work_hours = calculator.calculate_work_hours(
            check_in, check_out, break_start, break_end
        )
        assert work_hours == 8.0  # 9 hours - 1 hour break
    
    def test_calculate_overtime_hours(self):
        """Test overtime calculation."""
        calculator = AttendanceCalculator(standard_hours=8.0)
        
        work_hours = 10.0
        overtime = calculator.calculate_overtime(work_hours)
        assert overtime == 2.0
    
    def test_calculate_overtime_no_overtime(self):
        """Test no overtime when within standard hours."""
        calculator = AttendanceCalculator(standard_hours=8.0)
        
        work_hours = 7.5
        overtime = calculator.calculate_overtime(work_hours)
        assert overtime == 0.0
    
    def test_calculate_break_duration(self):
        """Test break duration calculation."""
        calculator = AttendanceCalculator()
        
        break_start = datetime(2024, 1, 15, 12, 0, 0)
        break_end = datetime(2024, 1, 15, 13, 30, 0)
        
        duration = calculator.calculate_break_duration(break_start, break_end)
        assert duration == 1.5  # 1.5 hours
    
    def test_is_late(self):
        """Test late arrival detection."""
        calculator = AttendanceCalculator()
        
        # Standard start time 9:00
        on_time = datetime(2024, 1, 15, 9, 0, 0)
        late = datetime(2024, 1, 15, 9, 15, 0)
        
        assert not calculator.is_late(on_time)
        assert calculator.is_late(late)
    
    def test_is_early_departure(self):
        """Test early departure detection."""
        calculator = AttendanceCalculator()
        
        # Standard end time 18:00
        on_time = datetime(2024, 1, 15, 18, 0, 0)
        early = datetime(2024, 1, 15, 17, 30, 0)
        
        assert not calculator.is_early_departure(on_time)
        assert calculator.is_early_departure(early)


class TestAttendanceService:
    """Test attendance service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for testing."""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def attendance_service(self, mock_db):
        """Create attendance service for testing."""
        with patch('src.bot.services.attendance.get_database_manager', return_value=mock_db):
            return AttendanceService()
    
    @pytest.mark.asyncio
    async def test_check_in(self, attendance_service, mock_db):
        """Test user check-in functionality."""
        user_id = 123456
        check_in_time = datetime(2024, 1, 15, 9, 0, 0)
        
        # Mock database responses
        mock_db.execute = AsyncMock()
        mock_db.fetchone = AsyncMock(return_value=None)  # No existing record
        
        result = await attendance_service.check_in(user_id, check_in_time)
        
        assert result.success is True
        assert "checked in" in result.message.lower()
        mock_db.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_in_already_checked_in(self, attendance_service, mock_db):
        """Test check-in when already checked in."""
        user_id = 123456
        check_in_time = datetime(2024, 1, 15, 9, 0, 0)
        
        # Mock existing record
        existing_record = {"check_in": "2024-01-15T08:30:00", "check_out": None}
        mock_db.fetchone = AsyncMock(return_value=existing_record)
        
        result = await attendance_service.check_in(user_id, check_in_time)
        
        assert result.success is False
        assert "already checked in" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_out(self, attendance_service, mock_db):
        """Test user check-out functionality."""
        user_id = 123456
        check_out_time = datetime(2024, 1, 15, 18, 0, 0)
        
        # Mock existing check-in record
        existing_record = {
            "check_in": "2024-01-15T09:00:00",
            "check_out": None,
            "break_start": None,
            "break_end": None
        }
        mock_db.fetchone = AsyncMock(return_value=existing_record)
        mock_db.execute = AsyncMock()
        
        result = await attendance_service.check_out(user_id, check_out_time)
        
        assert result.success is True
        assert "checked out" in result.message.lower()
        mock_db.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_out_not_checked_in(self, attendance_service, mock_db):
        """Test check-out when not checked in."""
        user_id = 123456
        check_out_time = datetime(2024, 1, 15, 18, 0, 0)
        
        mock_db.fetchone = AsyncMock(return_value=None)
        
        result = await attendance_service.check_out(user_id, check_out_time)
        
        assert result.success is False
        assert "not checked in" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_start_break(self, attendance_service, mock_db):
        """Test starting break."""
        user_id = 123456
        break_start_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Mock existing check-in record
        existing_record = {
            "check_in": "2024-01-15T09:00:00",
            "check_out": None,
            "break_start": None,
            "break_end": None
        }
        mock_db.fetchone = AsyncMock(return_value=existing_record)
        mock_db.execute = AsyncMock()
        
        result = await attendance_service.start_break(user_id, break_start_time)
        
        assert result.success is True
        assert "break started" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_end_break(self, attendance_service, mock_db):
        """Test ending break."""
        user_id = 123456
        break_end_time = datetime(2024, 1, 15, 13, 0, 0)
        
        # Mock existing record with break started
        existing_record = {
            "check_in": "2024-01-15T09:00:00",
            "check_out": None,
            "break_start": "2024-01-15T12:00:00",
            "break_end": None
        }
        mock_db.fetchone = AsyncMock(return_value=existing_record)
        mock_db.execute = AsyncMock()
        
        result = await attendance_service.end_break(user_id, break_end_time)
        
        assert result.success is True
        assert "break ended" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_get_daily_record(self, attendance_service, mock_db):
        """Test getting daily attendance record."""
        user_id = 123456
        date = "2024-01-15"
        
        mock_record = {
            "user_id": user_id,
            "date": date,
            "check_in": "2024-01-15T09:00:00",
            "check_out": "2024-01-15T18:00:00",
            "work_hours": 8.0,
            "overtime_hours": 0.0
        }
        mock_db.fetchone = AsyncMock(return_value=mock_record)
        
        record = await attendance_service.get_daily_record(user_id, date)
        
        assert record is not None
        assert record.user_id == user_id
        assert record.date == date
    
    @pytest.mark.asyncio
    async def test_get_weekly_summary(self, attendance_service, mock_db):
        """Test getting weekly attendance summary."""
        user_id = 123456
        week_start = "2024-01-15"
        
        mock_records = [
            {"date": "2024-01-15", "work_hours": 8.0, "overtime_hours": 0.0},
            {"date": "2024-01-16", "work_hours": 9.0, "overtime_hours": 1.0},
            {"date": "2024-01-17", "work_hours": 7.5, "overtime_hours": 0.0},
        ]
        mock_db.fetchall = AsyncMock(return_value=mock_records)
        
        summary = await attendance_service.get_weekly_summary(user_id, week_start)
        
        assert summary["total_work_hours"] == 24.5
        assert summary["total_overtime_hours"] == 1.0
        assert summary["days_worked"] == 3
    
    @pytest.mark.asyncio
    async def test_get_monthly_summary(self, attendance_service, mock_db):
        """Test getting monthly attendance summary."""
        user_id = 123456
        year = 2024
        month = 1
        
        mock_records = [
            {"date": "2024-01-15", "work_hours": 8.0, "overtime_hours": 0.0},
            {"date": "2024-01-16", "work_hours": 9.0, "overtime_hours": 1.0},
        ]
        mock_db.fetchall = AsyncMock(return_value=mock_records)
        
        summary = await attendance_service.get_monthly_summary(user_id, year, month)
        
        assert summary["total_work_hours"] == 17.0
        assert summary["total_overtime_hours"] == 1.0
        assert summary["average_work_hours"] == 8.5
    
    @pytest.mark.asyncio
    async def test_get_current_status(self, attendance_service, mock_db):
        """Test getting current attendance status."""
        user_id = 123456
        
        # Mock current record (checked in, no break)
        current_record = {
            "check_in": "2024-01-15T09:00:00",
            "check_out": None,
            "break_start": None,
            "break_end": None
        }
        mock_db.fetchone = AsyncMock(return_value=current_record)
        
        status = await attendance_service.get_current_status(user_id)
        
        assert status["status"] == "checked_in"
        assert status["check_in"] is not None
        assert status["on_break"] is False
    
    @pytest.mark.asyncio
    async def test_export_csv(self, attendance_service, mock_db):
        """Test exporting attendance data to CSV."""
        user_id = 123456
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        mock_records = [
            {
                "date": "2024-01-15",
                "check_in": "2024-01-15T09:00:00",
                "check_out": "2024-01-15T18:00:00",
                "work_hours": 8.0,
                "overtime_hours": 0.0
            }
        ]
        mock_db.fetchall = AsyncMock(return_value=mock_records)
        
        csv_content = await attendance_service.export_csv(user_id, start_date, end_date)
        
        assert isinstance(csv_content, str)
        assert "Date,Check In,Check Out" in csv_content
        assert "2024-01-15" in csv_content


class TestAttendanceIntegration:
    """Test attendance system integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_day_workflow(self):
        """Test complete daily attendance workflow."""
        mock_db = AsyncMock()
        user_id = 123456
        
        with patch('src.bot.services.attendance.get_database_manager', return_value=mock_db):
            service = AttendanceService()
            
            # Mock database responses for each step
            mock_db.fetchone = AsyncMock(side_effect=[
                None,  # No existing record for check-in
                {"check_in": "2024-01-15T09:00:00", "check_out": None, "break_start": None, "break_end": None},  # For break start
                {"check_in": "2024-01-15T09:00:00", "check_out": None, "break_start": "2024-01-15T12:00:00", "break_end": None},  # For break end
                {"check_in": "2024-01-15T09:00:00", "check_out": None, "break_start": "2024-01-15T12:00:00", "break_end": "2024-01-15T13:00:00"}  # For check-out
            ])
            mock_db.execute = AsyncMock()
            
            # 1. Check in
            result = await service.check_in(user_id, datetime(2024, 1, 15, 9, 0, 0))
            assert result.success is True
            
            # 2. Start break
            result = await service.start_break(user_id, datetime(2024, 1, 15, 12, 0, 0))
            assert result.success is True
            
            # 3. End break
            result = await service.end_break(user_id, datetime(2024, 1, 15, 13, 0, 0))
            assert result.success is True
            
            # 4. Check out
            result = await service.check_out(user_id, datetime(2024, 1, 15, 18, 0, 0))
            assert result.success is True
            
            # Should have made 4 database calls
            assert mock_db.execute.call_count == 4
    
    @pytest.mark.asyncio
    async def test_attendance_error_handling(self):
        """Test attendance system error handling."""
        mock_db = AsyncMock()
        user_id = 123456
        
        with patch('src.bot.services.attendance.get_database_manager', return_value=mock_db):
            service = AttendanceService()
            
            # Simulate database error
            mock_db.execute.side_effect = Exception("Database error")
            mock_db.fetchone = AsyncMock(return_value=None)
            
            result = await service.check_in(user_id, datetime(2024, 1, 15, 9, 0, 0))
            
            # Should handle error gracefully
            assert result.success is False
            assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_attendance_validation(self):
        """Test attendance data validation."""
        mock_db = AsyncMock()
        user_id = 123456
        
        with patch('src.bot.services.attendance.get_database_manager', return_value=mock_db):
            service = AttendanceService()
            
            # Test invalid check-out before check-in
            result = await service.check_out(user_id, datetime(2024, 1, 15, 8, 0, 0))
            assert result.success is False
            
            # Test break end before break start
            mock_db.fetchone = AsyncMock(return_value={
                "check_in": "2024-01-15T09:00:00",
                "break_start": "2024-01-15T12:00:00"
            })
            
            result = await service.end_break(user_id, datetime(2024, 1, 15, 11, 0, 0))
            assert result.success is False