#!/usr/bin/env python3
"""
Final Test Suite for Fixed Issues
Tests all the fixes made to the Discord Bot without external dependencies
"""

import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

class FixedIssuesTest:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test_pass(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")
    
    def test_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 FINAL TEST SUMMARY:")
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")
        if self.errors:
            print(f"\n❌ REMAINING ISSUES ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        return self.failed == 0

def setup_mock_environment():
    """Setup clean mock environment"""
    # Mock external dependencies
    sys.modules['discord'] = Mock()
    sys.modules['discord.ext'] = Mock()
    sys.modules['discord.ext.commands'] = Mock()
    
    # Set environment variables
    os.environ.update({
        'DISCORD_TOKEN': 'mock_token',
        'GUILD_ID': '123456789',
        'DATABASE_URL': 'sqlite:///test.db',
        'TIMEZONE': 'Asia/Tokyo'
    })

def test_datetime_fixes(test):
    """Test datetime fixes - timezone handling without pytz dependency issues"""
    try:
        # Test 1: Import datetime utilities with fallback
        from bot.utils.datetime_utils import now_jst, format_datetime_jst, ensure_jst, calculate_work_hours
        test.test_pass("DateTime utilities import with fallback")
        
        # Test 2: Test timezone-aware datetime creation (using fallback)
        dt = now_jst()
        if dt.tzinfo is not None:
            test.test_pass("now_jst() returns timezone-aware datetime")
        else:
            test.test_fail("now_jst() timezone", "Returns naive datetime")
        
        # Test 3: Test string formatting
        formatted = format_datetime_jst(dt)
        if formatted and len(formatted) > 10:  # Should be YYYY-MM-DD HH:MM:SS format
            test.test_pass("format_datetime_jst() works correctly")
        else:
            test.test_fail("format_datetime_jst()", f"Invalid format: {formatted}")
        
        # Test 4: Test ensure_jst function
        naive_dt = datetime(2024, 1, 15, 9, 0, 0)
        jst_dt = ensure_jst(naive_dt)
        if jst_dt.tzinfo is not None:
            test.test_pass("ensure_jst() adds timezone to naive datetime")
        else:
            test.test_fail("ensure_jst()", "Failed to add timezone")
        
        # Test 5: Test calculate_work_hours with new signature
        check_in = datetime(2024, 1, 15, 9, 0, 0)
        check_out = datetime(2024, 1, 15, 18, 0, 0)
        break_start = datetime(2024, 1, 15, 12, 0, 0)
        break_end = datetime(2024, 1, 15, 13, 0, 0)
        
        # Test with break times
        work_hours = calculate_work_hours(check_in, check_out, break_start, break_end)
        if work_hours == 8.0:  # 9 hours - 1 hour break = 8 hours
            test.test_pass("calculate_work_hours() with break times")
        else:
            test.test_fail("calculate_work_hours() with break times", f"Expected 8.0, got {work_hours}")
        
        # Test with break_duration parameter
        work_hours_duration = calculate_work_hours(check_in, check_out, break_duration=1.0)
        if work_hours_duration == 8.0:
            test.test_pass("calculate_work_hours() with break_duration parameter")
        else:
            test.test_fail("calculate_work_hours() with break_duration", f"Expected 8.0, got {work_hours_duration}")
        
    except Exception as e:
        test.test_fail("DateTime fixes test", str(e))

def test_database_fixes(test):
    """Test database fixes - utilities and consistency"""
    try:
        # Test 1: Import database utilities
        from bot.utils.database_utils import (
            handle_db_error, transaction_context, safe_execute,
            fetch_one_as_dict, fetch_all_as_dict, DatabaseError
        )
        test.test_pass("Database utilities import")
        
        # Test 2: Test transaction context with mock
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)
            try:
                with transaction_context(conn) as cursor:
                    cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
                    cursor.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
                
                # Verify transaction worked
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM test")
                count = cursor.fetchone()[0]
                if count == 1:
                    test.test_pass("transaction_context() works correctly")
                else:
                    test.test_fail("transaction_context()", f"Expected 1 record, got {count}")
            finally:
                conn.close()
                os.unlink(tmp.name)
        
        # Test 3: Test handle_db_error decorator
        @handle_db_error
        def test_function():
            return "success"
        
        result = test_function()
        if result == "success":
            test.test_pass("handle_db_error() decorator works")
        else:
            test.test_fail("handle_db_error() decorator", f"Expected 'success', got {result}")
        
    except Exception as e:
        test.test_fail("Database fixes test", str(e))

def test_table_consistency(test):
    """Test table name consistency in database schema"""
    try:
        # Test 1: Check database.py schema uses 'attendance' table
        with open('database.py', 'r') as f:
            content = f.read()
            if 'CREATE TABLE IF NOT EXISTS attendance (' in content:
                test.test_pass("Database schema uses correct 'attendance' table name")
            else:
                test.test_fail("Database schema", "Table name inconsistency found")
        
        # Test 2: Verify no 'attendance_records' references in main files
        main_files = ['bot/commands/admin.py', 'bot/commands/attendance.py', 'database.py']
        attendance_records_found = False
        
        for file_path in main_files:
            if Path(file_path).exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'attendance_records' in content:
                        attendance_records_found = True
                        break
        
        if not attendance_records_found:
            test.test_pass("No 'attendance_records' references in main files")
        else:
            test.test_fail("Table name consistency", "Found 'attendance_records' references")
        
    except Exception as e:
        test.test_fail("Table consistency test", str(e))

def test_function_signatures(test):
    """Test function signature consistency"""
    try:
        from bot.utils.datetime_utils import calculate_work_hours
        import inspect
        
        # Test 1: Check calculate_work_hours signature
        sig = inspect.signature(calculate_work_hours)
        params = list(sig.parameters.keys())
        expected_params = ['check_in', 'check_out', 'break_start', 'break_end', 'break_duration']
        
        if params == expected_params:
            test.test_pass("calculate_work_hours() has correct signature")
        else:
            test.test_fail("calculate_work_hours() signature", f"Expected {expected_params}, got {params}")
        
        # Test 2: Test default values
        defaults = [param.default for param in sig.parameters.values()]
        expected_defaults = [inspect.Parameter.empty, inspect.Parameter.empty, None, None, 0.0]
        
        if defaults == expected_defaults:
            test.test_pass("calculate_work_hours() has correct default values")
        else:
            test.test_fail("calculate_work_hours() defaults", f"Expected {expected_defaults}, got {defaults}")
        
    except Exception as e:
        test.test_fail("Function signatures test", str(e))

def test_import_structure(test):
    """Test that all imports work correctly"""
    try:
        # Mock dotenv before importing config
        with patch('config.load_dotenv'):
            # Test 1: Core module imports
            from config import Config
            test.test_pass("Config import with mocked dotenv")
            
            # Test 2: Database manager import
            from core.database import db_manager
            test.test_pass("Database manager import")
            
            # Test 3: Utility imports
            from bot.utils.datetime_utils import now_jst
            from bot.utils.database_utils import handle_db_error
            test.test_pass("Utility modules import correctly")
        
    except Exception as e:
        test.test_fail("Import structure test", str(e))

def main():
    """Run all fix validation tests"""
    print("🧪 Final Test Suite - Validating All Fixes")
    print("=" * 50)
    
    setup_mock_environment()
    test = FixedIssuesTest()
    
    print("\n1️⃣ Testing DateTime Fixes...")
    test_datetime_fixes(test)
    
    print("\n2️⃣ Testing Database Fixes...")
    test_database_fixes(test)
    
    print("\n3️⃣ Testing Table Consistency...")
    test_table_consistency(test)
    
    print("\n4️⃣ Testing Function Signatures...")
    test_function_signatures(test)
    
    print("\n5️⃣ Testing Import Structure...")
    test_import_structure(test)
    
    print("\n" + "=" * 50)
    success = test.summary()
    
    if success:
        print("\n🎉 ALL FIXES VALIDATED SUCCESSFULLY!")
        print("The bot should work correctly once dependencies are installed.")
        print("\nNext steps:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Set up your .env file with Discord token")
        print("3. Run: python main.py")
    else:
        print(f"\n⚠️  Some issues remain. Please review the failed tests above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())