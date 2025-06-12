"""
リファクタリングしたコードのテスト実行スクリプト

このスクリプトは、リファクタリング後のコードの全テストを実行し、
詳細なレポートを生成します。
"""

import unittest
import sys
import os
import json
import time
from datetime import datetime
import logging

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResultWithDetails(unittest.TestResult):
    """詳細な情報を収集するカスタムTestResult"""
    
    def __init__(self):
        super().__init__()
        self.test_details = []
        self.start_time = None
        self.end_time = None
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
        logger.info(f"テスト開始: {test}")
    
    def stopTest(self, test):
        super().stopTest(test)
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        status = 'success'
        error_message = None
        
        if test in [e[0] for e in self.errors]:
            status = 'error'
            error_message = next(e[1] for e in self.errors if e[0] == test)
        elif test in [f[0] for f in self.failures]:
            status = 'failure'
            error_message = next(f[1] for f in self.failures if f[0] == test)
        elif test in [s[0] for s in self.skipped]:
            status = 'skipped'
            error_message = next(s[1] for s in self.skipped if s[0] == test)
        
        self.test_details.append({
            'test_name': str(test),
            'status': status,
            'duration': duration,
            'error_message': error_message
        })
        
        logger.info(f"テスト終了: {test} - {status} ({duration:.3f}秒)")


def discover_and_run_tests():
    """テストを検出して実行"""
    # テストローダーを作成
    loader = unittest.TestLoader()
    
    # テストスイートを作成
    suite = unittest.TestSuite()
    
    # tests/test_refactored_code.py のテストを追加
    try:
        from test_refactored_code import (
            TestDateTimeUtils,
            TestDatabaseUtils,
            TestDatabaseIntegration,
            TestCommandsIntegration
        )
        
        suite.addTests(loader.loadTestsFromTestCase(TestDateTimeUtils))
        suite.addTests(loader.loadTestsFromTestCase(TestDatabaseUtils))
        suite.addTests(loader.loadTestsFromTestCase(TestDatabaseIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestCommandsIntegration))
        
        logger.info("リファクタリングテストをロードしました")
    except ImportError as e:
        logger.error(f"テストのインポートエラー: {e}")
        return None
    
    # 既存のテストも追加（エラーが出ないもののみ）
    try:
        from test_basic import TestBasicFunctions
        suite.addTests(loader.loadTestsFromTestCase(TestBasicFunctions))
        logger.info("基本機能テストをロードしました")
    except Exception as e:
        logger.warning(f"基本機能テストのロードをスキップ: {e}")
    
    try:
        from test_attendance import TestAttendanceSystem
        suite.addTests(loader.loadTestsFromTestCase(TestAttendanceSystem))
        logger.info("出退勤テストをロードしました")
    except Exception as e:
        logger.warning(f"出退勤テストのロードをスキップ: {e}")
    
    try:
        from test_database_integration import TestDatabaseIntegration as OldDBTest
        suite.addTests(loader.loadTestsFromTestCase(OldDBTest))
        logger.info("既存のデータベーステストをロードしました")
    except Exception as e:
        logger.warning(f"既存のデータベーステストのロードをスキップ: {e}")
    
    # カスタムResultでテストを実行
    result = TestResultWithDetails()
    start_time = time.time()
    suite.run(result)
    end_time = time.time()
    
    return result, end_time - start_time


def generate_report(result, total_duration):
    """テスト結果のレポートを生成"""
    total_tests = result.testsRun
    success_count = total_tests - len(result.errors) - len(result.failures) - len(result.skipped)
    
    report = {
        'test_run_date': datetime.now().isoformat(),
        'total_tests': total_tests,
        'success_count': success_count,
        'failure_count': len(result.failures),
        'error_count': len(result.errors),
        'skipped_count': len(result.skipped),
        'success_rate': (success_count / total_tests * 100) if total_tests > 0 else 0,
        'total_duration': total_duration,
        'test_details': result.test_details
    }
    
    # コンソールにサマリーを表示
    print("\n" + "="*80)
    print("リファクタリングコード テスト結果サマリー")
    print("="*80)
    print(f"実行日時: {report['test_run_date']}")
    print(f"総テスト数: {report['total_tests']}")
    print(f"成功: {report['success_count']} ({report['success_rate']:.1f}%)")
    print(f"失敗: {report['failure_count']}")
    print(f"エラー: {report['error_count']}")
    print(f"スキップ: {report['skipped_count']}")
    print(f"実行時間: {report['total_duration']:.2f}秒")
    print("="*80)
    
    # 失敗・エラーの詳細を表示
    if result.failures or result.errors:
        print("\n失敗・エラーの詳細:")
        print("-"*80)
        
        for test, error in result.failures:
            print(f"\n[FAILURE] {test}")
            print(error)
            print("-"*40)
        
        for test, error in result.errors:
            print(f"\n[ERROR] {test}")
            print(error)
            print("-"*40)
    
    # JSONファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"refactored_test_report_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n詳細レポートを保存しました: {filename}")
    
    return report


def main():
    """メイン実行関数"""
    print("リファクタリングしたコードのテストを開始します...")
    
    # 環境変数設定（テスト用）
    os.environ['DISCORD_TOKEN'] = 'test_token'
    os.environ['DISCORD_GUILD_ID'] = '123456789'
    os.environ['TIMEZONE'] = 'Asia/Tokyo'
    
    try:
        # テストを実行
        result, duration = discover_and_run_tests()
        
        if result:
            # レポートを生成
            report = generate_report(result, duration)
            
            # 終了コードを設定
            if result.failures or result.errors:
                sys.exit(1)
            else:
                sys.exit(0)
        else:
            print("テストの実行に失敗しました")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 