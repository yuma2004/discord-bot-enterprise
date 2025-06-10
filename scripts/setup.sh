#!/bin/bash

# Discord Bot Enterprise - Supabase CLI セットアップスクリプト
# このスクリプトはローカル開発環境を簡単にセットアップします

set -e

echo "🚀 Discord Bot Enterprise セットアップを開始します..."

# 色付きの出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# エラーハンドリング
handle_error() {
    echo -e "${RED}❌ エラーが発生しました: $1${NC}"
    exit 1
}

# 成功メッセージ
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 警告メッセージ
warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# 情報メッセージ
info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# 前提条件のチェック
echo "📋 前提条件をチェックしています..."

# Node.js のチェック
if ! command -v node &> /dev/null; then
    handle_error "Node.js がインストールされていません。Node.js 16以上をインストールしてください。"
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    handle_error "Node.js のバージョンが古すぎます (現在: v$NODE_VERSION)。Node.js 16以上が必要です。"
fi
success "Node.js v$(node --version) が利用可能です"

# Python のチェック
if ! command -v python3 &> /dev/null; then
    handle_error "Python 3 がインストールされていません。Python 3.8以上をインストールしてください。"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    handle_error "Python のバージョンが古すぎます (現在: $PYTHON_VERSION)。Python 3.8以上が必要です。"
fi
success "Python $(python3 --version) が利用可能です"

# Docker のチェック
if ! command -v docker &> /dev/null; then
    handle_error "Docker がインストールされていません。Docker Desktop をインストールして起動してください。"
fi

if ! docker ps &> /dev/null; then
    handle_error "Docker が起動していません。Docker Desktop を起動してください。"
fi
success "Docker が利用可能です"

# Git のチェック
if ! command -v git &> /dev/null; then
    warning "Git がインストールされていません。バージョン管理を行う場合はGitをインストールしてください。"
else
    success "Git が利用可能です"
fi

echo ""

# Supabase CLI のインストール確認
echo "🔧 Supabase CLI をセットアップしています..."

if ! command -v supabase &> /dev/null; then
    info "Supabase CLI をインストールしています..."
    if command -v npm &> /dev/null; then
        npm install -g supabase || handle_error "Supabase CLI のインストールに失敗しました"
    else
        handle_error "npm が利用できません。Node.js とnpm を正しくインストールしてください。"
    fi
else
    success "Supabase CLI は既にインストールされています"
fi

# Supabase CLI のバージョン確認
SUPABASE_VERSION=$(supabase --version 2>/dev/null || echo "unknown")
success "Supabase CLI バージョン: $SUPABASE_VERSION"

echo ""

# プロジェクトの依存関係セットアップ
echo "📦 プロジェクトの依存関係をセットアップしています..."

# Node.js の依存関係
if [ -f "package.json" ]; then
    info "Node.js の依存関係をインストールしています..."
    npm install || handle_error "Node.js 依存関係のインストールに失敗しました"
    success "Node.js 依存関係のインストールが完了しました"
else
    warning "package.json が見つかりません。npm install をスキップします。"
fi

# Python の依存関係
if [ -f "requirements.txt" ]; then
    info "Python の依存関係をインストールしています..."
    
    # 仮想環境の作成
    if [ ! -d "venv" ]; then
        info "Python 仮想環境を作成しています..."
        python3 -m venv venv || handle_error "仮想環境の作成に失敗しました"
    fi
    
    # 仮想環境のアクティベート
    source venv/bin/activate || source venv/Scripts/activate
    
    # pip のアップグレード
    pip install --upgrade pip
    
    # 依存関係のインストール
    pip install -r requirements.txt || handle_error "Python 依存関係のインストールに失敗しました"
    success "Python 依存関係のインストールが完了しました"
else
    warning "requirements.txt が見つかりません。pip install をスキップします。"
fi

echo ""

# Supabase プロジェクトの初期化
echo "🏗️ Supabase プロジェクトを初期化しています..."

if [ ! -f "supabase/config.toml" ]; then
    info "Supabase プロジェクトを初期化しています..."
    supabase init || handle_error "Supabase プロジェクトの初期化に失敗しました"
    success "Supabase プロジェクトの初期化が完了しました"
else
    success "Supabase プロジェクトは既に初期化されています"
fi

echo ""

# 環境変数ファイルのセットアップ
echo "⚙️ 環境変数をセットアップしています..."

if [ ! -f ".env" ]; then
    if [ -f "env_local_example.txt" ]; then
        info "環境変数ファイルを作成しています..."
        cp env_local_example.txt .env || handle_error "環境変数ファイルの作成に失敗しました"
        success "環境変数ファイル (.env) を作成しました"
        warning "⚠️ .env ファイルを編集して、必要な設定値を入力してください"
    else
        warning "env_local_example.txt が見つかりません。手動で .env ファイルを作成してください。"
    fi
else
    success "環境変数ファイル (.env) は既に存在します"
fi

echo ""

# Supabase ローカル環境の起動
echo "🚀 Supabase ローカル環境を起動しています..."

info "Supabase ローカル環境を起動中... (初回は時間がかかります)"
supabase start || handle_error "Supabase ローカル環境の起動に失敗しました"

success "Supabase ローカル環境が起動しました"

echo ""

# データベースマイグレーションの実行
echo "🗄️ データベースマイグレーションを実行しています..."

if [ -f "supabase/migrations/20240101000000_init_discord_bot.sql" ]; then
    info "初期マイグレーションを適用しています..."
    supabase db reset --db-url postgresql://postgres:postgres@127.0.0.1:54322/postgres || warning "マイグレーションの適用に失敗しました。手動で実行してください。"
    success "データベースマイグレーションが完了しました"
else
    warning "マイグレーションファイルが見つかりません。手動でマイグレーションを実行してください。"
fi

echo ""

# セットアップ完了
echo -e "${GREEN}🎉 セットアップが完了しました！${NC}"
echo ""
echo "次のステップ:"
echo -e "${BLUE}1.${NC} .env ファイルを編集して Discord Bot Token を設定してください"
echo -e "${BLUE}2.${NC} Supabase Studio (http://127.0.0.1:54323) でデータベースを確認してください"
echo -e "${BLUE}3.${NC} 以下のコマンドで Bot を起動してください:"
echo ""
echo -e "${YELLOW}  # 仮想環境をアクティベート (Linux/macOS)${NC}"
echo -e "${YELLOW}  source venv/bin/activate${NC}"
echo ""
echo -e "${YELLOW}  # 仮想環境をアクティベート (Windows)${NC}"
echo -e "${YELLOW}  venv\\Scripts\\activate${NC}"
echo ""
echo -e "${YELLOW}  # Bot を起動${NC}"
echo -e "${YELLOW}  python main.py${NC}"
echo ""
echo "便利なコマンド:"
echo -e "${BLUE}  npm run studio${NC}     - Supabase Studio を開く"
echo -e "${BLUE}  npm run status${NC}     - Supabase の状態を確認"
echo -e "${BLUE}  npm run stop${NC}       - Supabase を停止"
echo -e "${BLUE}  npm run logs${NC}       - Supabase のログを表示"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}" 