#!/usr/bin/env python3
"""
包括的テストランナー
全てのテストを効率的に実行し、詳細なレポートを生成
"""

import unittest
import sys
import os
import time
from io import StringIO
import json
from datetime import datetime

# テスト用環境変数を設定
os.environ.setdefault('DISCORD_TOKEN', 'test_token')
os.environ.setdefault('DISCORD_GUILD_ID', '123456789')
os.environ.setdefault('DATABASE_URL', 'test_runner.db')
os.environ.setdefault('ENVIRONMENT', 'test')

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class ColoredTestResult(unittest.TextTestResult):
    """カラー出力付きテスト結果クラス"""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
        self.start_time = None
        self.colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
        # 簡単な出力（verbosityはparentから取得）
        if hasattr(self, 'verbosity') and self.verbosity > 1:
            self.stream.write(f"{self.colors['blue']}実行中: {test._testMethodName}{self.colors['reset']} ... ")
            self.stream.flush()
    
    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.time() - self.start_time
        self.test_results.append({
            'test': str(test),
            'status': 'SUCCESS',
            'duration': duration,
            'message': None
        })
        # 成功時は簡潔な出力のみ
        pass
    
    def addError(self, test, err):
        super().addError(test, err)
        duration = time.time() - self.start_time
        self.test_results.append({
            'test': str(test),
            'status': 'ERROR',
            'duration': duration,
            'message': self._exc_info_to_string(err, test)
        })
        # エラー時は別途表示
        pass
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.time() - self.start_time
        self.test_results.append({
            'test': str(test),
            'status': 'FAILURE',
            'duration': duration,
            'message': self._exc_info_to_string(err, test)
        })
        # 失敗時は別途表示
        pass
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        duration = time.time() - self.start_time
        self.test_results.append({
            'test': str(test),
            'status': 'SKIP',
            'duration': duration,
            'message': reason
        })
        # スキップ時は別途表示
        pass


class TestSuiteRunner:
    """テストスイート実行クラス"""
    
    def __init__(self):
        self.test_modules = [
            'test_basic',
            'test_attendance', 
            'test_database_integration',
            'test_error_handling',
            'test_performance'
        ]
        self.results = {}
        self.total_start_time = None
    
    def run_module_tests(self, module_name, verbosity=2):
        """特定のモジュールのテストを実行"""
        print(f"\n{'='*60}")
        print(f"🧪 {module_name.upper()} テスト実行中...")
        print(f"{'='*60}")
        
        try:
            # モジュールをインポート
            module = __import__(f'tests.{module_name}', fromlist=[''])
            
            # テストスイートを作成
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            
            # カスタムテストランナーで実行
            stream = StringIO()
            runner = unittest.TextTestRunner(
                stream=stream,
                verbosity=verbosity,
                resultclass=ColoredTestResult
            )
            
            start_time = time.time()
            result = runner.run(suite)
            end_time = time.time()
            
            # 結果を記録
            self.results[module_name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'success_count': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                'duration': end_time - start_time,
                'details': getattr(result, 'test_results', []),
                'output': stream.getvalue()
            }
            
            # 結果表示
            self._print_module_summary(module_name, self.results[module_name])
            
            return result.wasSuccessful()
            
        except ImportError as e:
            print(f"❌ モジュール {module_name} のインポートに失敗: {e}")
            self.results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success_count': 0,
                'duration': 0,
                'details': [],
                'output': f"Import Error: {e}"
            }
            return False
        except Exception as e:
            print(f"❌ モジュール {module_name} でエラー発生: {e}")
            self.results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success_count': 0,
                'duration': 0,
                'details': [],
                'output': f"Error: {e}"
            }
            return False
    
    def _print_module_summary(self, module_name, result):
        """モジュール結果のサマリーを表示"""
        total_tests = result['tests_run']
        success_count = result['success_count']
        failure_count = result['failures']
        error_count = result['errors']
        skip_count = result['skipped']
        duration = result['duration']
        
        print(f"\n📊 {module_name} テスト結果:")
        print(f"   ✅ 成功: {success_count}/{total_tests}")
        if failure_count > 0:
            print(f"   ❌ 失敗: {failure_count}")
        if error_count > 0:
            print(f"   🔥 エラー: {error_count}")
        if skip_count > 0:
            print(f"   ⚠️  スキップ: {skip_count}")
        print(f"   ⏱️  実行時間: {duration:.2f}秒")
        
        if total_tests > 0:
            success_rate = (success_count / total_tests) * 100
            if success_rate == 100:
                print(f"   🎉 成功率: {success_rate:.1f}% (完璧!)")
            elif success_rate >= 90:
                print(f"   😊 成功率: {success_rate:.1f}% (優秀)")
            elif success_rate >= 80:
                print(f"   😐 成功率: {success_rate:.1f}% (普通)")
            else:
                print(f"   😞 成功率: {success_rate:.1f}% (要改善)")
    
    def run_all_tests(self, verbosity=2, save_report=True):
        """全てのテストを実行"""
        print("🚀 包括的テストスイート実行開始")
        print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.total_start_time = time.time()
        
        successful_modules = 0
        total_modules = len(self.test_modules)
        
        # 各モジュールのテストを実行
        for module_name in self.test_modules:
            success = self.run_module_tests(module_name, verbosity)
            if success:
                successful_modules += 1
        
        total_end_time = time.time()
        total_duration = total_end_time - self.total_start_time
        
        # 全体結果の表示
        self._print_overall_summary(successful_modules, total_modules, total_duration)
        
        # レポート保存
        if save_report:
            self._save_report()
        
        return successful_modules == total_modules
    
    def _print_overall_summary(self, successful_modules, total_modules, total_duration):
        """全体結果のサマリーを表示"""
        print(f"\n{'='*80}")
        print(f"🏁 包括的テスト実行完了")
        print(f"{'='*80}")
        
        # 統計計算
        total_tests = sum(r['tests_run'] for r in self.results.values())
        total_success = sum(r['success_count'] for r in self.results.values())
        total_failures = sum(r['failures'] for r in self.results.values())
        total_errors = sum(r['errors'] for r in self.results.values())
        total_skipped = sum(r['skipped'] for r in self.results.values())
        
        print(f"📈 全体統計:")
        print(f"   🎯 モジュール成功率: {successful_modules}/{total_modules} ({successful_modules/total_modules*100:.1f}%)")
        print(f"   📊 総テスト数: {total_tests}")
        print(f"   ✅ 成功: {total_success}")
        print(f"   ❌ 失敗: {total_failures}")
        print(f"   🔥 エラー: {total_errors}")
        print(f"   ⚠️  スキップ: {total_skipped}")
        print(f"   ⏱️  総実行時間: {total_duration:.2f}秒")
        
        if total_tests > 0:
            overall_success_rate = (total_success / total_tests) * 100
            print(f"   🎯 全体成功率: {overall_success_rate:.1f}%")
            
            if overall_success_rate == 100:
                print(f"   🎉 結果: 完璧! 全てのテストが成功しました!")
            elif overall_success_rate >= 95:
                print(f"   😊 結果: 優秀! ほぼ全てのテストが成功しました!")
            elif overall_success_rate >= 80:
                print(f"   😐 結果: 普通です。いくつかの問題があります。")
            else:
                print(f"   😞 結果: 要改善。多くの問題があります。")
        
        # パフォーマンス指標
        avg_test_duration = total_duration / total_tests if total_tests > 0 else 0
        tests_per_second = total_tests / total_duration if total_duration > 0 else 0
        
        print(f"\n⚡ パフォーマンス指標:")
        print(f"   平均テスト実行時間: {avg_test_duration:.4f}秒")
        print(f"   テスト実行速度: {tests_per_second:.1f}テスト/秒")
        
        # 問題があるモジュールをハイライト
        problematic_modules = []
        for module_name, result in self.results.items():
            if result['failures'] > 0 or result['errors'] > 0:
                problematic_modules.append(module_name)
        
        if problematic_modules:
            print(f"\n⚠️  問題があるモジュール:")
            for module in problematic_modules:
                result = self.results[module]
                print(f"   - {module}: {result['failures']}失敗, {result['errors']}エラー")
    
    def _save_report(self):
        """テスト結果をJSON形式で保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': time.time() - self.total_start_time,
            'results': self.results,
            'summary': {
                'total_tests': sum(r['tests_run'] for r in self.results.values()),
                'total_success': sum(r['success_count'] for r in self.results.values()),
                'total_failures': sum(r['failures'] for r in self.results.values()),
                'total_errors': sum(r['errors'] for r in self.results.values()),
                'total_skipped': sum(r['skipped'] for r in self.results.values())
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 テストレポートを保存しました: {filename}")
        except Exception as e:
            print(f"\n❌ レポート保存に失敗: {e}")
    
    def run_specific_categories(self, categories=None):
        """特定のカテゴリのテストのみ実行"""
        if categories is None:
            categories = ['basic', 'integration', 'performance']
        
        category_mapping = {
            'basic': ['test_basic'],
            'attendance': ['test_attendance'],
            'integration': ['test_database_integration'],
            'error': ['test_error_handling'],
            'performance': ['test_performance']
        }
        
        modules_to_run = []
        for category in categories:
            if category in category_mapping:
                modules_to_run.extend(category_mapping[category])
        
        # 重複除去
        modules_to_run = list(set(modules_to_run))
        
        print(f"🎯 特定カテゴリのテスト実行: {categories}")
        print(f"実行予定モジュール: {modules_to_run}")
        
        self.test_modules = modules_to_run
        return self.run_all_tests()


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='包括的テストランナー')
    parser.add_argument('--verbosity', '-v', type=int, default=2, 
                       help='出力の詳細レベル (0-2)')
    parser.add_argument('--no-report', action='store_true',
                       help='レポートファイルを保存しない')
    parser.add_argument('--categories', nargs='+', 
                       choices=['basic', 'attendance', 'integration', 'error', 'performance'],
                       help='実行するテストカテゴリを指定')
    parser.add_argument('--modules', nargs='+',
                       help='実行するテストモジュールを直接指定')
    
    args = parser.parse_args()
    
    runner = TestSuiteRunner()
    
    # モジュール直接指定の場合
    if args.modules:
        runner.test_modules = args.modules
        success = runner.run_all_tests(args.verbosity, not args.no_report)
    # カテゴリ指定の場合
    elif args.categories:
        success = runner.run_specific_categories(args.categories)
    # 全テスト実行
    else:
        success = runner.run_all_tests(args.verbosity, not args.no_report)
    
    # 終了コード設定
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 