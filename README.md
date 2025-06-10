# 企業用Discord Bot

企業のワークフロー効率化を目的としたDiscord Botです。日報管理、タスク管理、カレンダー連携などの機能を提供します。

## 主な機能

### ✅ 実装済み機能
- **日報管理**: 日報の提出、確認、テンプレート表示
- **タスク管理**: 個人別タスクの追加、一覧表示、ステータス変更、削除
- **出退勤管理**: Discord GUIによる出退勤記録、勤務時間計算、在席状況表示
- **基本機能**: Ping応答、Bot情報表示

### 🚧 開発予定機能
- **Googleカレンダー連携**: 予定表示、会議リマインド
- **リマインド機能**: 日報リマインド、タスクリマインド
- **管理者機能**: 統計情報、ユーザー管理
- **出退勤機能拡張**: 有給申請、承認ワークフロー

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

## ファイル構成

```
discord_bot/
├── main.py                 # メインエントリーポイント
├── config.py              # 設定管理
├── database.py            # データベース操作
├── bot/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── daily_report.py  # 日報関連コマンド
│       ├── task_manager.py  # タスク管理コマンド
│       └── attendance.py    # 出退勤管理コマンド
├── requirements.txt        # Python依存関係
├── env_example.txt        # 環境変数設定例
├── 要件定義.md           # 要件定義書
├── 実装タスク.md         # 実装タスク一覧
└── README.md              # このファイル
```

## 開発情報

### データベース構造
- **SQLite** を使用したローカルデータベース
- **テーブル**: users, daily_reports, tasks, attendance, settings

### 技術スタック
- **言語**: Python 3.8+
- **フレームワーク**: discord.py
- **データベース**: SQLite
- **その他**: python-dotenv, google-api-python-client

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
   - `discord_bot.db` ファイルの権限を確認
   - ディスク容量を確認

## ライセンス

このプロジェクトは社内使用を目的としています。

## 連絡先

開発チーム: [連絡先情報] 