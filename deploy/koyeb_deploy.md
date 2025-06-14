# Koyeb Deployment Guide - Discord Bot Enterprise v3.0.0

## 🚀 Koyeb + PostgreSQL デプロイメントガイド

このガイドでは、Discord Bot Enterprise v3.0.0をKoyebにデプロイし、PostgreSQLデータベースに接続する手順を説明します。

## 📋 前提条件

- Koyebアカウント
- GitHubリポジトリ（公開または組織のプライベートリポジトリ）
- PostgreSQLデータベース（Supabase、Railway、Neon等）
- Discord Bot Token

## 🛠️ Step 1: PostgreSQLデータベースの準備

### Supabaseを使用する場合

1. [Supabase](https://supabase.com)でプロジェクト作成
2. データベース設定で以下を確認：
   ```
   Database URL: postgresql://postgres:[password]@[host]:5432/postgres
   ```
3. SQL Editorで初期設定（オプション）：
   ```sql
   -- Create specific user for bot (optional)
   CREATE USER discord_bot WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE postgres TO discord_bot;
   ```

### 他のPostgreSQLプロバイダー

- **Railway**: [railway.app](https://railway.app)
- **Neon**: [neon.tech](https://neon.tech)
- **Heroku Postgres**: [heroku.com](https://heroku.com)

## 🔧 Step 2: Koyebプロジェクト設定

### 2.1 GitHubリポジトリの準備

1. リポジトリをGitHubにプッシュ：
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Discord Bot Enterprise v3.0.0"
   git branch -M main
   git remote add origin https://github.com/your-username/discord-bot-enterprise.git
   git push -u origin main
   ```

### 2.2 Koyebアプリケーション作成

1. [Koyeb Console](https://app.koyeb.com)にログイン
2. "Create App" をクリック
3. GitHub連携を選択
4. リポジトリを選択：`your-username/discord-bot-enterprise`
5. ブランチ：`main`

### 2.3 Build設定

- **Build command**: `pip install -r requirements.txt`
- **Run command**: `python main.py`
- **Dockerfile**: `Dockerfile` (自動検出)

### 2.4 Environment Variables設定

Koyeb Consoleで以下の環境変数を設定：

#### 必須設定
```bash
ENVIRONMENT=production
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_guild_id
DATABASE_URL=postgresql://username:password@host:5432/database
LOG_LEVEL=INFO
TIMEZONE=Asia/Tokyo
HEALTH_CHECK_PORT=8000
```

#### オプション設定（Google Calendar連携）
```bash
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_CALENDAR_ID=your_calendar_id
```

### 2.5 Secrets設定

機密情報は環境変数ではなくSecretsとして設定：

1. Koyeb Console → Settings → Secrets
2. 以下のSecretsを作成：
   - `DISCORD_TOKEN`: Discord Bot Token
   - `DATABASE_URL`: PostgreSQL接続URL
   - `GOOGLE_CLIENT_SECRET`: Google API Secret（使用する場合）

## 🔧 Step 3: ヘルスチェック設定

### 3.1 Koyebヘルスチェック

`koyeb.yaml`に以下が設定済み：
```yaml
health_check:
  http:
    port: 8000
    path: /health
```

### 3.2 ヘルスチェックエンドポイント

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics`
- **Service Info**: `GET /`

## 🚀 Step 4: デプロイ実行

### 4.1 自動デプロイ

1. Koyeb Console → Deployments → "Deploy"
2. ビルドログを確認
3. デプロイ完了を待機

### 4.2 手動デプロイ（CLI使用）

```bash
# Koyeb CLI インストール
curl -fsSL https://github.com/koyeb/koyeb-cli/raw/main/install.sh | sh

# 認証
koyeb auth login

# デプロイ
koyeb app deploy discord-bot-enterprise \
  --git github.com/your-username/discord-bot-enterprise \
  --git-branch main \
  --instance-type nano \
  --env ENVIRONMENT=production \
  --env DISCORD_TOKEN=$DISCORD_TOKEN \
  --env DATABASE_URL=$DATABASE_URL \
  --port 8000:http \
  --health-check-path /health
```

## 📊 Step 5: デプロイ後の確認

### 5.1 ヘルスチェック確認

```bash
# アプリURLを確認
curl https://your-app-name-your-org.koyeb.app/health

# 期待される応答
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "type": "postgresql"
    }
  }
}
```

### 5.2 Discord Bot動作確認

1. DiscordサーバーでBotがオンラインか確認
2. `!ping` コマンドでレスポンス確認
3. `!health` コマンドでシステム状態確認

### 5.3 ログ確認

```bash
# Koyeb Console → Logs
# または CLI
koyeb logs -a discord-bot-enterprise -f
```

## 🔧 Step 6: トラブルシューティング

### 6.1 よくある問題

#### データベース接続エラー
```bash
# ログでPostgreSQL接続エラーが出る場合
# 1. DATABASE_URLが正しいか確認
# 2. PostgreSQLデータベースが起動しているか確認
# 3. ファイアウォール設定確認
```

#### Bot起動エラー
```bash
# Discord Token関連エラー
# 1. DISCORD_TOKENが正しく設定されているか確認
# 2. Bot権限が適切に設定されているか確認
# 3. GuildIDが正しいか確認
```

#### ヘルスチェック失敗
```bash
# Port 8000が正しく設定されているか確認
# Flask依存関係がインストールされているか確認
```

### 6.2 デバッグモード

一時的にログレベルを上げる：
```bash
LOG_LEVEL=DEBUG
```

### 6.3 手動スケーリング

```bash
# インスタンス数調整
koyeb app scale discord-bot-enterprise --instances 1
```

## 📈 Step 7: 監視・メンテナンス

### 7.1 監視設定

1. Koyeb Console → Monitoring
2. アラート設定（CPU、メモリ、レスポンス時間）
3. ログ監視

### 7.2 自動再起動設定

`koyeb.yaml`に設定済み：
```yaml
restart_policy: always
```

### 7.3 バックアップ

PostgreSQLデータベースの定期バックアップ設定を推奨。

## 🎉 完了！

これで Discord Bot Enterprise v3.0.0 が Koyeb + PostgreSQL 環境で稼働します。

## 📞 サポート

問題が発生した場合：
1. Koyebログを確認
2. PostgreSQLデータベースの状態確認  
3. Discord Bot権限の確認
4. 環境変数の設定確認

---

**🚀 Discord Bot Enterprise v3.0.0 - Production Ready!**