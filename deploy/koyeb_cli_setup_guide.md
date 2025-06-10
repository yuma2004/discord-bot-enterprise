# Koyeb CLI を使用した Discord Bot デプロイガイド

このガイドでは、Koyeb CLI を使用して Discord Bot をクラウド環境に完全にデプロイする方法を説明します。

## 前提条件

- Koyeb アカウント（無料プランでも利用可能）
- Git リポジトリ（GitHub, GitLab, Bitbucket）
- Docker Hub アカウント（オプション）
- Supabase プロジェクト

## 1. Koyeb CLI のインストール

### Windows (PowerShell)
```powershell
# Scoopを使用してインストール
scoop bucket add koyeb https://github.com/koyeb/scoop-koyeb.git
scoop install koyeb

# または直接ダウンロード
Invoke-WebRequest -Uri "https://github.com/koyeb/koyeb-cli/releases/latest/download/koyeb-cli_windows_amd64.exe" -OutFile "koyeb.exe"
```

### macOS
```bash
# Homebrewを使用してインストール
brew install koyeb/tap/koyeb

# または curl でインストール
curl -L https://github.com/koyeb/koyeb-cli/releases/latest/download/koyeb-cli_darwin_amd64.tar.gz | tar xz
sudo mv koyeb /usr/local/bin/
```

### Linux
```bash
# APT (Ubuntu/Debian)
curl -fsSL https://cli.koyeb.com/install.sh | sh

# または手動でダウンロード
curl -L https://github.com/koyeb/koyeb-cli/releases/latest/download/koyeb-cli_linux_amd64.tar.gz | tar xz
sudo mv koyeb /usr/local/bin/
```

インストール確認：
```bash
koyeb version
```

## 2. Koyeb CLI の初期設定

### 2.1 API トークンの取得

1. [Koyeb Dashboard](https://app.koyeb.com) にログイン
2. **Settings** → **API** → **Tokens** に移動
3. **Create Token** をクリック
4. トークン名を入力（例：`discord-bot-cli`）
5. 生成されたトークンをコピー

### 2.2 CLI の認証

```bash
# API トークンで認証
koyeb login --token YOUR_API_TOKEN

# または対話形式で認証
koyeb login

# 認証確認
koyeb profile
```

## 3. プロジェクトの準備

### 3.1 Git リポジトリのセットアップ

```bash
# Git リポジトリの初期化（まだの場合）
git init
git add .
git commit -m "Initial commit"

# GitHub にプッシュ
git remote add origin https://github.com/YOUR_USERNAME/discord-bot-enterprise.git
git branch -M main
git push -u origin main
```

### 3.2 Dockerfile の確認

プロジェクトルートに `Dockerfile` があることを確認してください。

### 3.3 ヘルスチェックエンドポイントの追加

`main.py` にヘルスチェック用のエンドポイントを追加：

```python
# main.py に追加（既存のコードに）
from flask import Flask
import threading

# Flask アプリケーション（ヘルスチェック用）
health_app = Flask(__name__)

@health_app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'discord-bot'}, 200

def run_health_server():
    health_app.run(host='0.0.0.0', port=8000, debug=False)

# Bot 起動前に追加
if __name__ == "__main__":
    # ヘルスチェックサーバーを別スレッドで起動
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Bot を起動
    bot.run(Config.DISCORD_TOKEN)
```

## 4. Koyeb でのシークレット管理

### 4.1 シークレットの作成

```bash
# Discord Bot Token
koyeb secrets create discord-token --value "YOUR_DISCORD_BOT_TOKEN"

# Supabase Database URL
koyeb secrets create database-url --value "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"

# Google API認証情報（オプション）
koyeb secrets create google-client-id --value "YOUR_GOOGLE_CLIENT_ID"
koyeb secrets create google-client-secret --value "YOUR_GOOGLE_CLIENT_SECRET"
koyeb secrets create google-calendar-id --value "YOUR_GOOGLE_CALENDAR_ID"
```

### 4.2 シークレットの確認

```bash
# シークレット一覧を表示
koyeb secrets list

# 特定のシークレット詳細
koyeb secrets describe discord-token
```

## 5. アプリケーションのデプロイ

### 5.1 設定ファイルを使用したデプロイ

```bash
# プロジェクトルートで実行
koyeb apps deploy --file koyeb.yaml

# デプロイ状況の確認
koyeb apps list
koyeb services list
```

### 5.2 CLI コマンドを使用したデプロイ

```bash
# Git リポジトリから直接デプロイ
koyeb services create discord-bot \
  --app discord-bot-enterprise \
  --git-repository https://github.com/YOUR_USERNAME/discord-bot-enterprise.git \
  --git-branch main \
  --instance-type nano \
  --region fra \
  --port 8000:http \
  --env DISCORD_TOKEN=@discord-token \
  --env DATABASE_URL=@database-url \
  --env ENVIRONMENT=production \
  --env BOT_PREFIX="!" \
  --env TIMEZONE=Asia/Tokyo \
  --env DAILY_REPORT_TIME="17:00" \
  --env DEBUG=false \
  --env LOG_LEVEL=INFO \
  --health-check-path /health
```

### 5.3 Docker Hub を使用したデプロイ

```bash
# Docker イメージをビルドしてプッシュ
docker build -t YOUR_USERNAME/discord-bot-enterprise .
docker push YOUR_USERNAME/discord-bot-enterprise

# Docker Hub からデプロイ
koyeb services create discord-bot \
  --app discord-bot-enterprise \
  --docker YOUR_USERNAME/discord-bot-enterprise:latest \
  --instance-type nano \
  --region fra \
  --port 8000:http \
  --env DISCORD_TOKEN=@discord-token \
  --env DATABASE_URL=@database-url \
  --health-check-path /health
```

## 6. デプロイ後の管理

### 6.1 サービスの状態確認

```bash
# アプリケーション一覧
koyeb apps list

# サービス一覧
koyeb services list

# サービス詳細
koyeb services describe discord-bot

# デプロイメント一覧
koyeb deployments list --service discord-bot
```

### 6.2 ログの確認

```bash
# リアルタイムログ
koyeb services logs discord-bot --follow

# 過去のログ
koyeb services logs discord-bot --since 1h

# 特定のインスタンスのログ
koyeb instances logs INSTANCE_ID
```

### 6.3 サービスの更新

```bash
# 環境変数の更新
koyeb services update discord-bot --env NEW_ENV_VAR=value

# スケールの変更
koyeb services update discord-bot --scale 2

# インスタンスタイプの変更
koyeb services update discord-bot --instance-type small

# 再デプロイ
koyeb services redeploy discord-bot
```

## 7. 自動デプロイの設定

### 7.1 GitHub Actions との連携

`.github/workflows/deploy.yml` を作成：

```yaml
name: Deploy to Koyeb

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Koyeb CLI
      run: |
        curl -fsSL https://cli.koyeb.com/install.sh | sh
        sudo mv koyeb /usr/local/bin/
    
    - name: Deploy to Koyeb
      env:
        KOYEB_TOKEN: ${{ secrets.KOYEB_TOKEN }}
      run: |
        koyeb login --token $KOYEB_TOKEN
        koyeb services redeploy discord-bot
```

### 7.2 Git Webhook の設定

```bash
# 自動デプロイを有効化
koyeb services update discord-bot --git-auto-deploy
```

## 8. 監視とアラート

### 8.1 ヘルスチェックの設定

```bash
# ヘルスチェックの更新
koyeb services update discord-bot \
  --health-check-path /health \
  --health-check-port 8000 \
  --health-check-protocol http
```

### 8.2 メトリクスの確認

```bash
# CPU/メモリ使用量
koyeb services metrics discord-bot --metric cpu
koyeb services metrics discord-bot --metric memory

# ネットワーク統計
koyeb services metrics discord-bot --metric network
```

## 9. トラブルシューティング

### 9.1 一般的な問題と解決方法

#### デプロイが失敗する場合

```bash
# デプロイメントの詳細確認
koyeb deployments describe DEPLOYMENT_ID

# ビルドログの確認
koyeb services logs discord-bot --deployment DEPLOYMENT_ID

# サービスの再起動
koyeb services restart discord-bot
```

#### Bot が起動しない場合

```bash
# 環境変数の確認
koyeb services describe discord-bot | grep -A 20 "Environment"

# シークレットの確認
koyeb secrets list

# ログでエラーを確認
koyeb services logs discord-bot --since 30m
```

#### データベース接続エラー

```bash
# DATABASE_URL の確認
koyeb secrets describe database-url

# Supabase接続テスト
koyeb services exec discord-bot -- python -c "import psycopg2; psycopg2.connect('YOUR_DATABASE_URL')"
```

### 9.2 パフォーマンス最適化

```bash
# リソース使用量の確認
koyeb services metrics discord-bot --metric memory --since 1h

# インスタンスタイプのアップグレード
koyeb services update discord-bot --instance-type small

# スケールアウト
koyeb services update discord-bot --scale 2
```

## 10. 費用最適化

### 10.1 リソース管理

```bash
# 現在の費用確認
koyeb billing usage

# インスタンスタイプ一覧と価格
koyeb instance-types list

# 使用していないサービスの削除
koyeb services delete OLD_SERVICE_NAME
```

### 10.2 スケジューリング

```bash
# 開発環境の自動停止（平日夜間・週末）
koyeb services update discord-bot-dev --schedule "0 22 * * 1-5"
```

## 11. バックアップとリストア

### 11.1 設定のバックアップ

```bash
# サービス設定をエクスポート
koyeb services describe discord-bot --output yaml > backup/service-config.yaml

# シークレットのリスト保存
koyeb secrets list --output json > backup/secrets-list.json
```

### 11.2 災害復旧

```bash
# 新しい地域にサービスを複製
koyeb services create discord-bot-backup \
  --app discord-bot-enterprise \
  --region was \
  --git-repository https://github.com/YOUR_USERNAME/discord-bot-enterprise.git
```

## 12. セキュリティ設定

### 12.1 アクセス制御

```bash
# APIトークンの権限確認
koyeb tokens list

# 新しい制限付きトークンの作成
koyeb tokens create deployment-only --scope deployments
```

### 12.2 環境分離

```bash
# 本番環境とは別の開発アプリを作成
koyeb apps create discord-bot-dev

# 開発環境用のサービス
koyeb services create discord-bot \
  --app discord-bot-dev \
  --git-branch develop \
  --env ENVIRONMENT=development
```

## 13. 便利なスクリプト

### 13.1 クイックデプロイスクリプト

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Discord Bot をKoyebにデプロイしています..."

# 最新のコードをプッシュ
git add .
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main

# Koyebで再デプロイ
koyeb services redeploy discord-bot

echo "✅ デプロイが完了しました！"
```

### 13.2 ステータス確認スクリプト

```bash
#!/bin/bash
# scripts/status.sh

echo "📊 Koyeb サービス状況"
echo "======================="

koyeb services list
echo ""

echo "📈 最新のメトリクス"
echo "=================="
koyeb services metrics discord-bot --metric cpu --since 1h | tail -5
echo ""

echo "📝 最新のログ"
echo "============"
koyeb services logs discord-bot --since 10m | tail -10
```

---

このガイドに従うことで、Koyeb CLI を使用して Discord Bot を効率的にデプロイ・管理できます。無料プランでも月間100時間まで利用可能で、小規模なBotには十分です。

何か問題が発生した場合は、[Koyeb ドキュメント](https://www.koyeb.com/docs) も参照してください。 