#!/usr/bin/env python3
"""
Test script to verify all import issues are fixed
"""

import sys
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all critical imports that were failing"""
    results = {"passed": 0, "failed": 0, "errors": []}
    
    def test_import(description, import_func):
        try:
            import_func()
            results["passed"] += 1
            print(f"✅ {description}")
            return True
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{description}: {e}")
            print(f"❌ {description}: {e}")
            return False
    
    print("🧪 Testing Import Fixes")
    print("=" * 40)
    
    # Test 1: Config import (should work without dotenv)
    test_import("Config import", lambda: __import__('config'))
    
    # Test 2: Core logging import
    test_import("Core logging import", lambda: __import__('core.logging'))
    
    # Test 3: Core database import
    test_import("Core database import", lambda: __import__('core.database'))
    
    # Test 4: Database repositories import
    def test_database_repos():
        from database import user_repo, task_repo, attendance_repo
        return user_repo is not None
    test_import("Database repositories import", test_database_repos)
    
    # Test 5: Bot utilities import
    test_import("DateTime utilities import", lambda: __import__('bot.utils.datetime_utils'))
    test_import("Database utilities import", lambda: __import__('bot.utils.database_utils'))
    
    # Test 6: Command modules import (should work now)
    def test_attendance_import():
        # Mock discord modules properly
        import types
        
        # Create mock discord module  
        mock_discord = types.ModuleType('discord')
        mock_discord.Embed = type('Embed', (), {})
        mock_discord.Color = type('Color', (), {
            'green': lambda: 0x00ff00,
            'red': lambda: 0xff0000, 
            'blue': lambda: 0x0000ff,
            'orange': lambda: 0xffa500,
            'gold': lambda: 0xffd700
        })
        mock_discord.ButtonStyle = type('ButtonStyle', (), {
            'green': 1,
            'red': 2,
            'secondary': 3
        })
        mock_discord.Intents = type('Intents', (), {
            'default': lambda: type('Instance', (), {'message_content': True, 'members': True})()
        })
        mock_discord.Activity = type('Activity', (), {})
        mock_discord.ActivityType = type('ActivityType', (), {'watching': 1})
        mock_discord.Interaction = type('Interaction', (), {})
        
        # Create mock ui module
        mock_ui = types.ModuleType('ui')
        mock_ui.View = type('View', (), {})
        mock_ui.button = lambda **kwargs: lambda f: f
        mock_ui.Button = type('Button', (), {})
        mock_discord.ui = mock_ui
        
        # Create mock ext module
        mock_ext = types.ModuleType('ext')
        mock_commands = types.ModuleType('commands')
        mock_commands.Cog = type('Cog', (), {})
        mock_commands.command = lambda **kwargs: lambda f: f
        mock_commands.group = lambda **kwargs: lambda f: f
        mock_commands.Context = type('Context', (), {})
        mock_commands.Bot = type('Bot', (), {})
        mock_commands.has_permissions = lambda **kwargs: lambda f: f
        mock_commands.CommandNotFound = type('CommandNotFound', (Exception,), {})
        mock_commands.MissingRequiredArgument = type('MissingRequiredArgument', (Exception,), {})
        mock_commands.BadArgument = type('BadArgument', (Exception,), {})
        mock_commands.CommandOnCooldown = type('CommandOnCooldown', (Exception,), {})
        mock_ext.commands = mock_commands
        mock_discord.ext = mock_ext
        
        # Register in sys.modules
        sys.modules['discord'] = mock_discord
        sys.modules['discord.ext'] = mock_ext
        sys.modules['discord.ext.commands'] = mock_commands
        sys.modules['discord.ui'] = mock_ui
        
        # Now try to import the attendance module
        import bot.commands.attendance
        return True
    
    test_import("Attendance command module import", test_attendance_import)
    
    # Test other command modules
    def test_admin_import():
        import bot.commands.admin
        return True
    test_import("Admin command module import", test_admin_import)
    
    def test_task_manager_import():
        import bot.commands.task_manager  
        return True
    test_import("Task manager command module import", test_task_manager_import)
    
    print("\n" + "=" * 40)
    total = results["passed"] + results["failed"]
    print(f"📊 IMPORT TEST SUMMARY:")
    print(f"Total: {total} | Passed: {results['passed']} | Failed: {results['failed']}")
    
    if results["errors"]:
        print(f"\n❌ REMAINING IMPORT ISSUES ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")
        return False
    else:
        print("\n🎉 ALL IMPORTS WORKING!")
        print("Command modules should now load correctly when discord.py is installed.")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)