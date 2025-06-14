#!/usr/bin/env python3
"""
修正内容の検証テストスクリプト
主要な修正項目が正常に動作することを確認します。
"""

import sys
import os
from datetime import datetime, date
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_datetime_utils():
    """日時ユーティリティの修正確認"""
    print("🧪 日時ユーティリティのテスト...")
    
    try:
        from bot.utils.datetime_utils import (
            now_jst, today_jst, ensure_jst, format_time_only, 
            format_date_only, calculate_work_hours, calculate_time_difference
        )
        
        # 基本的な日時取得
        current_jst = now_jst()
        today = today_jst()
        print(f"✅ JST現在時刻: {current_jst}")
        print(f"✅ JST今日の日付: {today}")
        
        # 文字列からdatetimeへの変換
        test_str = "2024-01-15T09:30:00"
        jst_dt = ensure_jst(test_str)
        print(f"✅ 文字列変換: {test_str} -> {jst_dt}")
        
        # フォーマット機能
        time_str = format_time_only(jst_dt)
        date_str = format_date_only(jst_dt)
        print(f"✅ 時刻フォーマット: {time_str}")
        print(f"✅ 日付フォーマット: {date_str}")
        
        # 勤務時間計算（新しいシグネチャ）
        check_in = "2024-01-15T09:00:00"
        check_out = "2024-01-15T18:00:00"
        break_start = "2024-01-15T12:00:00"
        break_end = "2024-01-15T13:00:00"
        
        work_hours = calculate_work_hours(check_in, check_out, break_start, break_end)
        break_hours = calculate_time_difference(break_start, break_end)
        
        print(f"✅ 勤務時間計算: {work_hours}時間")
        print(f"✅ 休憩時間計算: {break_hours}時間")
        
        return True
        
    except Exception as e:
        print(f"❌ 日時ユーティリティエラー: {e}")
        traceback.print_exc()
        return False

def test_database_utils():
    """データベースユーティリティの修正確認"""
    print("\n🧪 データベースユーティリティのテスト...")
    
    try:
        from bot.utils.database_utils import (
            sanitize_string, build_update_query, validate_required_fields,
            DatabaseError, RecordNotFoundError, DuplicateRecordError
        )
        
        # 文字列サニタイズ
        test_string = "  test string  "
        sanitized = sanitize_string(test_string, max_length=10)
        print(f"✅ 文字列サニタイズ: '{test_string}' -> '{sanitized}'")
        
        # None値の処理
        none_result = sanitize_string(None)
        print(f"✅ None処理: None -> {none_result}")
        
        # UPDATE文構築
        data = {'name': 'test', 'value': 123}
        query, params = build_update_query('test_table', data, 'id = ?')
        print(f"✅ UPDATE文構築: {query}")
        print(f"✅ パラメータ: {params}")
        
        # 必須フィールド検証
        valid_data = {'name': 'test', 'value': 123}
        validate_required_fields(valid_data, ['name', 'value'])
        print("✅ 必須フィールド検証: 成功")
        
        # エラークラスの確認
        print(f"✅ エラークラス: {DatabaseError.__name__}, {RecordNotFoundError.__name__}, {DuplicateRecordError.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ データベースユーティリティエラー: {e}")
        traceback.print_exc()
        return False

def test_admin_command_import():
    """admin.pyの修正確認"""
    print("\n🧪 adminコマンドの修正確認...")
    
    try:
        # import時にエラーが出ないか確認
        import bot.commands.admin
        print("✅ admin.py インポート成功")
        
        # now_jstが正しくインポートされているか確認
        from bot.commands.admin import now_jst
        current_time = now_jst()
        print(f"✅ now_jst関数: {current_time}")
        
        return True
        
    except Exception as e:
        print(f"❌ adminコマンドエラー: {e}")
        traceback.print_exc()
        return False

def test_attendance_command_import():
    """attendance.pyの修正確認"""
    print("\n🧪 attendanceコマンドの修正確認...")
    
    try:
        # import時にエラーが出ないか確認
        import bot.commands.attendance
        print("✅ attendance.py インポート成功")
        
        # 修正された関数がインポートされているか確認
        from bot.commands.attendance import calculate_time_difference
        result = calculate_time_difference("2024-01-15T12:00:00", "2024-01-15T13:00:00")
        print(f"✅ calculate_time_difference関数: {result}時間")
        
        return True
        
    except Exception as e:
        print(f"❌ attendanceコマンドエラー: {e}")
        traceback.print_exc()
        return False

def test_task_manager_import():
    """task_manager.pyの修正確認"""
    print("\n🧪 task_managerコマンドの修正確認...")
    
    try:
        # import時にエラーが出ないか確認
        import bot.commands.task_manager
        print("✅ task_manager.py インポート成功")
        
        # parse_date_stringが正しくインポートされているか確認
        from bot.commands.task_manager import parse_date_string
        test_date = parse_date_string("2024-01-15")
        print(f"✅ parse_date_string関数: {test_date}")
        
        return True
        
    except Exception as e:
        print(f"❌ task_managerコマンドエラー: {e}")
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🚀 修正内容の検証テスト開始\n")
    print("=" * 60)
    
    test_results = []
    
    # 各テストを実行
    test_results.append(("日時ユーティリティ", test_datetime_utils()))
    test_results.append(("データベースユーティリティ", test_database_utils()))
    test_results.append(("adminコマンド", test_admin_command_import()))
    test_results.append(("attendanceコマンド", test_attendance_command_import()))
    test_results.append(("task_managerコマンド", test_task_manager_import()))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:<25} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"総合結果: 成功 {passed}/{len(test_results)}, 失敗 {failed}/{len(test_results)}")
    
    if failed == 0:
        print("🎉 すべてのテストが成功しました！")
        print("💡 修正内容が正常に動作しています。")
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("🔧 失敗した項目を確認して修正してください。")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)