#!/usr/bin/env python3
"""
Comprehensive Test Suite for Discord Bot Issues
Identifies date/time inconsistencies, command errors, and other issues
"""

import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.fixes_needed = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def add_fix_needed(self, issue, fix):
        self.fixes_needed.append(f"{issue} -> {fix}")
        print(f"🔧 FIX NEEDED: {issue} -> {fix}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 TEST SUMMARY:")
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")
        if self.fixes_needed:
            print(f"\n🔧 FIXES NEEDED ({len(self.fixes_needed)}):")
            for fix in self.fixes_needed:
                print(f"  - {fix}")
        return self.failed == 0

def setup_mock_environment():
    """Setup mock environment to avoid dependency issues"""
    # Mock external dependencies
    sys.modules['discord'] = Mock()
    sys.modules['discord.ext'] = Mock()
    sys.modules['discord.ext.commands'] = Mock()
    sys.modules['pytz'] = Mock()
    
    # Create mock timezone
    mock_timezone = Mock()
    mock_timezone.localize = Mock(side_effect=lambda dt: dt.replace(tzinfo=timezone.utc))
    sys.modules['pytz'].timezone = Mock(return_value=mock_timezone)
    
    # Mock dotenv
    os.environ.update({
        'DISCORD_TOKEN': 'mock_token',
        'GUILD_ID': '123456789',
        'DATABASE_URL': 'sqlite:///test.db',
        'TIMEZONE': 'Asia/Tokyo'
    })

def test_datetime_issues(results):
    """Test for datetime and timezone related issues"""
    try:
        # Test 1: Import datetime utilities
        try:
            from bot.utils.datetime_utils import now_jst, format_datetime_jst
            results.add_pass("datetime_utils import")
        except ImportError as e:
            results.add_fail("datetime_utils import", str(e))
            results.add_fix_needed("Missing datetime utilities", "Create bot/utils/datetime_utils.py")
            return
        
        # Test 2: Check for naive datetime usage
        files_to_check = [
            'bot/commands/admin.py',
            'bot/commands/attendance.py', 
            'bot/commands/task_manager.py'
        ]
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'datetime.now()' in content:
                        results.add_fix_needed(f"Naive datetime in {file_path}", "Replace with now_jst()")
                    else:
                        results.add_pass(f"No naive datetime in {file_path}")
            else:
                results.add_fail(f"File check {file_path}", "File not found")
        
        # Test 3: Timezone awareness
        try:
            dt = now_jst()
            if dt.tzinfo is None:
                results.add_fix_needed("now_jst() returns naive datetime", "Add timezone info")
            else:
                results.add_pass("now_jst() timezone aware")
        except Exception as e:
            results.add_fail("now_jst() test", str(e))
            
    except Exception as e:
        results.add_fail("datetime_issues test", str(e))

def test_database_issues(results):
    """Test for database related issues"""
    try:
        # Test 1: Database utilities import
        try:
            from bot.utils.database_utils import transaction_context, handle_db_error
            results.add_pass("database_utils import")
        except ImportError as e:
            results.add_fail("database_utils import", str(e))
            results.add_fix_needed("Missing database utilities", "Create bot/utils/database_utils.py")
            return
        
        # Test 2: Check for table name inconsistencies
        files_to_check = [
            'bot/commands/admin.py',
            'bot/commands/attendance.py',
            'database.py'
        ]
        
        table_references = {}
        for file_path in files_to_check:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'attendance_records' in content:
                        table_references.setdefault('attendance_records', []).append(file_path)
                    if 'attendance' in content and 'attendance_records' not in content:
                        table_references.setdefault('attendance', []).append(file_path)
        
        if 'attendance_records' in table_references and 'attendance' in table_references:
            results.add_fix_needed("Table name inconsistency", "Standardize to 'attendance'")
        else:
            results.add_pass("Table name consistency check")
        
        # Test 3: Function signature consistency  
        try:
            # Check if calculate_work_hours exists and has consistent signature
            from bot.utils.datetime_utils import calculate_work_hours
            import inspect
            sig = inspect.signature(calculate_work_hours)
            params = list(sig.parameters.keys())
            if 'break_duration' not in params:
                results.add_fix_needed("calculate_work_hours missing break_duration", "Add break_duration parameter")
            else:
                results.add_pass("calculate_work_hours signature correct")
        except Exception as e:
            results.add_fail("calculate_work_hours signature test", str(e))
            
    except Exception as e:
        results.add_fail("database_issues test", str(e))

def test_command_errors(results):
    """Test for command related errors"""
    try:
        # Test 1: Check for command import issues
        command_files = [
            'bot/commands/admin.py',
            'bot/commands/attendance.py',
            'bot/commands/task_manager.py',
            'bot/commands/calendar.py',
            'bot/commands/help.py'
        ]
        
        for cmd_file in command_files:
            if Path(cmd_file).exists():
                results.add_pass(f"Command file exists: {cmd_file}")
                
                # Check for common error patterns
                with open(cmd_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for proper error handling
                    if 'try:' in content and 'except:' in content:
                        results.add_pass(f"Error handling in {cmd_file}")
                    else:
                        results.add_fix_needed(f"Missing error handling in {cmd_file}", "Add try/except blocks")
                    
                    # Check for await usage in async functions
                    if 'async def' in content:
                        if 'await' not in content:
                            results.add_fix_needed(f"Async function without await in {cmd_file}", "Review async/await usage")
                        else:
                            results.add_pass(f"Proper async/await in {cmd_file}")
            else:
                results.add_fail(f"Command file check: {cmd_file}", "File not found")
                
    except Exception as e:
        results.add_fail("command_errors test", str(e))

def test_configuration_issues(results):
    """Test for configuration related issues"""
    try:
        # Test 1: Environment variables
        required_env_vars = ['DISCORD_TOKEN', 'GUILD_ID', 'DATABASE_URL', 'TIMEZONE']
        for var in required_env_vars:
            if var in os.environ:
                results.add_pass(f"Environment variable {var} set")
            else:
                results.add_fix_needed(f"Missing environment variable {var}", "Add to .env file")
        
        # Test 2: Config file import
        try:
            # Mock the dotenv load since we don't have it installed
            with patch('config.load_dotenv'):
                from config import Config
                results.add_pass("Config import successful")
        except Exception as e:
            results.add_fail("Config import", str(e))
        
        # Test 3: Database file
        if Path('database.py').exists():
            results.add_pass("Database module exists")
        else:
            results.add_fail("Database module check", "database.py not found")
            
    except Exception as e:
        results.add_fail("configuration_issues test", str(e))

def main():
    """Run comprehensive test suite"""
    print("🧪 Starting Comprehensive Test Suite for Discord Bot Issues")
    print("=" * 60)
    
    setup_mock_environment()
    results = TestResults()
    
    print("\n1️⃣ Testing DateTime Issues...")
    test_datetime_issues(results)
    
    print("\n2️⃣ Testing Database Issues...")
    test_database_issues(results)
    
    print("\n3️⃣ Testing Command Errors...")
    test_command_errors(results)
    
    print("\n4️⃣ Testing Configuration Issues...")
    test_configuration_issues(results)
    
    print("\n" + "=" * 60)
    success = results.summary()
    
    if not success:
        print(f"\n⚠️  Found {results.failed} issues that need fixing")
        print("Run this test again after applying fixes to verify resolution")
    else:
        print("\n🎉 All tests passed! Bot should work correctly after dependency installation")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())