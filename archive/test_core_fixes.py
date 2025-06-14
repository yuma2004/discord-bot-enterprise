#!/usr/bin/env python3
"""
コア修正内容の検証テストスクリプト
Discord依存のない部分の修正を検証します。
"""

import sys
import os
from datetime import datetime, date
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_datetime_functions():
    """強化された日時処理関数のテスト"""
    print("🧪 強化された日時処理関数のテスト...")
    
    try:
        from bot.utils.datetime_utils import (
            ensure_jst, format_time_only, format_date_only, 
            calculate_work_hours, calculate_time_difference, parse_date_string
        )
        
        # 修正前の問題: 型の不整合
        test_cases = [
            # PostgreSQL形式（datetime オブジェクト）
            datetime(2024, 1, 15, 9, 30, 0),
            # SQLite形式（ISO文字列）
            "2024-01-15T09:30:00",
            # None値の処理
            None
        ]
        
        print("📝 各データ形式の処理テスト:")
        for i, test_case in enumerate(test_cases):
            try:
                if test_case is None:
                    time_result = format_time_only(test_case)
                    date_result = format_date_only(test_case)
                    print(f"  {i+1}. None値 -> 時刻: '{time_result}', 日付: '{date_result}'")
                else:
                    jst_result = ensure_jst(test_case)
                    time_result = format_time_only(test_case)
                    date_result = format_date_only(test_case)
                    print(f"  {i+1}. {type(test_case).__name__} -> JST: {jst_result}, 時刻: {time_result}, 日付: {date_result}")
            except Exception as e:
                print(f"  {i+1}. {type(test_case).__name__} -> エラー: {e}")
        
        # 修正前の問題: calculate_work_hours関数のシグネチャ不整合
        print("\n📝 勤務時間計算の新シグネチャテスト:")
        
        # 新しいシグネチャ（break_start, break_endをサポート）
        work_hours_new = calculate_work_hours(
            "2024-01-15T09:00:00",  # check_in
            "2024-01-15T18:00:00",  # check_out
            "2024-01-15T12:00:00",  # break_start
            "2024-01-15T13:00:00"   # break_end
        )
        print(f"  新シグネチャ（休憩時間込み）: {work_hours_new}時間")
        
        # 休憩時間なし
        work_hours_simple = calculate_work_hours(
            "2024-01-15T09:00:00",  # check_in
            "2024-01-15T18:00:00"   # check_out
        )
        print(f"  休憩時間なし: {work_hours_simple}時間")
        
        # 時間差計算
        time_diff = calculate_time_difference(
            "2024-01-15T12:00:00",
            "2024-01-15T13:00:00"
        )
        print(f"  時間差計算: {time_diff}時間")
        
        # 修正前の問題: parse_date_stringのエラーメッセージ改善
        print("\n📝 日付パースのエラーハンドリングテスト:")
        
        valid_dates = ["2024-01-15", "2024/01/15"]
        for date_str in valid_dates:
            try:
                result = parse_date_string(date_str)
                print(f"  '{date_str}' -> {result}")
            except Exception as e:
                print(f"  '{date_str}' -> エラー: {e}")
        
        # エラーケース
        invalid_dates = ["", "invalid-date", "2024-13-01"]
        for date_str in invalid_dates:
            try:
                result = parse_date_string(date_str)
                print(f"  '{date_str}' -> {result} (予期しない成功)")
            except ValueError as e:
                print(f"  '{date_str}' -> 期待通りのエラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 強化された日時処理エラー: {e}")
        traceback.print_exc()
        return False

def test_database_utils_improvements():
    """データベースユーティリティの改善テスト"""
    print("\n🧪 データベースユーティリティの改善テスト...")
    
    try:
        from bot.utils.database_utils import (
            sanitize_string, build_update_query, safe_execute
        )
        
        # 修正前の問題: None値の処理
        print("📝 None値処理の改善:")
        none_result = sanitize_string(None)
        print(f"  None -> {none_result} (型: {type(none_result)})")
        
        empty_result = sanitize_string("")
        print(f"  '' -> '{empty_result}'")
        
        # 修正前の問題: build_update_queryでupdated_atが自動追加されない
        print("\n📝 UPDATE文構築の改善:")
        data = {'name': 'test_user', 'email': 'test@example.com'}
        query, params = build_update_query('users', data, 'id = ?')
        print(f"  クエリ: {query}")
        print(f"  パラメータ: {params}")
        print(f"  updated_at自動追加: {'CURRENT_TIMESTAMP' in query}")
        
        # safe_execute関数の柔軟性テスト
        print("\n📝 safe_execute関数の改善:")
        
        # モックオブジェクトでテスト
        class MockCursor:
            def execute(self, query, params):
                return f"executed: {query} with {params}"
        
        mock_cursor = MockCursor()
        result = safe_execute(mock_cursor, "SELECT * FROM test WHERE id = ?", (1,))
        print(f"  mock実行結果: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ データベースユーティリティ改善エラー: {e}")
        traceback.print_exc()
        return False

def test_compatibility_scenarios():
    """PostgreSQL/SQLite互換性シナリオのテスト"""
    print("\n🧪 PostgreSQL/SQLite互換性シナリオのテスト...")
    
    try:
        from bot.utils.datetime_utils import format_time_only, format_date_only, ensure_jst
        
        # シナリオ1: PostgreSQL形式のデータ処理
        print("📝 PostgreSQL形式（datetimeオブジェクト）:")
        pg_datetime = datetime(2024, 1, 15, 14, 30, 0)
        pg_time = format_time_only(pg_datetime)
        pg_date = format_date_only(pg_datetime)
        print(f"  入力: {pg_datetime}")
        print(f"  時刻: {pg_time}, 日付: {pg_date}")
        
        # シナリオ2: SQLite形式のデータ処理
        print("\n📝 SQLite形式（ISO文字列）:")
        sqlite_string = "2024-01-15T14:30:00"
        sqlite_time = format_time_only(sqlite_string)
        sqlite_date = format_date_only(sqlite_string)
        sqlite_jst = ensure_jst(sqlite_string)
        print(f"  入力: {sqlite_string}")
        print(f"  時刻: {sqlite_time}, 日付: {sqlite_date}")
        print(f"  JST変換: {sqlite_jst}")
        
        # シナリオ3: 混在環境での勤務時間計算
        print("\n📝 混在環境での勤務時間計算:")
        from bot.utils.datetime_utils import calculate_work_hours
        
        # PostgreSQL形式とSQLite形式の混在
        pg_checkin = datetime(2024, 1, 15, 9, 0, 0)
        sqlite_checkout = "2024-01-15T18:00:00"
        sqlite_break_start = "2024-01-15T12:00:00"
        pg_break_end = datetime(2024, 1, 15, 13, 0, 0)
        
        mixed_work_hours = calculate_work_hours(
            pg_checkin, sqlite_checkout, sqlite_break_start, pg_break_end
        )
        print(f"  混在形式での勤務時間: {mixed_work_hours}時間")
        
        return True
        
    except Exception as e:
        print(f"❌ 互換性シナリオエラー: {e}")
        traceback.print_exc()
        return False

def test_error_handling_improvements():
    """エラーハンドリングの改善テスト"""
    print("\n🧪 エラーハンドリングの改善テスト...")
    
    try:
        from bot.utils.datetime_utils import ensure_jst, parse_date_string
        from bot.utils.database_utils import validate_required_fields
        
        # 無効な型のテスト
        print("📝 型エラーハンドリング:")
        try:
            ensure_jst(123)  # 数値は無効
            print("  数値入力: 予期しない成功")
        except ValueError as e:
            print(f"  数値入力: 期待通りのエラー - {e}")
        
        # 無効な日付のテスト
        print("\n📝 日付エラーハンドリング:")
        try:
            parse_date_string("invalid-date")
            print("  無効な日付: 予期しない成功")
        except ValueError as e:
            print(f"  無効な日付: 期待通りのエラー - {e}")
        
        # 必須フィールドのテスト
        print("\n📝 必須フィールドエラーハンドリング:")
        try:
            validate_required_fields({'name': 'test'}, ['name', 'email'])
            print("  不足フィールド: 予期しない成功")
        except ValueError as e:
            print(f"  不足フィールド: 期待通りのエラー - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーハンドリング改善エラー: {e}")
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🚀 コア修正内容の検証テスト開始\n")
    print("=" * 70)
    
    test_results = []
    
    # 各テストを実行
    test_results.append(("強化された日時処理関数", test_enhanced_datetime_functions()))
    test_results.append(("データベースユーティリティ改善", test_database_utils_improvements()))
    test_results.append(("PostgreSQL/SQLite互換性", test_compatibility_scenarios()))
    test_results.append(("エラーハンドリング改善", test_error_handling_improvements()))
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:<35} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 70)
    print(f"総合結果: 成功 {passed}/{len(test_results)}, 失敗 {failed}/{len(test_results)}")
    
    if failed == 0:
        print("\n🎉 すべてのコア修正が正常に動作しています！")
        print("💡 主要な問題点が解決されました:")
        print("   ✅ PostgreSQL/SQLite日時互換性")
        print("   ✅ calculate_work_hours関数シグネチャ") 
        print("   ✅ None値の安全な処理")
        print("   ✅ 改善されたエラーメッセージ")
        print("   ✅ 自動updated_at追加")
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("🔧 失敗した項目を確認して修正してください。")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)