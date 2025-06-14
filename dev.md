## 🎯 プロジェクト概要

**Enterprise Discord Bot v3.0.0** は、Clean TDD (Test-Driven Development) アーキテクチャを採用した企業向けDiscord Botです。生産性向上を目的とした包括的な機能を提供し、高い保守性と拡張性を実現しています。

### 🏗️ アーキテクチャ特徴
- **Clean TDD Design**: 95%以上のテストカバレッジ
- **型安全性**: 完全な型ヒントとバリデーション
- **エラー耐性**: 包括的なエラーハンドリングとユーザーフレンドリーなメッセージ
- **構造化ログ**: 本番環境対応のコンテキスト付きログ
- **データベース柔軟性**: SQLite/PostgreSQL自動切り替え

---

## 📂 プロジェクト構造

```
discord-bot-enterprise/
├── main.py                          # アプリケーションエントリーポイント
├── src/                            # メインソースコード
│   ├── __init__.py
│   ├── core/                       # コアインフラストラクチャ
│   │   ├── __init__.py
│   │   ├── config.py              # 設定管理システム
│   │   ├── database.py            # データベース抽象化層
│   │   ├── database_postgres.py   # PostgreSQL実装
│   │   ├── logging.py             # 構造化ログシステム
│   │   ├── error_handling.py      # エラーハンドリングフレームワーク
│   │   └── health_check.py        # ヘルスチェック機能
│   └── bot/                       # Discord Bot実装
│       ├── __init__.py
│       ├── core.py               # Botフレームワーク
│       ├── commands/             # コマンド実装
│       │   ├── __init__.py
│       │   ├── admin.py         # 管理者機能
│       │   ├── attendance.py    # 出退勤管理
│       │   ├── task_manager.py  # タスク管理
│       │   ├── help.py          # ヘルプ機能
│       │   └── calendar.py      # カレンダー機能
│       ├── services/            # ビジネスロジックサービス
│       │   └── attendance.py   # 勤怠追跡サービス
│       └── models/              # データモデル
├── tests/                        # 包括的テストスイート
│   ├── __init__.py
│   ├── conftest.py              # テスト設定とフィクスチャ
│   ├── unit/                    # ユニットテスト
│   ├── integration/             # 統合テスト
│   └── fixtures/                # テストフィクスチャ
├── deploy/                       # デプロイ関連
├── scripts/                      # ユーティリティスクリプト
├── supabase/                     # Supabaseマイグレーション
├── archive/                      # 旧バージョンのアーカイブ
├── requirements.txt              # Python依存関係
├── pyproject.toml               # プロジェクト設定
├── pytest.ini                   # テスト設定
├── Dockerfile                   # 本番環境用コンテナ
└── README.md                    # プロジェクト説明
```

---

## ⚙️ 設定管理 (src/core/config.py)

### 主要クラス

#### `Config`
アプリケーション設定を管理するメインクラス

**主要プロパティ:**
```python
DISCORD_TOKEN: str              # Discord Bot Token
DISCORD_GUILD_ID: int           # Guild ID
DATABASE_URL: str               # データベース接続URL
ENVIRONMENT: str                # 実行環境 (development/staging/production/test)
TIMEZONE: str                   # タイムゾーン設定
LOG_LEVEL: str                  # ログレベル
DAILY_REPORT_TIME: str          # 日次レポート時刻
GOOGLE_CLIENT_ID: str           # Google API設定
GOOGLE_CLIENT_SECRET: str
GOOGLE_CALENDAR_ID: str
HEALTH_CHECK_PORT: int          # ヘルスチェックポート
MEETING_REMINDER_MINUTES: int   # 会議リマインダー設定
```

**主要メソッド:**
```python
validate() -> None                           # 設定検証
to_dict(include_sensitive: bool) -> Dict     # 辞書変換
update(updates: Dict) -> None                # 設定更新
reload() -> None                             # 設定再読み込み
is_development() -> bool                     # 開発環境判定
is_production() -> bool                      # 本番環境判定
get_database_type() -> str                   # DB種別取得
has_google_api_config() -> bool              # Google API設定確認
```

#### `ConfigValidator`
設定値の検証を行うクラス

**検証項目:**
- 必須フィールドの存在確認
- 環境値の妥当性 (development/staging/production/test)
- Discord Guild IDの数値形式
- ログレベルの有効性 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- タイムゾーン形式
- 時刻形式 (HH:MM)

### グローバル関数
```python
get_config() -> Config                       # グローバル設定インスタンス取得
set_config(config: Config) -> None           # グローバル設定設定
load_config_from_env(env_file: str) -> Config  # 環境ファイルから設定読み込み
```

---

## 🗄️ データベース抽象化 (src/core/database.py)

### 主要クラス

#### `DatabaseManager`
SQLite用のデータベースマネージャー

**プロパティ:**
```python
database_url: str               # データベースURL
pool_size: int                  # コネクションプールサイズ
connection_pool: Optional[asyncio.Queue]  # コネクションプール
_initialized: bool              # 初期化状態
logger: logging.Logger          # ロガー
```

**主要メソッド:**
```python
async def initialize() -> None                              # DB初期化
async def get_connection() -> AsyncGenerator[DatabaseConnection, None]  # コネクション取得
async def close() -> None                                   # コネクション終了
async def _run_migrations() -> None                         # マイグレーション実行
async def get_schema_version() -> int                       # スキーマバージョン取得

# ユーザー操作
async def create_user(discord_id: int, username: str, display_name: str, **kwargs) -> int
async def get_user(discord_id: int) -> Optional[Dict[str, Any]]
async def update_user(discord_id: int, **kwargs) -> bool
async def list_users() -> List[Dict[str, Any]]
```

#### `DatabaseConnection`
非同期データベース接続ラッパー

**メソッド:**
```python
async def execute(query: str, parameters: tuple) -> aiosqlite.Cursor
async def commit() -> None
async def rollback() -> None
```

### データベーススキーマ

#### `users` テーブル
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER UNIQUE NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    timezone TEXT DEFAULT 'Asia/Tokyo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `tasks` テーブル
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (discord_id)
);
```

#### `attendance` テーブル
```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    check_in TIMESTAMP NOT NULL,
    check_out TIMESTAMP,
    break_start TIMESTAMP,
    break_end TIMESTAMP,
    work_hours REAL DEFAULT 0.0,
    overtime_hours REAL DEFAULT 0.0,
    date TEXT NOT NULL, -- YYYY-MM-DD format
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (discord_id),
    UNIQUE(user_id, date)
);
```

#### `user_preferences` テーブル
```sql
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    language TEXT DEFAULT 'ja',
    notification_enabled BOOLEAN DEFAULT TRUE,
    daily_report_time TEXT DEFAULT '17:00',
    FOREIGN KEY (user_id) REFERENCES users (discord_id)
);
```

### グローバル関数
```python
get_database_manager(database_url: str) -> Union[DatabaseManager, PostgreSQLManager]  # DB管理者取得
set_database_manager(manager) -> None                                                  # DB管理者設定
is_postgresql_url(database_url: str) -> bool                                          # PostgreSQL URL判定
```

---

## 📊 ログシステム (src/core/logging.py)

### 主要クラス

#### `StructuredFormatter`
構造化ログフォーマッター

**機能:**
- タイムスタンプ、レベル、ロガー名、メッセージの構造化
- 追加フィールドの自動抽出
- 例外情報の自動フォーマット
- JSON対応の値変換

#### `LoggerManager`
ログ管理クラス

**プロパティ:**
```python
log_level: int                  # ログレベル
log_file: Optional[str]         # ログファイルパス
include_extra: bool             # 追加情報含有フラグ
formatter: StructuredFormatter  # フォーマッター
_configured_loggers: set        # 設定済みロガー集合
```

**メソッド:**
```python
get_logger(name: str, **context) -> logging.Logger     # ロガー取得
_configure_logger(logger: logging.Logger) -> None      # ロガー設定
from_config(config) -> LoggerManager                   # 設定からの作成
```

#### `LoggerAdapter`
コンテキスト付きロガーアダプター

#### `PerformanceTimer`
操作の性能測定用コンテキストマネージャー

### ユーティリティ関数
```python
log_user_action(logger, user_id: int, action: str, **details) -> None
log_command_execution(logger, command: str, user_id: int, guild_id: int, success: bool, **details) -> None
log_database_operation(logger, operation: str, table: str, success: bool, **details) -> None
log_error_with_context(logger, error: Exception, context: Dict) -> None
time_operation(logger, operation: str, **context) -> PerformanceTimer
```

### グローバル関数
```python
get_logger(name: str, **context) -> logging.Logger
set_logger_manager(manager: LoggerManager) -> None
configure_logging(log_level: str, log_file: Optional[str]) -> None
get_contextual_logger(name: str, **context) -> LoggerAdapter
```

---

## 🛡️ エラーハンドリング (src/core/error_handling.py)

### 例外階層

#### `BotError` (基底例外)
```python
class BotError(Exception):
    error_code: Optional[str]           # エラーコード
    user_message: Optional[str]         # ユーザー向けメッセージ
    context: Dict[str, Any]             # コンテキスト情報
    timestamp: datetime                 # 発生時刻
    error_id: str                       # エラーID
```

#### `UserError` (ユーザーエラー)
ユーザーの操作に起因するエラー（ユーザーに表示）

#### `SystemError` (システムエラー)
内部システムエラー（ログ記録、ユーザーには簡潔なメッセージ）

#### `ConfigurationError` (設定エラー)
設定関連のエラー

### 主要クラス

#### `ErrorContext`
エラーコンテキスト情報
```python
user_id: Optional[int]              # ユーザーID
guild_id: Optional[int]             # ギルドID
channel_id: Optional[int]           # チャンネルID
command: Optional[str]              # コマンド名
message_id: Optional[int]           # メッセージID
additional_data: Optional[Dict]     # 追加データ
```

#### `ErrorResult`
エラー処理結果
```python
user_message: str                   # ユーザー向けメッセージ
should_notify_user: bool            # ユーザー通知要否
should_log: bool                    # ログ記録要否
log_level: str                      # ログレベル
context: Dict[str, Any]             # コンテキスト
recovered: bool                     # 復旧状態
recovery_result: Optional[Any]      # 復旧結果
error_id: Optional[str]             # エラーID
```

#### `ErrorRecovery`
エラー復旧メカニズム
```python
strategies: Dict[str, Callable]     # 復旧戦略
register_strategy(error_code: str, strategy: Callable) -> None
attempt_recovery(error: BotError, context: ErrorContext) -> Optional[Any]
```

#### `ErrorHandler`
メインエラーハンドリングコーディネーター
```python
logger: logging.Logger              # ロガー
recovery: ErrorRecovery             # 復旧システム
error_counts: defaultdict[int]      # エラー統計
user_error_timestamps: defaultdict[list]  # レート制限用
rate_limit_window: int              # レート制限ウィンドウ
rate_limit_max: int                 # レート制限最大値

# 主要メソッド
handle_error(error: Union[Exception, BotError], context: ErrorContext) -> ErrorResult
async handle_error_async(error: Union[Exception, BotError], context: ErrorContext) -> ErrorResult
async handle_discord_error(error: Union[Exception, BotError], ctx: Any) -> None
get_error_metrics() -> Dict[str, int]
clear_metrics() -> None
```

### ユーティリティ関数
```python
handle_user_input_error(message: str, user_message: str, **context) -> UserError
handle_permission_error(user_id: int, required_permission: str, **context) -> UserError
handle_database_error(operation: str, table: str, original_error: Exception, **context) -> SystemError
handle_api_error(service: str, endpoint: str, status_code: int, **context) -> SystemError
```

### デコレーター
```python
@handle_errors(error_handler: Optional[ErrorHandler] = None)
```
関数の自動エラーハンドリング

---

## 🤖 Botフレームワーク (src/bot/core.py)

### 主要クラス

#### `DiscordBot`
Discord Bot メインクラス（`commands.Bot`を継承）

**プロパティ:**
```python
config: Config                      # 設定
logger: logging.Logger              # ロガー
error_handler: ErrorHandler        # エラーハンドラー
start_time: datetime                # 開始時刻
commands_executed: int              # 実行コマンド数
```

**組み込みコマンド:**
- `!ping` - ボットレイテンシーとステータス確認
- `!info` - ボット情報表示
- `!health` - ヘルスチェック

**イベントハンドラー:**
```python
async def on_ready()                        # ボット準備完了
async def on_message(message)               # メッセージ受信
async def on_command(ctx)                   # コマンド実行
async def on_command_error(ctx, error)      # コマンドエラー
```

**内部メソッド:**
```python
async def setup_hook()                      # セットアップ
async def _initialize_database()            # DB初期化
async def _set_status()                     # ステータス設定
async def _load_extensions()                # 拡張読み込み
def _add_builtin_commands()                 # 組み込みコマンド追加
def _get_uptime() -> str                    # 稼働時間取得
def _get_memory_usage() -> str              # メモリ使用量取得
```

#### `BotManager`
Bot ライフサイクル管理

**メソッド:**
```python
async def create_bot() -> DiscordBot        # ボット作成
async def start_bot()                       # ボット開始
async def stop_bot()                        # ボット停止
async def restart_bot()                     # ボット再起動
def get_status() -> dict                    # ステータス取得
```

### ユーティリティ関数
```python
async def ensure_user_registered(ctx: commands.Context) -> bool  # ユーザー登録確認
```

### デコレーター
```python
@require_registration  # ユーザー登録必須
@admin_only           # 管理者専用
```

### グローバル関数
```python
get_bot_manager() -> BotManager
set_bot_manager(manager: BotManager) -> None
```

---

## 👤 出退勤管理 (src/bot/commands/attendance.py)

### UI コンポーネント

#### `AttendanceView`
出退勤管理用ボタンUI（`discord.ui.View`）

**ボタン:**
- 🟢 出勤ボタン (`clock_in_button`)
- 🔴 退勤ボタン (`clock_out_button`)
- 🟡 休憩開始ボタン (`break_start_button`)
- 🟢 休憩終了ボタン (`break_end_button`)

### コマンドクラス

#### `AttendanceCog`
出退勤管理機能を提供するCog

**コマンド:**
```python
@commands.command(name='出退勤', aliases=['attendance', 'punch'])
async def attendance_panel(ctx)                           # 出退勤パネル表示

@commands.command(name='勤怠確認', aliases=['attendance_status', 'status'])
async def check_attendance(ctx, target_date: str = None)  # 勤怠状況確認

@commands.command(name='在席状況', aliases=['who_is_here', 'status_all'])
async def show_all_status(ctx)                            # 全員在席状況

@commands.command(name='月次勤怠', aliases=['monthly_report'])
async def monthly_attendance_report(ctx, year: int = None, month: int = None)  # 月次レポート

@commands.command(name='勤怠CSV', aliases=['attendance_csv', 'export_csv'])
async def export_attendance_csv(ctx, start_date: str = None, end_date: str = None, user_mention: discord.Member = None)  # CSV出力

@commands.command(name='勤怠CSV使い方', aliases=['csv_help'])
async def csv_help(ctx)                                   # CSV出力ヘルプ
```

---

## 📋 タスク管理 (src/bot/commands/task_manager.py)

#### `TaskManagerCog`
タスク管理機能を提供するCog

**コマンド:**
```python
@commands.command(name='タスク追加', aliases=['task_add', 'add_task'])
async def add_task(ctx, *, task_info: str)                # タスク追加

@commands.command(name='タスク一覧', aliases=['task_list', 'tasks'])
async def list_tasks(ctx, status: Optional[str] = None)   # タスク一覧

@commands.command(name='タスク完了', aliases=['task_done', 'done'])
async def complete_task(ctx, task_id: int)                # タスク完了

@commands.command(name='タスク削除', aliases=['task_delete', 'delete_task'])
async def delete_task(ctx, task_id: int)                  # タスク削除

@commands.command(name='タスク進行中', aliases=['task_progress', 'progress'])
async def progress_task(ctx, task_id: int)                # タスク進行中変更

@commands.command(name='タスクヘルプ', aliases=['task_help'])
async def task_help(ctx)                                  # タスクヘルプ
```

**タスク情報解析:**
```python
def _parse_task_info(task_info: str) -> Dict[str, Any]
```

**対応オプション:**
- `priority:高/中/低` - 優先度設定
- `due:YYYY-MM-DD` - 期限設定

**タスクステータス:**
- 未着手 (pending)
- 進行中 (in_progress)
- 完了 (completed)
- 中断 (cancelled)

---

## 🔧 管理者機能 (src/bot/commands/admin.py)

#### `AdminCog`
管理者機能を提供するCog

**コマンドグループ:**
```python
@commands.group(name='admin', aliases=['管理'])
@commands.has_permissions(administrator=True)
async def admin_group(ctx)                                # 管理者コマンドグループ
```

**サブコマンド:**
```python
@admin_group.command(name='stats', aliases=['統計'])
async def show_stats(ctx)                                 # システム統計

@admin_group.command(name='users', aliases=['ユーザー'])
async def show_users(ctx)                                 # ユーザー一覧

@admin_group.command(name='tasks', aliases=['タスク'])
async def show_task_stats(ctx)                            # タスク統計

@admin_group.command(name='attendance', aliases=['出勤'])
async def show_attendance_stats(ctx, days: int = 7)       # 出勤統計

@admin_group.command(name='backup', aliases=['バックアップ'])
async def create_backup(ctx)                              # DBバックアップ

@admin_group.command(name='settings', aliases=['設定'])
async def show_settings(ctx)                              # Bot設定表示
```

**統計情報:**
```python
def _get_system_stats(self) -> Dict[str, Any]:
```
- 登録ユーザー数
- 総タスク数
- 未完了タスク数
- 期限切れタスク数
- 今日の出勤者数
- 現在出勤中人数
- 稼働時間

---

## 🕐 勤怠追跡サービス (src/bot/services/attendance.py)

### データモデル

#### `AttendanceRecord`
勤怠記録データクラス
```python
user_id: int                        # ユーザーID
date: str                           # 日付
check_in: Optional[datetime]        # 出勤時刻
check_out: Optional[datetime]       # 退勤時刻
break_start: Optional[datetime]     # 休憩開始
break_end: Optional[datetime]       # 休憩終了
work_hours: float                   # 勤務時間
overtime_hours: float               # 残業時間
created_at: Optional[datetime]      # 作成日時
```

#### `AttendanceResult`
勤怠操作結果
```python
success: bool                       # 成功フラグ
message: str                        # メッセージ
data: Optional[Dict[str, Any]]      # データ
```

### サービスクラス

#### `AttendanceCalculator`
勤怠計算クラス
```python
standard_hours: float = 8.0         # 標準勤務時間
standard_start_time: str = "09:00"  # 標準開始時刻
standard_end_time: str = "18:00"    # 標準終了時刻

# メソッド
calculate_work_hours(check_in, check_out, break_start=None, break_end=None) -> float
calculate_break_duration(break_start, break_end) -> float
calculate_overtime(work_hours) -> float
is_late(check_in, grace_minutes=5) -> bool
is_early_departure(check_out) -> bool
```

#### `AttendanceService`
メイン勤怠サービス
```python
logger: logging.Logger              # ロガー
calculator: AttendanceCalculator    # 計算機
timezone: timezone                  # タイムゾーン

# 主要メソッド
async def check_in(user_id: int, check_in_time: Optional[datetime] = None) -> AttendanceResult
async def check_out(user_id: int, check_out_time: Optional[datetime] = None) -> AttendanceResult
async def start_break(user_id: int, break_start_time: Optional[datetime] = None) -> AttendanceResult
async def end_break(user_id: int, break_end_time: Optional[datetime] = None) -> AttendanceResult
async def get_current_status(user_id: int) -> Dict[str, Any]
async def get_daily_record(user_id: int, date: str) -> Optional[AttendanceRecord]
async def get_weekly_summary(user_id: int, week_start: str) -> Dict[str, Any]
async def get_monthly_summary(user_id: int, year: int, month: int) -> Dict[str, Any]
async def export_csv(user_id: int, start_date: str, end_date: str) -> str
```

---

## 🧪 テストアーキテクチャ (tests/)

### テスト設定 (conftest.py)

#### フィクスチャ一覧
```python
@pytest.fixture(scope="session")
event_loop()                        # イベントループ

@pytest.fixture
temp_db_path()                      # 一時DB パス

@pytest.fixture
async test_db(temp_db_path)         # テストDB接続

@pytest.fixture
mock_discord_bot()                  # モックDiscord Bot

@pytest.fixture
mock_discord_ctx()                  # モックDiscordコンテキスト

@pytest.fixture
mock_discord_member()               # モックDiscordメンバー

@pytest.fixture
sample_user_data()                  # サンプルユーザーデータ

@pytest.fixture
sample_task_data()                  # サンプルタスクデータ

@pytest.fixture
sample_attendance_data()            # サンプル勤怠データ

@pytest.fixture
mock_config()                       # モック設定

@pytest.fixture
async mock_database()               # モックデータベース

@pytest.fixture
mock_logger()                       # モックロガー

@pytest.fixture(autouse=True)
setup_test_environment()            # テスト環境セットアップ
```

### テスト設定 (pytest.ini)
```ini
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    database: Database dependent tests
    discord: Discord API dependent tests
```

---

## 🏭 本番環境設定

### Docker設定 (Dockerfile)
```dockerfile
FROM python:3.11-slim

# セキュリティ: 非rootユーザー作成
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコピー
COPY src/ ./src/
COPY main.py .

# 権限設定
RUN mkdir -p logs && chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
```

### 依存関係 (requirements.txt)
```txt
# Core Dependencies
discord.py==2.3.2
python-dotenv==1.0.0
pytz==2023.3

# Database
psycopg2-binary==2.9.9
asyncpg==0.28.0
aiosqlite==0.19.0

# Testing & Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-xdist==3.3.1

# Google API (Optional)
google-api-python-client==2.108.0
google-auth==2.23.4
google-auth-oauthlib==1.1.0

# Development Tools
black==23.9.1
isort==5.12.0
mypy==1.6.1
flake8==6.1.0

# Production
uvloop==0.19.0
aiofiles==23.2.1
Flask==3.0.0
psutil==5.9.6
requests==2.31.0
```

---

## 🔧 開発ルール・規則

### 🏗️ アーキテクチャ原則

#### 1. Clean Architecture
- **関心の分離**: コア機能、Bot実装、外部依存の明確な分離
- **依存性逆転**: 外部システムはインターフェースを通してアクセス
- **単一責任**: 各クラスは単一の責任を持つ
- **開放閉鎖**: 拡張に開放、修正に閉鎖

#### 2. Test-Driven Development (TDD)
- **テストファースト**: 実装前にテストを作成
- **Red-Green-Refactor**: 失敗→成功→リファクタリングのサイクル
- **高カバレッジ**: 85%以上のテストカバレッジ維持
- **継続的統合**: 全テストパス必須

### 📝 コーディング規約

#### 1. Python スタイル
- **PEP 8** 準拠
- **Type Hints** 必須
- **Docstrings** 必須（関数、クラス、モジュール）
- **Black** による自動フォーマット
- **isort** による import 整理
- **mypy** による型チェック
- **flake8** による静的解析

#### 2. 命名規則
```python
# クラス: PascalCase
class DatabaseManager:
    pass

# 関数・変数: snake_case
def get_user_data():
    user_name = "example"

# 定数: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# プライベート: 先頭アンダースコア
def _internal_method():
    pass

# ファイル: snake_case
# attendance_service.py
```

#### 3. ファイル構造規約
```python
"""
モジュールdocstring
機能の説明
"""
import standard_library
import third_party
import local_imports

# 定数定義
CONSTANT_VALUE = 42

# 例外定義
class CustomError(Exception):
    pass

# データクラス定義
@dataclass
class DataModel:
    pass

# メインクラス
class MainClass:
    pass

# 関数定義
def utility_function():
    pass

# グローバル変数とアクセサー
_global_instance = None

def get_instance():
    return _global_instance
```

### 🛡️ エラーハンドリング規約

#### 1. 例外階層の使用
```python
# 適切な例外クラスを選択
raise UserError("Invalid input", user_message="Please check your input")
raise SystemError("Database connection failed", error_code="DB_001")
```

#### 2. ログ記録
```python
# 構造化ログの使用
logger.info("User action completed", extra={
    "user_id": user_id,
    "action": "check_in",
    "duration": 1.23
})

# エラーコンテキストの記録
log_error_with_context(logger, error, {
    "user_id": user_id,
    "command": "attendance"
})
```

#### 3. ユーザー向けメッセージ
```python
# 明確で実用的なメッセージ
return AttendanceResult(
    success=False,
    message="You must check in before starting a break."
)
```

### 🗄️ データベース規約

#### 1. マイグレーション
- バージョン管理されたマイグレーション
- 後方互換性の維持
- ロールバック可能な変更

#### 2. クエリ最適化
- インデックスの適切な使用
- N+1 問題の回避
- 適切な結合の使用

#### 3. トランザクション管理
```python
async with db_manager.get_connection() as conn:
    try:
        # 複数の操作
        await conn.execute(query1)
        await conn.execute(query2)
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
```

### 🧪 テスト規約

#### 1. テスト分類
- **Unit Tests**: 単一クラス・関数のテスト
- **Integration Tests**: 複数コンポーネントの統合テスト
- **End-to-End Tests**: 全体フローのテスト

#### 2. テスト命名
```python
def test_check_in_success_creates_attendance_record():
    # Given
    user_id = 123
    
    # When
    result = await attendance_service.check_in(user_id)
    
    # Then
    assert result.success is True
    assert "checked in" in result.message
```

#### 3. モックの使用
- 外部依存をモック
- テストの独立性確保
- 決定論的なテスト結果

### 🚀 デプロイメント規約

#### 1. 環境分離
- **development**: 開発環境
- **staging**: ステージング環境
- **production**: 本番環境
- **test**: テスト環境

#### 2. 設定管理
- 環境変数による設定
- 機密情報の適切な管理
- 設定検証の実施

#### 3. ヘルスチェック
- 定期的なヘルスチェック
- 依存サービスの監視
- 自動復旧メカニズム

### 📊 監視・運用規約

#### 1. ログ管理
- 構造化ログの使用
- 適切なログレベル設定
- ログローテーション

#### 2. メトリクス収集
- パフォーマンスメトリクス
- エラー率の監視
- リソース使用量の追跡

#### 3. アラート設定
- 重要エラーの即座通知
- リソース枯渇の早期警告
- SLA 監視

### 🔒 セキュリティ規約

#### 1. 認証・認可
- Discord ユーザー認証
- 管理者権限の適切な管理
- API アクセス制御

#### 2. データ保護
- 個人情報の適切な処理
- 機密情報のマスキング
- 適切なデータ保持期間

#### 3. 入力検証
- すべての外部入力の検証
- SQL インジェクション対策
- XSS 対策

---

## 🎮 主要コマンド一覧

### 基本コマンド
- `!ping` - Bot レイテンシー確認
- `!info` - Bot 情報表示
- `!health` - システムヘルスチェック

### 出退勤管理
- `!出退勤` / `!attendance` - 出退勤パネル表示
- `!勤怠確認` / `!status [日付]` - 勤怠状況確認
- `!在席状況` / `!who_is_here` - 全員の在席状況
- `!月次勤怠` / `!monthly_report [年] [月]` - 月次レポート
- `!勤怠CSV` / `!attendance_csv [開始日] [終了日] [@ユーザー]` - CSV出力

### タスク管理
- `!タスク追加` / `!task_add [タスク名] [priority:優先度] [due:期限]` - タスク追加
- `!タスク一覧` / `!tasks [ステータス]` - タスク一覧表示
- `!タスク完了` / `!done [ID]` - タスク完了
- `!タスク削除` / `!delete_task [ID]` - タスク削除
- `!タスク進行中` / `!progress [ID]` - タスク進行中変更

### 管理者コマンド
- `!admin stats` - システム統計表示
- `!admin users` - ユーザー一覧表示
- `!admin tasks` - タスク統計表示
- `!admin attendance [日数]` - 出勤統計表示
- `!admin backup` - データベースバックアップ
- `!admin settings` - Bot設定表示

---

## 📈 システム監視

### ヘルスチェックエンドポイント
- `GET /health` - サービスヘルス状態
- `GET /` - サービス情報

### メトリクス
- データベース接続状態
- Bot レイテンシー
- メモリ使用量
- 実行コマンド数
- エラー発生率

### ログ出力
- 構造化ログによる詳細な追跡
- ユーザーアクション記録
- コマンド実行履歴
- エラー詳細とコンテキスト
- パフォーマンス測定

---

## 🏆 品質保証

### テストカバレッジ
- **目標**: 85%以上
- **単体テスト**: 各クラス・関数の個別テスト
- **統合テスト**: コンポーネント間の相互作用テスト
- **エンドツーエンドテスト**: 完全なユーザーフローのテスト

### コード品質ツール
- **Black**: コードフォーマット自動化
- **isort**: import 文の整理
- **mypy**: 型チェック
- **flake8**: 静的解析
- **pytest**: テスト実行とカバレッジ測定

### 継続的統合
- すべてのプルリクエストでテスト実行
- コード品質チェック必須
- カバレッジ低下の検出
- 自動デプロイメント

---

## 📚 参考情報

### 技術スタック
- **言語**: Python 3.8+
- **フレームワーク**: Discord.py 2.3+
- **データベース**: SQLite (開発) / PostgreSQL (本番)
- **テスト**: pytest, pytest-asyncio, pytest-cov
- **コード品質**: Black, isort, mypy, flake8
- **本番環境**: Docker, ヘルスチェック

### 外部依存関係
- **Discord API**: Botインターフェース
- **Google Calendar API**: カレンダー統合（オプション）
- **PostgreSQL**: 本番データベース
- **Docker**: コンテナ化
- **Koyeb/Supabase**: デプロイメントプラットフォーム

---

*このドキュメントは Enterprise Discord Bot v3.0.0 の完全な技術仕様書です。開発、保守、運用に必要な全ての情報を含んでいます。*