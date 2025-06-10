# Koyeb + Supabase デプロイガイド

## 1. Supabase セットアップ

### 1-1. Supabaseプロジェクト作成

1. [Supabase](https://supabase.com/) でアカウント作成
2. 「New Project」でプロジェクト作成
3. データベースパスワードを設定
4. プロジェクト作成完了を待つ

### 1-2. データベース情報取得

プロジェクトの Settings → Database で以下を確認：

- **Host**: `db.xxx.supabase.co`
- **Database name**: `postgres`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: 設定したパスワード

### 1-3. データベースURL作成

```
postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

## 2. Koyeb セットアップ

### 2-1. Koyebアカウント作成

1. [Koyeb](https://www.koyeb.com/) でアカウント作成
2. GitHubアカウントと連携

### 2-2. アプリケーション作成

1. Koyebダッシュボードで「Create App」
2. GitHubリポジトリを選択
3. 以下の設定を行う：

**Build Configuration:**
- **Build command**: `docker build -t app .`
- **Run command**: `python main.py`

**Environment Variables:**
```
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
LOG_LEVEL=INFO
TIMEZONE=Asia/Tokyo
DAILY_REPORT_TIME=17:00
MEETING_REMINDER_MINUTES=15
GOOGLE_CLIENT_ID=your_google_client_id (オプション)
GOOGLE_CLIENT_SECRET=your_google_client_secret (オプション)
GOOGLE_CALENDAR_ID=your_calendar_id (オプション)
```

### 2-3. デプロイ設定

**Regions:** Tokyo (asia-northeast1)
**Instance Type:** Nano (512MB RAM) - 無料枠内

## 3. コード修正（PostgreSQL対応）

### 3-1. main.py の修正

```python
# main.py の先頭付近
import os

# データベースの切り替え
if os.getenv('DATABASE_URL') and 'postgres' in os.getenv('DATABASE_URL'):
    from database_postgres import postgres_db_manager as db_manager
    from database_postgres import postgres_user_repo as user_repo
    logger.info("PostgreSQL (Supabase) を使用します")
else:
    from database import db_manager, user_repo
    logger.info("SQLite を使用します")
```

### 3-2. 環境変数チェック

```python
# 必要な環境変数の確認
required_vars = ['DISCORD_BOT_TOKEN', 'DATABASE_URL']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"環境変数が不足: {missing_vars}")
    exit(1)
```

## 4. デプロイ手順

### 4-1. リポジトリ準備

```bash
# 新しいファイルをコミット
git add Dockerfile database_postgres.py requirements.txt
git commit -m "Add Koyeb + Supabase support"
git push origin main
```

### 4-2. Koyebでデプロイ

1. Koyebダッシュボードで「Deploy」
2. ビルドとデプロイの完了を待つ
3. ログでエラーがないか確認

### 4-3. データベース初期化

初回デプロイ後、Supabaseの SQL Editor で以下を実行：

```sql
-- または、Bot側で自動実行されるのを確認
SELECT * FROM users;
```

## 5. 監視とログ

### 5-1. Koyebでのログ確認

- Koyebダッシュボード → App → Logs
- リアルタイムでログ確認可能

### 5-2. Supabaseでのデータ確認

- Supabase → Table Editor でデータ確認
- Authentication → Users でユーザー管理

## 6. ドメイン設定（オプション）

### 6-1. カスタムドメイン

Koyebダッシュボード → App → Domains で独自ドメイン設定可能

## 7. スケールアップ

### 7-1. 利用量に応じた調整

**Koyeb:**
- Nano → Micro → Small へのスケールアップ
- 複数インスタンスでの冗長化

**Supabase:**
- 無料枠: 50MB DB、50,000 月間API実行
- Pro: $25/月 〜

## 8. トラブルシューティング

### 8-1. よくある問題

**デプロイ失敗:**
```bash
# requirements.txt の依存関係確認
pip install -r requirements.txt
```

**データベース接続エラー:**
- DATABASE_URL の形式確認
- Supabaseプロジェクトの状態確認

**Bot がオフライン:**
- DISCORD_BOT_TOKEN の確認
- Koyebのログ確認

### 8-2. デバッグ方法

```bash
# Koyebログの確認
# ダッシュボード → Logs → Real-time

# 環境変数の確認
echo $DATABASE_URL
```

## 9. コスト見積り

### 9-1. 無料枠での運用

**Koyeb:**
- Nano インスタンス：無料
- 月100時間実行可能

**Supabase:**
- 50MB データベース：無料
- 月50,000 API実行：無料

### 9-2. 有料プラン

**小規模企業（10-20名）:**
- Koyeb Micro: $5-10/月
- Supabase Pro: $25/月
- **合計: $30-35/月**

## 10. 運用のコツ

### 10-1. 定期バックアップ

Supabaseは自動バックアップがあるが、追加で：

```bash
# pg_dump を使用したバックアップ
pg_dump $DATABASE_URL > backup.sql
```

### 10-2. 監視アラート

- Koyebのアプリケーション監視
- Supabaseのメトリクス確認
- Discord Botの生存監視

## 11. 次のステップ

1. **カスタムドメイン設定**
2. **SSL証明書の設定**
3. **ロードバランサーの設定（大規模時）**
4. **監視ツールの導入**

このガイドに従って、企業向けDiscord BotをKoyeb + Supabaseで運用開始できます！ 