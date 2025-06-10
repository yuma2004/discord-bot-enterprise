# 企業用Discord Bot デプロイガイド

## 前提条件

- Python 3.8以上がインストールされていること
- Discord Developer Portal へのアクセス権限があること
- サーバー管理者権限（本番環境の場合）

## 1. 環境セットアップ

### 1-1. 仮想環境の作成

```bash
# 仮想環境作成
python -m venv discord_bot_env

# 仮想環境有効化 (Windows)
discord_bot_env\Scripts\activate

# 仮想環境有効化 (Linux/Mac)
source discord_bot_env/bin/activate
```

### 1-2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 2. Discord Bot設定

### 2-1. Discord Developer Portalでの設定

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリック
3. アプリケーション名を入力（例: 企業用Bot）
4. 「Bot」セクションに移動
5. 「Add Bot」をクリック
6. Botトークンをコピー（後で.envファイルに設定）

### 2-2. Bot権限の設定

「OAuth2」→「URL Generator」で以下の権限を設定：

**Scopes:**
- `bot`
- `applications.commands`

**Bot Permissions:**
- Send Messages
- Use Slash Commands
- Read Message History
- Add Reactions
- Embed Links
- Attach Files
- Mention Everyone

### 2-3. サーバーにBotを招待

生成されたURLを使用してBotをサーバーに招待

## 3. 環境変数の設定

### 3-1. .envファイルの作成

`env_example.txt` をコピーして `.env` ファイルを作成：

```bash
cp env_example.txt .env
```

### 3-2. 環境変数の設定

`.env` ファイルを編集：

```env
# Discord Bot設定
DISCORD_BOT_TOKEN=あなたのBotトークン
DISCORD_GUILD_ID=サーバーのGuild ID

# データベース設定
DATABASE_URL=discord_bot.db

# Google Calendar API設定（オプション）
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALENDAR_ID=

# その他設定
LOG_LEVEL=INFO
TIMEZONE=Asia/Tokyo
DAILY_REPORT_TIME=17:00
MEETING_REMINDER_MINUTES=15
```

## 4. データベースの初期化

```bash
python main.py --init-db
```

または、Pythonスクリプト内で：

```python
from database import db_manager
db_manager.initialize_database()
```

## 5. テストの実行

```bash
# 基本テストの実行
python tests/test_basic.py

# または pytest を使用（インストール済みの場合）
pytest tests/
```

## 6. Bot の起動

### 6-1. 開発環境での起動

```bash
python main.py
```

### 6-2. 本番環境での起動

#### systemd サービスとして実行（Linux）

1. サービスファイルを作成 (`/etc/systemd/system/discord-bot.service`)：

```ini
[Unit]
Description=企業用Discord Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/your/bot
Environment=PATH=/path/to/your/bot/discord_bot_env/bin
ExecStart=/path/to/your/bot/discord_bot_env/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. サービスを有効化・開始：

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
```

#### スクリーンセッションで実行

```bash
# スクリーンセッション開始
screen -S discord-bot

# Bot起動
python main.py

# セッションから抜ける (Ctrl+A, D)
```

## 7. Google Calendar API設定（オプション）

### 7-1. Google Cloud Console設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. Google Calendar API を有効化
4. 認証情報を作成（OAuth 2.0 クライアントID）
5. 認証情報をダウンロードし、プロジェクトルートに配置

### 7-2. 認証フローの実行

初回起動時にブラウザで認証を完了

## 8. 監視・ログ設定

### 8-1. ログファイルの確認

```bash
# ログファイルの場所
tail -f discord_bot.log

# または journalctl（systemd使用時）
journalctl -u discord-bot -f
```

### 8-2. 定期バックアップの設定

crontabでデータベースの定期バックアップを設定：

```bash
crontab -e

# 毎日午前2時にバックアップ
0 2 * * * /path/to/backup_script.sh
```

バックアップスクリプト例：

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cp /path/to/discord_bot.db "$BACKUP_DIR/discord_bot_$DATE.db"

# 30日以上古いバックアップを削除
find $BACKUP_DIR -name "discord_bot_*.db" -mtime +30 -delete
```

## 9. トラブルシューティング

### 9-1. よくある問題

**Bot がオフラインと表示される**
- トークンが正しく設定されているか確認
- Bot権限が適切に設定されているか確認

**コマンドが動作しない**
- Bot に適切な権限があるか確認
- エラーログを確認

**データベースエラー**
- データベースファイルの権限を確認
- 初期化が正しく行われているか確認

### 9-2. ログレベルの変更

デバッグ時は `LOG_LEVEL=DEBUG` に設定

### 9-3. 緊急時の対応

1. Bot プロセスの停止：
```bash
sudo systemctl stop discord-bot
```

2. 最新バックアップからの復元：
```bash
cp /path/to/backup/discord_bot_YYYYMMDD.db discord_bot.db
```

3. Bot プロセスの再開：
```bash
sudo systemctl start discord-bot
```

## 10. アップデート手順

1. サービス停止
2. コードの更新
3. 依存関係の確認・更新
4. データベースマイグレーション（必要に応じて）
5. テスト実行
6. サービス再開

```bash
sudo systemctl stop discord-bot
git pull origin main
pip install -r requirements.txt
python tests/test_basic.py
sudo systemctl start discord-bot
```

## 11. セキュリティ対策

- `.env` ファイルの権限を制限 (`chmod 600 .env`)
- データベースファイルのアクセス権限を制限
- 定期的なバックアップとリストア手順の確認
- Bot トークンの定期的な更新

## 12. 利用者向けドキュメント

利用者には以下の基本コマンドを案内：

- `!ヘルプ` - 基本的な使い方
- `!サポート` - 問い合わせ先
- `!バージョン` - Bot情報

## 問い合わせ

技術的な問題やサポートが必要な場合は、システム管理者までお問い合わせください。 