#!/usr/bin/env python3
"""
Installation Verification Script
Checks if all required dependencies are properly installed
"""

import sys
import os
import subprocess
from pathlib import Path

class InstallationChecker:
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "errors": []}
    
    def check_package(self, package_name, import_name=None):
        """Check if a Python package is installed"""
        if import_name is None:
            import_name = package_name
        
        try:
            __import__(import_name)
            self.results["passed"] += 1
            print(f"✅ {package_name}")
            return True
        except ImportError:
            self.results["failed"] += 1
            self.results["errors"].append(f"Missing package: {package_name}")
            print(f"❌ {package_name} - Not installed")
            return False
    
    def check_file_exists(self, file_path, description):
        """Check if a required file exists"""
        if Path(file_path).exists():
            self.results["passed"] += 1
            print(f"✅ {description}")
            return True
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"Missing file: {file_path}")
            print(f"❌ {description} - File not found: {file_path}")
            return False
    
    def check_environment_variable(self, var_name):
        """Check if environment variable is set"""
        if os.getenv(var_name):
            self.results["passed"] += 1
            print(f"✅ Environment variable: {var_name}")
            return True
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"Missing environment variable: {var_name}")
            print(f"❌ Environment variable: {var_name} - Not set")
            return False
    
    def summary(self):
        """Print summary and return success status"""
        total = self.results["passed"] + self.results["failed"]
        print(f"\n📊 VERIFICATION SUMMARY:")
        print(f"Total checks: {total} | Passed: {self.results['passed']} | Failed: {self.results['failed']}")
        
        if self.results["errors"]:
            print(f"\n❌ ISSUES FOUND ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        return self.results["failed"] == 0

def main():
    """Run installation verification"""
    print("🔍 Discord Bot Installation Verification")
    print("=" * 50)
    
    checker = InstallationChecker()
    
    print("\n1️⃣ Checking Required Python Packages...")
    # Critical packages
    checker.check_package("discord.py", "discord")
    checker.check_package("python-dotenv", "dotenv")
    checker.check_package("pytz")
    
    # Optional but recommended packages
    checker.check_package("Flask", "flask")
    checker.check_package("aiohttp")
    checker.check_package("psycopg2-binary", "psycopg2")
    
    print("\n2️⃣ Checking Core Application Files...")
    checker.check_file_exists("main.py", "Main application file")
    checker.check_file_exists("config.py", "Configuration file")
    checker.check_file_exists("database.py", "Database module")
    checker.check_file_exists(".env", "Environment configuration")
    checker.check_file_exists("requirements.txt", "Requirements file")
    
    print("\n3️⃣ Checking Bot Command Modules...")
    command_files = [
        ("bot/commands/admin.py", "Admin commands"),
        ("bot/commands/attendance.py", "Attendance commands"),
        ("bot/commands/task_manager.py", "Task manager commands"),
        ("bot/commands/calendar.py", "Calendar commands"),
        ("bot/commands/help.py", "Help commands")
    ]
    
    for file_path, description in command_files:
        checker.check_file_exists(file_path, description)
    
    print("\n4️⃣ Checking Utility Modules...")
    checker.check_file_exists("bot/utils/datetime_utils.py", "DateTime utilities")
    checker.check_file_exists("bot/utils/database_utils.py", "Database utilities")
    
    print("\n5️⃣ Checking Environment Variables...")
    required_env_vars = ["DISCORD_TOKEN", "GUILD_ID", "DATABASE_URL", "TIMEZONE"]
    for var in required_env_vars:
        checker.check_environment_variable(var)
    
    print("\n6️⃣ Testing Module Imports...")
    try:
        # Test critical imports that shouldn't fail
        import sqlite3
        checker.results["passed"] += 1
        print("✅ SQLite3 (built-in)")
        
        import datetime
        checker.results["passed"] += 1
        print("✅ DateTime (built-in)")
        
        import logging
        checker.results["passed"] += 1
        print("✅ Logging (built-in)")
        
    except Exception as e:
        checker.results["failed"] += 1
        checker.results["errors"].append(f"Built-in module import error: {e}")
        print(f"❌ Built-in modules - Error: {e}")
    
    print("\n" + "=" * 50)
    success = checker.summary()
    
    if not success:
        print(f"\n🚨 INSTALLATION INCOMPLETE")
        print("To install missing packages, run:")
        print("  pip install -r requirements.txt")
        print("\nTo set environment variables, check the .env file")
        return 1
    else:
        print("\n🎉 INSTALLATION COMPLETE!")
        print("All required dependencies are installed and configured.")
        print("You can now run the bot with: python main.py")
        return 0

if __name__ == "__main__":
    sys.exit(main())