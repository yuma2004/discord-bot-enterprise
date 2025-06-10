#!/bin/bash

# Discord Bot Enterprise - Koyeb デプロイスクリプト
# このスクリプトはKoyeb CLIを使用してDiscord Botをデプロイします

set -e

# 色付きの出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 設定
APP_NAME="discord-bot-enterprise"
SERVICE_NAME="discord-bot"
REPOSITORY_URL=""
INSTANCE_TYPE="nano"
REGION="fra"

# 関数定義
error() {
    echo -e "${RED}❌ エラー: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

header() {
    echo -e "${CYAN}$1${NC}"
}

# ヘルプ表示
show_help() {
    echo "Discord Bot Enterprise - Koyeb デプロイスクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 [オプション] [コマンド]"
    echo ""
    echo "コマンド:"
    echo "  deploy     新規デプロイまたは更新"
    echo "  redeploy   既存サービスの再デプロイ"
    echo "  status     デプロイ状況の確認"
    echo "  logs       サービスログの表示"
    echo "  delete     サービスの削除"
    echo "  secrets    シークレットの管理"
    echo ""
    echo "オプション:"
    echo "  -r, --repository URL  GitリポジトリURL"
    echo "  -i, --instance TYPE   インスタンスタイプ (nano/small/medium)"
    echo "  -g, --region REGION   リージョン (fra/was/sin)"
    echo "  -h, --help           このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 deploy -r https://github.com/user/repo.git"
    echo "  $0 redeploy"
    echo "  $0 status"
}

# 前提条件のチェック
check_prerequisites() {
    header "🔍 前提条件をチェックしています..."
    
    # Koyeb CLI のチェック
    if ! command -v koyeb &> /dev/null; then
        error "Koyeb CLI がインストールされていません。インストールしてください。"
    fi
    success "Koyeb CLI が利用可能です"
    
    # 認証チェック
    if ! koyeb profile &> /dev/null; then
        error "Koyeb CLI にログインしていません。'koyeb login' を実行してください。"
    fi
    success "Koyeb CLI にログイン済みです"
    
    # Git のチェック（リポジトリが設定されている場合）
    if [ -n "$REPOSITORY_URL" ] && ! command -v git &> /dev/null; then
        warning "Git がインストールされていません。"
    fi
    
    # Docker のチェック（ローカルビルドの場合）
    if command -v docker &> /dev/null; then
        success "Docker が利用可能です"
    else
        warning "Docker がインストールされていません（Git デプロイのみ利用可能）"
    fi
}

# シークレットの確認・作成
manage_secrets() {
    header "🔐 シークレットを管理しています..."
    
    local secrets=(
        "discord-token:DISCORD_TOKEN"
        "database-url:DATABASE_URL"
        "google-client-id:GOOGLE_CLIENT_ID"
        "google-client-secret:GOOGLE_CLIENT_SECRET"
        "google-calendar-id:GOOGLE_CALENDAR_ID"
    )
    
    for secret_pair in "${secrets[@]}"; do
        IFS=':' read -r secret_name env_var <<< "$secret_pair"
        
        if koyeb secrets describe "$secret_name" &> /dev/null; then
            success "シークレット '$secret_name' は既に存在します"
        else
            warning "シークレット '$secret_name' が存在しません"
            
            if [ "$secret_name" = "discord-token" ] || [ "$secret_name" = "database-url" ]; then
                error "必須のシークレット '$secret_name' が存在しません。以下のコマンドで作成してください:\nkoyeb secrets create $secret_name --value \"YOUR_VALUE\""
            else
                info "オプションのシークレット '$secret_name' をスキップします"
            fi
        fi
    done
}

# アプリケーションのデプロイ
deploy_app() {
    header "🚀 アプリケーションをデプロイしています..."
    
    # リポジトリURLの確認
    if [ -z "$REPOSITORY_URL" ]; then
        # 現在のGitリポジトリから取得を試行
        if git remote get-url origin &> /dev/null; then
            REPOSITORY_URL=$(git remote get-url origin)
            info "Git リポジトリURL を自動検出: $REPOSITORY_URL"
        else
            error "リポジトリURL が指定されていません。-r オプションで指定してください。"
        fi
    fi
    
    # アプリが既に存在するかチェック
    if koyeb apps describe "$APP_NAME" &> /dev/null; then
        warning "アプリ '$APP_NAME' は既に存在します"
        
        # サービスが存在するかチェック
        if koyeb services describe "$SERVICE_NAME" &> /dev/null; then
            info "既存のサービスを更新します"
            redeploy_service
        else
            info "新しいサービスを作成します"
            create_service
        fi
    else
        info "新しいアプリとサービスを作成します"
        create_app_and_service
    fi
}

# 新しいアプリとサービスの作成
create_app_and_service() {
    info "アプリ '$APP_NAME' を作成しています..."
    
    koyeb apps create "$APP_NAME" || error "アプリの作成に失敗しました"
    success "アプリを作成しました"
    
    create_service
}

# サービスの作成
create_service() {
    info "サービス '$SERVICE_NAME' を作成しています..."
    
    local deploy_cmd="koyeb services create $SERVICE_NAME"
    deploy_cmd+=" --app $APP_NAME"
    deploy_cmd+=" --git-repository $REPOSITORY_URL"
    deploy_cmd+=" --git-branch main"
    deploy_cmd+=" --instance-type $INSTANCE_TYPE"
    deploy_cmd+=" --region $REGION"
    deploy_cmd+=" --port 8000:http"
    deploy_cmd+=" --env DISCORD_TOKEN=@discord-token"
    deploy_cmd+=" --env DATABASE_URL=@database-url"
    deploy_cmd+=" --env ENVIRONMENT=production"
    deploy_cmd+=" --env BOT_PREFIX=!"
    deploy_cmd+=" --env TIMEZONE=Asia/Tokyo"
    deploy_cmd+=" --env DAILY_REPORT_TIME=17:00"
    deploy_cmd+=" --env DEBUG=false"
    deploy_cmd+=" --env LOG_LEVEL=INFO"
    
    # オプションの環境変数（シークレットが存在する場合のみ）
    if koyeb secrets describe "google-client-id" &> /dev/null; then
        deploy_cmd+=" --env GOOGLE_CLIENT_ID=@google-client-id"
    fi
    if koyeb secrets describe "google-client-secret" &> /dev/null; then
        deploy_cmd+=" --env GOOGLE_CLIENT_SECRET=@google-client-secret"
    fi
    if koyeb secrets describe "google-calendar-id" &> /dev/null; then
        deploy_cmd+=" --env GOOGLE_CALENDAR_ID=@google-calendar-id"
    fi
    
    deploy_cmd+=" --health-check-path /health"
    
    eval "$deploy_cmd" || error "サービスの作成に失敗しました"
    success "サービスを作成しました"
}

# サービスの再デプロイ
redeploy_service() {
    info "サービス '$SERVICE_NAME' を再デプロイしています..."
    
    koyeb services redeploy "$SERVICE_NAME" || error "再デプロイに失敗しました"
    success "再デプロイを開始しました"
}

# デプロイ状況の確認
check_deployment() {
    header "📊 デプロイ状況を確認しています..."
    
    # デプロイ完了まで待機
    local max_wait=300  # 5分
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        local status=$(koyeb services describe "$SERVICE_NAME" --output json 2>/dev/null | jq -r '.latest_deployment.status' 2>/dev/null || echo "unknown")
        
        case "$status" in
            "healthy")
                success "デプロイが完了しました！"
                break
                ;;
            "unhealthy"|"error")
                error "デプロイが失敗しました。ログを確認してください。"
                ;;
            "pending"|"deploying")
                info "デプロイ中... ($((wait_time))秒経過)"
                ;;
            *)
                info "状況確認中... ($status)"
                ;;
        esac
        
        sleep 10
        wait_time=$((wait_time + 10))
    done
    
    if [ $wait_time -ge $max_wait ]; then
        warning "デプロイ状況の確認がタイムアウトしました"
    fi
}

# サービス情報の表示
show_status() {
    header "📈 サービス状況"
    
    echo "アプリケーション情報:"
    koyeb apps describe "$APP_NAME" 2>/dev/null || echo "アプリが見つかりません"
    
    echo ""
    echo "サービス情報:"
    koyeb services describe "$SERVICE_NAME" 2>/dev/null || echo "サービスが見つかりません"
    
    echo ""
    echo "最新のデプロイメント:"
    koyeb deployments list --service "$SERVICE_NAME" --limit 3 2>/dev/null || echo "デプロイメント情報を取得できません"
}

# ログの表示
show_logs() {
    header "📝 サービスログ"
    
    info "最新のログを表示しています..."
    koyeb services logs "$SERVICE_NAME" --since 30m || error "ログの取得に失敗しました"
}

# サービスの削除
delete_service() {
    header "🗑️ サービスを削除しています..."
    
    warning "この操作はサービス '$SERVICE_NAME' を完全に削除します。"
    read -p "続行しますか? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        koyeb services delete "$SERVICE_NAME" || error "サービスの削除に失敗しました"
        success "サービスを削除しました"
        
        # アプリが空になった場合は削除するか確認
        local service_count=$(koyeb services list --app "$APP_NAME" --output json 2>/dev/null | jq '.services | length' 2>/dev/null || echo "0")
        if [ "$service_count" = "0" ]; then
            read -p "アプリ '$APP_NAME' も削除しますか? (y/N): " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                koyeb apps delete "$APP_NAME" || warning "アプリの削除に失敗しました"
                success "アプリを削除しました"
            fi
        fi
    else
        info "削除をキャンセルしました"
    fi
}

# ヘルスチェック
health_check() {
    header "🏥 ヘルスチェックを実行しています..."
    
    local health_url
    health_url=$(koyeb services describe "$SERVICE_NAME" --output json 2>/dev/null | jq -r '.public_domain' 2>/dev/null)
    
    if [ "$health_url" != "null" ] && [ -n "$health_url" ]; then
        info "ヘルスチェックURL: https://$health_url/health"
        
        if curl -f -s "https://$health_url/health" > /dev/null; then
            success "ヘルスチェック成功"
        else
            warning "ヘルスチェック失敗 - サービスが完全に起動していない可能性があります"
        fi
    else
        warning "パブリックドメインが見つかりません"
    fi
}

# メイン処理
main() {
    echo -e "${CYAN}🚀 Discord Bot Enterprise - Koyeb デプロイスクリプト${NC}"
    echo ""
    
    # 引数の解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--repository)
                REPOSITORY_URL="$2"
                shift 2
                ;;
            -i|--instance)
                INSTANCE_TYPE="$2"
                shift 2
                ;;
            -g|--region)
                REGION="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            deploy)
                COMMAND="deploy"
                shift
                ;;
            redeploy)
                COMMAND="redeploy"
                shift
                ;;
            status)
                COMMAND="status"
                shift
                ;;
            logs)
                COMMAND="logs"
                shift
                ;;
            delete)
                COMMAND="delete"
                shift
                ;;
            secrets)
                COMMAND="secrets"
                shift
                ;;
            *)
                error "不明なオプション: $1"
                ;;
        esac
    done
    
    # デフォルトコマンド
    if [ -z "$COMMAND" ]; then
        COMMAND="deploy"
    fi
    
    # 前提条件チェック
    check_prerequisites
    
    # コマンド実行
    case $COMMAND in
        deploy)
            manage_secrets
            deploy_app
            check_deployment
            health_check
            show_status
            ;;
        redeploy)
            redeploy_service
            check_deployment
            health_check
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        delete)
            delete_service
            ;;
        secrets)
            manage_secrets
            ;;
        *)
            error "不明なコマンド: $COMMAND"
            ;;
    esac
    
    echo ""
    success "操作が完了しました！"
}

# スクリプト実行
main "$@" 