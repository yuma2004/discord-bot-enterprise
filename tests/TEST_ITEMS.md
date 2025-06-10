# Discord Bot Enterprise - テスト項目仕様書

## 📋 **テスト概要**

Discord Bot Enterpriseの出退勤機能における包括的なテスト項目を定義しています。
PostgreSQLとSQLiteの互換性、日時処理、エラーハンドリング、ビジネスロジックをカバーします。

---

## 🎯 **テストカテゴリー**

### 1. **日時処理互換性テスト** (`TestDateTimeCompatibility`)

#### 目的
PostgreSQLとSQLiteの日時データ形式の違いに対する処理の互換性を検証

#### テスト項目

| テスト名 | 目的 | 入力値 | 期待結果 |
|---------|------|--------|----------|
| `test_datetime_object_handling` | PostgreSQL形式（datetimeオブジェクト）の処理 | `datetime(2025, 6, 10, 9, 0, 0)` | 正常にdatetimeオブジェクトとして処理される |
| `test_string_datetime_handling` | SQLite形式（ISO文字列）の処理 | `"2025-06-10T09:00:00"` | 文字列からdatetimeオブジェクトに変換される |

#### 重要性
- PostgreSQLではdatetimeオブジェクトで返される
- SQLiteでは文字列で返される
- 両方に対応する統一的な処理が必要

---

### 2. **データベース互換性テスト** (`TestDatabaseCompatibility`)

#### 目的
データベースモジュールのインポートと切り替えが正常に動作することを検証

#### テスト項目

| テスト名 | 目的 | 検証内容 | 期待結果 |
|---------|------|----------|----------|
| `test_postgresql_imports` | PostgreSQLモジュールのインポート | `database_postgres`から必要クラスを取得 | ImportErrorが発生しない |
| `test_sqlite_fallback` | SQLiteフォールバック | `database`から必要クラスを取得 | ImportErrorが発生しない |

#### 重要性
- 環境に応じて適切なデータベースモジュールが選択される
- 本番（PostgreSQL）とローカル（SQLite）の両環境で動作する

---

### 3. **出退勤ビジネスロジックテスト** (`TestAttendanceBusinessLogic`)

#### 目的
出退勤機能の核となるビジネスロジックが正確に動作することを検証

#### テスト項目

| テスト名 | 目的 | テストデータ | 期待結果 |
|---------|------|-------------|----------|
| `test_clock_in_logic` | 出勤処理ロジック | 出勤時刻 9:00 | datetimeオブジェクトとして正しく処理 |
| `test_clock_out_logic` | 退勤処理ロジック | 退勤時刻 18:00 | datetimeオブジェクトとして正しく処理 |
| `test_work_hours_calculation` | 勤務時間計算 | 9:00-18:00 | 9時間として計算される |

#### ビジネスルール
- 出勤時刻と退勤時刻の型統一
- 勤務時間の正確な計算
- 残業時間の自動判定

---

### 4. **出退勤コマンドテスト** (`TestAttendanceCommands`)

#### 目的
Discord UI（ボタン）との連携とコマンド処理が正常に動作することを検証

#### テスト項目

| テスト名 | 目的 | テスト内容 | 期待結果 |
|---------|------|----------|----------|
| `test_user_creation` | ユーザー情報の作成 | Discord IDからユーザー情報生成 | 適切な形式でユーザー情報が作成される |
| `test_clock_in_button_logic` | 出勤ボタンロジック | ボタンクリック時の処理フロー | エラーなく出勤記録が作成される |

#### UI連携要件
- Discord Interactionの適切な処理
- ユーザー情報の取得と作成
- レスポンスの適切な送信

---

### 5. **エラーハンドリングテスト** (`TestErrorHandling`)

#### 目的
異常値や例外的な状況での適切なエラーハンドリングを検証

#### テスト項目

| テスト名 | 目的 | 異常値 | 期待結果 |
|---------|------|--------|----------|
| `test_none_datetime_handling` | None値の処理 | `None` | エラーなくNoneとして処理される |
| `test_invalid_datetime_string` | 無効な日時文字列 | `"invalid-datetime"` | ValueErrorをキャッチしてNone返却 |

#### エラー対応方針
- 予期しない値に対する適切な処理
- システム全体の安定性確保
- ユーザーへの分かりやすいエラーメッセージ

---

### 6. **設定検証テスト** (`TestConfigValidation`)

#### 目的
環境設定と設定値の妥当性を検証

#### テスト項目

| テスト名 | 目的 | 検証対象 | 期待結果 |
|---------|------|----------|----------|
| `test_environment_variables` | 環境変数の設定 | `ENVIRONMENT`, `DATABASE_URL` | 適切に設定されている |
| `test_database_url_format` | DATABASE_URL形式 | URLの形式 | SQLiteまたはPostgreSQL形式 |

#### 設定要件
- 必要な環境変数が全て設定されている
- DATABASE_URLの形式が適切
- 環境（test/development/production）が正しく識別される

---

## 🧪 **テスト実行方法**

### 基本実行
```bash
cd tests
python test_attendance.py
```

### 詳細出力での実行
```bash
python test_attendance.py -v
```

### 特定のテストクラスのみ実行
```bash
python -m unittest test_attendance.TestDateTimeCompatibility -v
```

---

## 📊 **成功基準**

### 全体
- 全テストケースが成功（PASS）
- エラー（ERROR）が0件
- 失敗（FAIL）が0件

### 個別カテゴリー
- **日時処理**: PostgreSQL/SQLite両形式で正常処理
- **データベース**: 環境に応じた適切なモジュール選択
- **ビジネスロジック**: 正確な出退勤処理
- **コマンド**: UI連携の正常動作
- **エラーハンドリング**: 異常値の適切な処理
- **設定**: 環境設定の妥当性

---

## 🚨 **重要な修正ポイント**

### 1. **日時処理の統一**
```python
# ❌ 修正前（エラーが発生）
clock_in = datetime.fromisoformat(record['clock_in_time'])

# ✅ 修正後（互換性あり）
clock_in = record['clock_in_time']
if isinstance(clock_in, str):
    clock_in = datetime.fromisoformat(clock_in)
```

### 2. **データベース動的選択**
```python
# ✅ 環境に応じた自動選択
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import db_manager, user_repo, attendance_repo
else:
    from database import db_manager, user_repo, attendance_repo
```

### 3. **エラーハンドリング**
```python
# ✅ 安全な日時処理
try:
    if isinstance(datetime_value, str):
        result = datetime.fromisoformat(datetime_value)
    else:
        result = datetime_value
except (ValueError, TypeError):
    result = None
```

---

## 📈 **テスト結果の読み方**

### 成功時
```
🧪 Discord Bot Enterprise - 出退勤機能テスト開始
============================================================
test_datetime_object_handling (__main__.TestDateTimeCompatibility) ... ok
test_string_datetime_handling (__main__.TestDateTimeCompatibility) ... ok
...
============================================================
🎯 テスト結果サマリー
✅ 成功: 12
❌ 失敗: 0
💥 エラー: 0
📊 総テスト数: 12
```

### 失敗時
```
🚨 失敗したテスト:
  - test_datetime_object_handling (TestDateTimeCompatibility)
💥 エラーが発生したテスト:
  - test_database_imports (TestDatabaseCompatibility)
```

---

## 🔧 **トラブルシューティング**

### よくある問題

#### 1. ImportError
**症状**: `database_postgres`のインポートエラー
**原因**: PostgreSQLライブラリ（psycopg2）未インストール
**解決**: `pip install psycopg2-binary`

#### 2. TypeError: fromisoformat
**症状**: 日時処理でTypeError
**原因**: PostgreSQLのdatetimeオブジェクトに対してfromisoformat実行
**解決**: 型チェック（`isinstance`）を追加

#### 3. 環境変数未設定
**症状**: `DATABASE_URL`が見つからない
**原因**: 環境変数が設定されていない
**解決**: `.env`ファイル作成または環境変数設定

---

## 📝 **今後の拡張予定**

### 追加予定テスト
- [ ] **パフォーマンステスト**: 大量データでの処理速度
- [ ] **並行処理テスト**: 同時アクセス時の整合性
- [ ] **統合テスト**: Discord APIとの実連携
- [ ] **セキュリティテスト**: 不正なユーザー入力への対応

### テストカバレッジ目標
- **関数カバレッジ**: 95%以上
- **分岐カバレッジ**: 90%以上
- **条件カバレッジ**: 85%以上

---

*最終更新: 2025年6月10日*
*作成者: Discord Bot Enterprise 開発チーム* 