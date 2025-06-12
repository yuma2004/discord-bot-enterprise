#!/usr/bin/env python3
"""
Import test script to verify all dependencies can be loaded
"""
import os
import sys

# Set up environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token_for_import_test'
os.environ['DISCORD_GUILD_ID'] = '123456789'
os.environ['DATABASE_URL'] = 'discord_bot.db'
os.environ['ENVIRONMENT'] = 'development'

def test_imports():
    """Test all imports used by main.py"""
    print("🔍 Testing imports used by main.py...")
    print("=" * 50)
    
    # Test standard library imports
    try:
        import asyncio
        import sys
        from pathlib import Path
        print("✅ Standard library imports: OK")
    except ImportError as e:
        print(f"❌ Standard library imports failed: {e}")
        return False
    
    # Test external dependencies
    external_deps = {
        'discord': 'Discord.py library',
        'dotenv': 'python-dotenv library',
        'flask': 'Flask web framework (optional)',
        'pytz': 'Python timezone library'
    }
    
    missing_deps = []
    for dep, desc in external_deps.items():
        try:
            __import__(dep)
            print(f"✅ {desc}: OK")
        except ImportError:
            print(f"❌ {desc}: MISSING")
            missing_deps.append(dep)
    
    # Test internal core modules
    core_modules = [
        ('config', 'Config'),
        ('core.database', 'db_manager, DB_TYPE'),
        ('core.logging', 'LoggerManager'),
        ('core.health_check', 'health_server')
    ]
    
    for module, items in core_modules:
        try:
            __import__(module)
            print(f"✅ {module} ({items}): OK")
        except ImportError as e:
            print(f"❌ {module} ({items}): {e}")
    
    # Test utility modules
    util_modules = [
        ('bot.utils.datetime_utils', 'DateTime utilities'),
        ('bot.utils.database_utils', 'Database utilities')
    ]
    
    for module, desc in util_modules:
        try:
            __import__(module)
            print(f"✅ {module} ({desc}): OK")
        except ImportError as e:
            print(f"❌ {module} ({desc}): {e}")
    
    # Test bot command modules (will fail without discord.py but we can check file existence)
    command_modules = [
        'bot.commands.task_manager',
        'bot.commands.attendance',
        'bot.commands.calendar',
        'bot.commands.admin',
        'bot.commands.help'
    ]
    
    print("\n📁 Checking bot command module files...")
    for module in command_modules:
        file_path = module.replace('.', '/') + '.py'
        if os.path.exists(file_path):
            print(f"✅ {module}: File exists")
        else:
            print(f"❌ {module}: File missing")
    
    print("\n" + "=" * 50)
    if missing_deps:
        print(f"⚠️  Missing external dependencies: {', '.join(missing_deps)}")
        print("📦 Install with: pip install " + " ".join(missing_deps))
        print("📋 Or use: pip install -r requirements.txt")
    else:
        print("🎉 All external dependencies are available!")
    
    return len(missing_deps) == 0

def main():
    """Main test function"""
    print("🚀 Discord Bot Import Test")
    print("=" * 50)
    
    all_good = test_imports()
    
    if all_good:
        print("\n✅ All imports should work correctly!")
        print("🤖 The bot should be able to start (if Discord token is valid)")
    else:
        print("\n❌ Some dependencies are missing")
        print("🔧 Install missing packages before running the bot")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())