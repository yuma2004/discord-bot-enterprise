# 企業用Discord Bot v2.0.0 🚀

企業のワークフロー効率化を目的としたDiscord Botです。タスク管理、出退勤管理、カレンダー連携などの機能を提供します。

## 🎯 主な機能

### ✅ 実装済み機能
- **タスク管理**: 個人別タスクの追加、一覧表示、ステータス変更、削除、優先度・期限管理
- **出退勤管理**: Discord GUIによる出退勤記録、勤務時間計算、在席状況表示、CSV出力
- **管理者機能**: 統計情報表示、ユーザー管理、データベースバックアップ
- **基本機能**: Ping応答、Bot情報表示、包括的ヘルプ機能
- **Googleカレンダー連携**: 今日・週間予定表示（基本実装済み）

### 🔧 v2.0.0 アーキテクチャ改善
- **コアモジュール化**: `core/` パッケージによる機能分離
  - データベース抽象化（SQLite/PostgreSQL対応）
  - 統一ログ管理とエラーハンドリング
  - 本番環境ヘルスチェック機能
- **型安全性**: 完全なTypeHint適用と型エラー修正完了
- **設定管理**: 改善された設定検証とバリデーション
- **テスト網羅**: 包括的テストスイート（97.8%成功率）
- **日本時間対応**: 全機能で Asia/Tokyo タイムゾーン統一

### 🚧 開発予定機能
- **日報機能**: 日報提出・管理機能の復旧と拡張
- **リマインド機能**: 日報・タスクリマインド機能
- **カレンダー機能拡張**: 会議リマインド、予定作成機能

## 📁 プロジェクト構造

```
discord-bot-enterprise/
├── main.py                 # メインアプリケーション
├── config.py              # 設定管理（リファクタリング済み）
├── database.py            # SQLiteデータベース操作
├── database_postgres.py   # PostgreSQLデータベース操作
├── core/                  # コアモジュール（新規）
│   ├── __init__.py
│   ├── database.py        # データベース抽象化
│   ├── logging.py         # ログ管理
│   ├── health_check.py    # ヘルスチェック機能
│   ├── error_handling.py  # エラーハンドリング
│   └── utils.py           # 共通ユーティリティ
├── bot/
│   ├── commands/          # コマンド機能
│   │   ├── task_manager.py       # タスク管理
│   │   ├── attendance.py         # 出退勤管理
│   │   ├── admin.py              # 管理者機能
│   │   ├── calendar.py           # カレンダー機能
│   │   └── help.py               # ヘルプ機能
│   └── utils/             # ユーティリティ
├── tests/                 # テストスイート
├── deploy/                # デプロイメント設定
└── scripts/               # セットアップスクリプト
```

## セットアップ

### 1. 必要な環境
- Python 3.8以上
- Discord Developer Portal でのBot作成

### 2. インストール
```bash
# リポジトリをクローン
git clone [repository-url]
cd discord-bot

# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 環境設定
1. `env_example.txt` を参考に `.env` ファイルを作成
2. Discord Developer Portal で Bot Token を取得
3. `.env` ファイルに必要な情報を設定

```bash
# .env ファイルの例
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
```

### 4. Bot の起動
```bash
python main.py
```

## 使用方法

### 日報機能
```
# 日報提出
!日報 今日の作業: プロジェクトA進捗確認
明日の予定: プロジェクトBのレビュー

# 日報確認
!日報確認 2024-02-15

# 日報テンプレート表示
!日報テンプレート
```

### タスク管理機能
```
# タスク追加
!タスク追加 プロジェクトAの資料作成
!タスク追加 会議の準備 priority:高 due:2024-02-15

# タスク一覧表示
!タスク一覧
!タスク一覧 進行中

# タスクステータス変更
!タスク完了 1
!タスク進行中 2

# タスク削除
!タスク削除 3

# ヘルプ表示
!タスクヘルプ
```

### 出退勤管理機能
```
# 出退勤管理パネル表示（ボタンUI）
!出退勤

# 自分の勤怠状況確認
!勤怠確認
!勤怠確認 2024-02-15

# 全員の在席状況表示
!在席状況

# 月次勤怠レポート
!月次勤怠
!月次勤怠 2024 2
```

### 基本機能
```
# Bot の応答速度確認
!ping

# Bot 情報表示
!info

# ヘルプ表示
!help
```

## 開発情報

### データベース構造
- **開発環境**: SQLite（ローカルファイル）
- **本番環境**: PostgreSQL（Supabase/Koyeb対応）
- **主要テーブル**: users, tasks, attendance, settings
- **特徴**: 自動データベース切り替え、日本時間対応

### 技術スタック
- **言語**: Python 3.8+
- **主要フレームワーク**: discord.py 2.x
- **データベース**: SQLite / PostgreSQL（psycopg2）
- **デプロイ**: Koyeb、Supabase連携
- **その他**: python-dotenv, pytz, google-api-python-client

### アーキテクチャ
- **リファクタリング版 v2.0.0**: コアモジュール化アーキテクチャ
- **設計パターン**: ファクトリーパターン（データベース）、シングルトン（設定管理）
- **型安全性**: 完全なTypeHint、型チェック済み

## 🚀 デプロイメント

### 本番環境（Koyeb + Supabase）
詳細な手順は `deploy/` ディレクトリ内のガイドを参照してください：
- `deploy/koyeb_supabase_guide.md` - メイン設定ガイド
- `deploy/production_deploy_manual.md` - 本番デプロイ手順

### ローカル開発環境
```bash
# 環境変数設定（.envファイル）
DISCORD_TOKEN=your_token_here
DATABASE_URL=discord_bot.db  # SQLite使用
ENVIRONMENT=development
```

## 🧪 テスト

### テスト実行
```bash
# 全テスト実行
python tests/run_all_tests.py

# 特定機能のテスト
python tests/test_attendance.py
python tests/test_basic.py
```

### テスト結果
- **総合成功率**: 97.8% (44/45 tests)
- **カバレッジ**: 基本機能、エラーハンドリング、パフォーマンステスト
- **詳細**: `tests/TEST_ITEMS.md` 参照

## 📋 変更履歴

### v2.0.0 (2025年6月)
- ✅ **アーキテクチャ全面リファクタリング**
- ✅ **型安全性向上** - 100+個の型エラー修正
- ✅ **コアモジュール化** - `core/` パッケージ新設
- ✅ **テストスイート整備** - 包括的テスト実装
- ✅ **本番対応強化** - PostgreSQL対応、ヘルスチェック
- ✅ **日時処理改善** - 日本時間統一対応

## トラブルシューティング

### よくある問題

1. **Bot が起動しない**
   - `.env` ファイルの設定を確認
   - Discord Token が正しいかチェック
   - Python のバージョンを確認（3.8以上）

2. **コマンドが反応しない**
   - Bot にメッセージを読む権限があるか確認
   - コマンドプレフィックス `!` を確認

3. **データベースエラー**
   - 開発環境: `discord_bot.db` ファイルの権限を確認
   - 本番環境: DATABASE_URL（PostgreSQL）の設定を確認

4. **型エラー**
   - Python 3.8以上を使用
   - 依存関係を最新に更新: `pip install -r requirements.txt`

## ライセンス

このプロジェクトは社内使用を目的としています。

## 連絡先

技術的な質問やサポートについては、システム管理者までお問い合わせください。 