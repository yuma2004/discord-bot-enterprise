# Supabase CLI を使用した Discord Bot セットアップガイド

このガイドでは、Supabase CLI を使用して Discord Bot のローカル開発環境から本番環境までを完全にセットアップする方法を説明します。

## 前提条件

- Node.js 16 以上
- Python 3.8 以上
- Docker Desktop
- Git

## 1. Supabase CLI のインストール

### Windows (PowerShell)
```powershell
# npm経由でインストール
npm install -g supabase

# または Chocolatey経由
choco install supabase
```

### macOS
```bash
# Homebrew経由
brew install supabase/tap/supabase

# または npm経由
npm install -g supabase
```

### Linux
```bash
# npm経由
npm install -g supabase

# または直接ダウンロード
curl -sL https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz | tar -xz && sudo mv supabase /usr/local/bin/
```

インストール確認：
```bash
supabase --version
```

## 2. プロジェクトのセットアップ

### 2.1 Supabase プロジェクトの初期化

```bash
# プロジェクトディレクトリに移動
cd /path/to/your/discord-bot

# Supabase プロジェクトを初期化
supabase init

# 設定ファイルが作成されることを確認
ls supabase/
```

### 2.2 ローカル開発環境の起動

```bash
# Docker が起動していることを確認してから実行
supabase start

# 初回起動時は Docker イメージのダウンロードに時間がかかります
# 完了すると以下のような出力が表示されます：
# Started supabase local development setup.
#
#          API URL: http://127.0.0.1:54321
#      GraphQL URL: http://127.0.0.1:54321/graphql/v1
#           DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
#       Studio URL: http://127.0.0.1:54323
#     Inbucket URL: http://127.0.0.1:54324
#       JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
#        anon key: ey...
# service_role key: ey...
```

### 2.3 環境変数の設定

```bash
# ローカル開発用の環境変数ファイルをコピー
cp env_local_example.txt .env

# .env ファイルを編集して必要な値を設定
# DATABASE_URL は supabase start の出力から取得した DB URL を使用
```

## 3. データベースマイグレーションの実行

### 3.1 初期マイグレーションの適用

```bash
# マイグレーションを実行
supabase db reset

# または個別にマイグレーションを適用
supabase migration up
```

### 3.2 Supabase Studio でデータベースを確認

ブラウザで http://127.0.0.1:54323 にアクセスして、作成されたテーブルを確認できます。

## 4. Discord Bot の開発・テスト

### 4.1 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4.2 Bot の起動

```bash
python main.py
```

### 4.3 動作確認

Discord サーバーで以下のコマンドをテストしてください：

```
!ping
!info
!日報 今日は新機能の開発を行いました
!タスク追加 "プロジェクト資料作成" "明日まで" 高
!出勤  # ボタンが表示されるのでクリック
```

## 5. 本番環境への展開

### 5.1 Supabase プロジェクトの作成

1. [Supabase Dashboard](https://supabase.com/dashboard) にアクセス
2. "New project" をクリック
3. プロジェクト名とパスワードを設定
4. プロジェクトが作成されるまで待機（約2分）

### 5.2 本番環境との連携

```bash
# プロジェクト ID を確認（Dashboard の Settings > General から取得）
supabase link --project-ref your-project-id

# ローカルの変更を本番環境に反映
supabase db push

# または新しいマイグレーションとして保存
supabase migration new production_schema
```

### 5.3 本番環境変数の設定

本番環境用の環境変数：

```bash
# Supabase Dashboard から取得
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

## 6. Koyeb へのデプロイ（推奨）

### 6.1 環境変数の設定

Koyeb の環境変数設定で以下を追加：

```
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
ENVIRONMENT=production
```

### 6.2 デプロイコマンド

```bash
# Git リポジトリにプッシュ
git add .
git commit -m "Add Supabase CLI configuration"
git push origin main

# Koyeb が自動的にデプロイを実行
```

## 7. 日常的な開発ワークフロー

### 7.1 開発開始時

```bash
# ローカル Supabase を起動
supabase start

# Bot を起動
python main.py
```

### 7.2 データベーススキーマの変更

```bash
# 新しいマイグレーションを作成
supabase migration new add_new_feature

# マイグレーションファイルを編集
# supabase/migrations/[timestamp]_add_new_feature.sql

# ローカルで適用
supabase migration up

# 本番環境に反映
supabase db push
```

### 7.3 開発終了時

```bash
# Supabase ローカル環境を停止
supabase stop

# または完全にリセット（データ削除）
supabase stop --no-backup
```

## 8. トラブルシューティング

### 8.1 Docker 関連の問題

```bash
# Docker Desktop が起動していることを確認
docker --version

# Docker コンテナの状態確認
docker ps

# Supabase コンテナを再起動
supabase stop
supabase start
```

### 8.2 データベース接続エラー

```bash
# データベース接続をテスト
supabase db reset

# ログを確認
supabase logs
```

### 8.3 マイグレーション関連の問題

```bash
# マイグレーション状態を確認
supabase migration list

# 特定のマイグレーションにリセット
supabase db reset --db-url [DATABASE_URL]
```

## 9. 便利なコマンド

### 9.1 データベース操作

```bash
# データベースに直接接続
supabase db connect

# SQL ファイルを実行
supabase db execute --file custom_script.sql

# データベースをダンプ
supabase db dump -f backup.sql
```

### 9.2 開発用コマンド

```bash
# 設定を確認
supabase status

# ログを監視
supabase logs -f

# TypeScript 型定義を生成（将来的にTypeScript化する場合）
supabase gen types typescript --local > types/supabase.ts
```

## 10. セキュリティ設定

### 10.1 Row Level Security (RLS) の確認

Supabase Studio で各テーブルの RLS ポリシーが正しく設定されていることを確認してください。

### 10.2 API キーの管理

```bash
# 環境変数でキーを管理（本番環境）
export SUPABASE_ANON_KEY="your_anon_key"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
```

## 11. 監視とログ

### 11.1 Supabase Dashboard での監視

1. プロジェクト Dashboard にアクセス
2. "Logs" セクションでクエリログを確認
3. "API" セクションで API 使用状況を監視

### 11.2 エラー監視

```python
# Python アプリケーション内でのログ記録
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース操作時のエラーハンドリング
try:
    # データベース操作
    pass
except Exception as e:
    logger.error(f"Database error: {e}")
```

## 12. バックアップとリストア

### 12.1 定期バックアップ

```bash
# 毎日のバックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
supabase db dump -f "backup_${DATE}.sql"

# 古いバックアップファイルを削除（7日以上前）
find . -name "backup_*.sql" -mtime +7 -delete
```

### 12.2 リストア

```bash
# バックアップからリストア
supabase db reset --db-url [DATABASE_URL] --file backup_20240101_120000.sql
```

---

このガイドに従って設定することで、Supabase CLI を使用した完全な開発・本番環境が構築できます。何か問題が発生した場合は、Supabase のドキュメント（https://supabase.com/docs）も参照してください。 