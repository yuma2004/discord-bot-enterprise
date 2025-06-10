# 🚀 Discord Bot Enterprise - 本番環境デプロイ手順書

## 📋 **概要**

この手順書では、GitHub CLI、Supabase CLI、Koyeb CLIを使用してDiscord Bot Enterpriseを本番環境にデプロイする手順を説明します。

---

## 🎯 **前提条件**

### **必要なアカウント**
- ✅ [GitHub](https://github.com/) アカウント
- ✅ [Supabase](https://supabase.com/) アカウント  
- ✅ [Koyeb](https://app.koyeb.com/) アカウント
- ✅ [Discord Developer Portal](https://discord.com/developers/applications) アカウント

### **必要なCLIツール**
- ✅ GitHub CLI (`gh`) - インストール済み
- ✅ Supabase CLI - プロジェクトディレクトリに配置済み (`./supabase.exe`)
- ✅ Koyeb CLI - プロジェクトディレクトリに配置済み (`./koyeb.exe`)

---

## 🔑 **手順1: Discord Bot設定**

### **1-1: Discord Botアプリケーション作成**
1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリック
3. アプリケーション名を入力（例: "企業用Discord Bot"）
4. 「Bot」セクションに移動
5. 「Add Bot」をクリック
6. **BOT TOKEN** をコピーして保存

### **1-2: 必要な権限設定**
```
Bot Permissions:
✅ Send Messages
✅ Use Slash Commands
✅ Read Message History
✅ View Channels
✅ Add Reactions
✅ Embed Links
✅ Manage Messages
```

---

## 🗄️ **手順2: Supabaseプロジェクト設定**

### **2-1: Supabaseプロジェクト作成**
1. [Supabase](https://supabase.com/dashboard) にアクセス
2. 「New Project」をクリック
3. プロジェクト情報を入力:
   - **Name**: `discord-bot-enterprise`
   - **Database Password**: 強力なパスワードを設定
   - **Region**: `Northeast Asia (Tokyo)`

### **2-2: データベース情報取得**
プロジェクト作成後、以下の情報を取得:
```
✅ Project URL: https://your-project.supabase.co
✅ Anon Key: (公開キー)
✅ Service Role Key: (サービスロールキー)
✅ Database URL: postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

### **2-3: データベーススキーマ設定**
1. Supabase SQL Editorで以下を実行:

```sql
-- ユーザーテーブル
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 日報テーブル
CREATE TABLE daily_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    discord_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    content TEXT NOT NULL,
    parsed_data JSONB DEFAULT '{}',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, date)
);

-- タスクテーブル
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    discord_id VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(10) DEFAULT '中',
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 出勤テーブル
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    discord_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    clock_in TIMESTAMP,
    clock_out TIMESTAMP,
    break_start TIMESTAMP,
    break_end TIMESTAMP,
    total_work_hours DECIMAL(4,2),
    overtime_hours DECIMAL(4,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'absent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, date)
);

-- 設定テーブル
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ☁️ **手順3: Koyebプロジェクト設定**

### **3-1: Koyeb API Token作成**
1. [Koyeb Dashboard](https://app.koyeb.com/user/settings/api) にアクセス
2. 「Create API Token」をクリック
3. トークン名を入力（例: "discord-bot-cli"）
4. **API Token** をコピーして保存

### **3-2: CLI認証**
```powershell
# Koyeb CLIでログイン
./koyeb.exe login
# APIトークンを入力
```

---

## 🚀 **手順4: 環境変数設定**

### **4-1: 本番環境変数ファイル作成**
`env_production_example.txt`をベースに実際の設定値で`.env`ファイルを作成:

```bash
# Discord Bot 設定
DISCORD_TOKEN=your_actual_discord_token
DISCORD_GUILD_ID=your_guild_id

# Supabase 設定
DATABASE_URL=postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# アプリケーション設定
ENVIRONMENT=production
DEBUG=false
TIMEZONE=Asia/Tokyo
DAILY_REPORT_TIME=17:00
LOG_LEVEL=INFO

# 管理者設定
ADMIN_USER_IDS=123456789012345678
```

---

## 🔧 **手順5: Koyebデプロイ実行**

### **5-1: アプリケーション作成**
```powershell
# アプリケーション作成
./koyeb.exe apps create discord-bot-enterprise

# サービス作成・デプロイ
./koyeb.exe services create discord-bot-service \
  --app discord-bot-enterprise \
  --git github.com/yuma2004/discord-bot-enterprise \
  --git-branch master \
  --instance-type micro \
  --regions fra \
  --env DISCORD_TOKEN=your_token \
  --env DATABASE_URL=your_database_url \
  --env SUPABASE_URL=your_supabase_url \
  --env SUPABASE_ANON_KEY=your_anon_key \
  --env ENVIRONMENT=production \
  --env DEBUG=false \
  --env TIMEZONE=Asia/Tokyo
```

### **5-2: デプロイ確認**
```powershell
# サービス状況確認
./koyeb.exe services describe discord-bot-service

# ログ確認
./koyeb.exe services logs discord-bot-service --since 30m

# デプロイメント一覧
./koyeb.exe deployments list --service discord-bot-service
```

---

## 📊 **手順6: 動作確認**

### **6-1: Discord Bot確認**
1. Discord サーバーに Bot を招待
2. 基本コマンドをテスト:
   ```
   !ping
   !info
   !ヘルプ
   ```

### **6-2: データベース接続確認**
```
!タスク追加 テストタスク
!タスク一覧
!日報 今日のテスト日報です
```

### **6-3: 管理機能確認**
```
!統計 (管理者のみ)
!ユーザー一覧 (管理者のみ)
```

---

## 🛠️ **トラブルシューティング**

### **よくある問題と解決策**

#### **Bot が応答しない**
- Discord Token が正しいか確認
- Bot 権限が適切に設定されているか確認
- Koyeb ログでエラーを確認

#### **データベース接続エラー**
- DATABASE_URL が正しいか確認
- Supabase プロジェクトが稼働中か確認
- ネットワーク制限がないか確認

#### **デプロイが失敗する**
- GitHub リポジトリがパブリックか確認
- Dockerfile の構文をチェック
- 環境変数が正しく設定されているか確認

### **ログ確認コマンド**
```powershell
# 詳細ログ表示
./koyeb.exe services logs discord-bot-service --since 1h

# エラーのみ表示
./koyeb.exe services logs discord-bot-service --since 30m | findstr ERROR
```

---

## 📈 **監視とメンテナンス**

### **定期確認項目**
- ✅ サービス稼働状況
- ✅ エラーログ監視
- ✅ データベース使用量
- ✅ API使用制限

### **更新デプロイ**
```powershell
# GitHub に新しいコードをプッシュ後
./koyeb.exe services redeploy discord-bot-service
```

---

## 🎉 **完了チェックリスト**

- [ ] Discord Bot が正常に起動
- [ ] 基本コマンドが動作
- [ ] データベース接続が正常
- [ ] 日報機能が動作
- [ ] タスク管理が動作
- [ ] 出勤管理が動作
- [ ] リマインド機能が動作
- [ ] 管理者機能が動作

---

## 📞 **サポート**

デプロイで問題が発生した場合:
1. 公式ドキュメントを確認
   - [Koyeb Documentation](https://docs.koyeb.com/)
   - [Supabase Documentation](https://supabase.com/docs)
2. ログファイルを確認
3. GitHub Issues で報告

---

**🎊 これで本番環境への Discord Bot Enterprise デプロイが完了です！** 