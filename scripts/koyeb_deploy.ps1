# Discord Bot Enterprise - Koyeb デプロイスクリプト (Windows PowerShell)
# このスクリプトはKoyeb CLIを使用してDiscord Botをデプロイします

param(
    [string]$Command = "deploy",
    [string]$Repository = "",
    [string]$InstanceType = "nano",
    [string]$Region = "fra",
    [switch]$Help
)

# 設定
$APP_NAME = "discord-bot-enterprise"
$SERVICE_NAME = "discord-bot"

# エラー時に停止
$ErrorActionPreference = "Stop"

# 関数定義
function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColoredOutput "✅ $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColoredOutput "⚠️ $Message" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColoredOutput "❌ エラー: $Message" "Red"
    exit 1
}

function Write-Info {
    param([string]$Message)
    Write-ColoredOutput "ℹ️ $Message" "Blue"
}

function Write-Header {
    param([string]$Message)
    Write-ColoredOutput $Message "Cyan"
}

function Test-Command {
    param([string]$CommandName)
    return (Get-Command $CommandName -ErrorAction SilentlyContinue) -ne $null
}

# ヘルプ表示
function Show-Help {
    Write-Host "Discord Bot Enterprise - Koyeb デプロイスクリプト (PowerShell)"
    Write-Host ""
    Write-Host "使用方法:"
    Write-Host "  .\scripts\koyeb_deploy.ps1 [パラメーター]"
    Write-Host ""
    Write-Host "パラメーター:"
    Write-Host "  -Command <string>     実行するコマンド (deploy/redeploy/status/logs/delete/secrets)"
    Write-Host "  -Repository <string>  GitリポジトリURL"
    Write-Host "  -InstanceType <string> インスタンスタイプ (nano/small/medium)"
    Write-Host "  -Region <string>      リージョン (fra/was/sin)"
    Write-Host "  -Help                 このヘルプを表示"
    Write-Host ""
    Write-Host "例:"
    Write-Host "  .\scripts\koyeb_deploy.ps1 -Command deploy -Repository https://github.com/user/repo.git"
    Write-Host "  .\scripts\koyeb_deploy.ps1 -Command redeploy"
    Write-Host "  .\scripts\koyeb_deploy.ps1 -Command status"
}

# 前提条件のチェック
function Test-Prerequisites {
    Write-Header "🔍 前提条件をチェックしています..."
    
    # Koyeb CLI のチェック
    if (-not (Test-Command "koyeb")) {
        Write-Error "Koyeb CLI がインストールされていません。インストールしてください。"
    }
    Write-Success "Koyeb CLI が利用可能です"
    
    # 認証チェック
    try {
        koyeb profile | Out-Null
        Write-Success "Koyeb CLI にログイン済みです"
    } catch {
        Write-Error "Koyeb CLI にログインしていません。'koyeb login' を実行してください。"
    }
    
    # Git のチェック
    if (Test-Command "git") {
        Write-Success "Git が利用可能です"
    } else {
        Write-Warning "Git がインストールされていません"
    }
    
    # Docker のチェック
    if (Test-Command "docker") {
        Write-Success "Docker が利用可能です"
    } else {
        Write-Warning "Docker がインストールされていません（Git デプロイのみ利用可能）"
    }
}

# シークレットの確認・作成
function Manage-Secrets {
    Write-Header "🔐 シークレットを管理しています..."
    
    $secrets = @(
        @{name="discord-token"; required=$true},
        @{name="database-url"; required=$true},
        @{name="google-client-id"; required=$false},
        @{name="google-client-secret"; required=$false},
        @{name="google-calendar-id"; required=$false}
    )
    
    foreach ($secret in $secrets) {
        try {
            koyeb secrets describe $secret.name | Out-Null
            Write-Success "シークレット '$($secret.name)' は既に存在します"
        } catch {
            Write-Warning "シークレット '$($secret.name)' が存在しません"
            
            if ($secret.required) {
                Write-Error "必須のシークレット '$($secret.name)' が存在しません。以下のコマンドで作成してください:`nkoyeb secrets create $($secret.name) --value `"YOUR_VALUE`""
            } else {
                Write-Info "オプションのシークレット '$($secret.name)' をスキップします"
            }
        }
    }
}

# アプリケーションのデプロイ
function Deploy-App {
    Write-Header "🚀 アプリケーションをデプロイしています..."
    
    # リポジトリURLの確認
    if ([string]::IsNullOrEmpty($Repository)) {
        # 現在のGitリポジトリから取得を試行
        try {
            $Repository = git remote get-url origin
            Write-Info "Git リポジトリURL を自動検出: $Repository"
        } catch {
            Write-Error "リポジトリURL が指定されていません。-Repository パラメーターで指定してください。"
        }
    }
    
    # アプリが既に存在するかチェック
    try {
        koyeb apps describe $APP_NAME | Out-Null
        Write-Warning "アプリ '$APP_NAME' は既に存在します"
        
        # サービスが存在するかチェック
        try {
            koyeb services describe $SERVICE_NAME | Out-Null
            Write-Info "既存のサービスを更新します"
            Redeploy-Service
        } catch {
            Write-Info "新しいサービスを作成します"
            Create-Service
        }
    } catch {
        Write-Info "新しいアプリとサービスを作成します"
        Create-AppAndService
    }
}

# 新しいアプリとサービスの作成
function Create-AppAndService {
    Write-Info "アプリ '$APP_NAME' を作成しています..."
    
    try {
        koyeb apps create $APP_NAME
        Write-Success "アプリを作成しました"
    } catch {
        Write-Error "アプリの作成に失敗しました: $_"
    }
    
    Create-Service
}

# サービスの作成
function Create-Service {
    Write-Info "サービス '$SERVICE_NAME' を作成しています..."
    
    $deployArgs = @(
        "services", "create", $SERVICE_NAME,
        "--app", $APP_NAME,
        "--git-repository", $Repository,
        "--git-branch", "main",
        "--instance-type", $InstanceType,
        "--region", $Region,
        "--port", "8000:http",
        "--env", "DISCORD_TOKEN=@discord-token",
        "--env", "DATABASE_URL=@database-url",
        "--env", "ENVIRONMENT=production",
        "--env", "BOT_PREFIX=!",
        "--env", "TIMEZONE=Asia/Tokyo",
        "--env", "DAILY_REPORT_TIME=17:00",
        "--env", "DEBUG=false",
        "--env", "LOG_LEVEL=INFO"
    )
    
    # オプションの環境変数（シークレットが存在する場合のみ）
    try {
        koyeb secrets describe "google-client-id" | Out-Null
        $deployArgs += "--env", "GOOGLE_CLIENT_ID=@google-client-id"
    } catch { }
    
    try {
        koyeb secrets describe "google-client-secret" | Out-Null
        $deployArgs += "--env", "GOOGLE_CLIENT_SECRET=@google-client-secret"
    } catch { }
    
    try {
        koyeb secrets describe "google-calendar-id" | Out-Null
        $deployArgs += "--env", "GOOGLE_CALENDAR_ID=@google-calendar-id"
    } catch { }
    
    $deployArgs += "--health-check-path", "/health"
    
    try {
        & koyeb $deployArgs
        Write-Success "サービスを作成しました"
    } catch {
        Write-Error "サービスの作成に失敗しました: $_"
    }
}

# サービスの再デプロイ
function Redeploy-Service {
    Write-Info "サービス '$SERVICE_NAME' を再デプロイしています..."
    
    try {
        koyeb services redeploy $SERVICE_NAME
        Write-Success "再デプロイを開始しました"
    } catch {
        Write-Error "再デプロイに失敗しました: $_"
    }
}

# デプロイ状況の確認
function Test-Deployment {
    Write-Header "📊 デプロイ状況を確認しています..."
    
    $maxWait = 300  # 5分
    $waitTime = 0
    
    while ($waitTime -lt $maxWait) {
        try {
            $statusJson = koyeb services describe $SERVICE_NAME --output json | ConvertFrom-Json
            $status = $statusJson.latest_deployment.status
        } catch {
            $status = "unknown"
        }
        
        switch ($status) {
            "healthy" {
                Write-Success "デプロイが完了しました！"
                return
            }
            "unhealthy" {
                Write-Error "デプロイが失敗しました。ログを確認してください。"
            }
            "error" {
                Write-Error "デプロイが失敗しました。ログを確認してください。"
            }
            "pending" {
                Write-Info "デプロイ中... ($waitTime 秒経過)"
            }
            "deploying" {
                Write-Info "デプロイ中... ($waitTime 秒経過)"
            }
            default {
                Write-Info "状況確認中... ($status)"
            }
        }
        
        Start-Sleep -Seconds 10
        $waitTime += 10
    }
    
    if ($waitTime -ge $maxWait) {
        Write-Warning "デプロイ状況の確認がタイムアウトしました"
    }
}

# サービス情報の表示
function Show-Status {
    Write-Header "📈 サービス状況"
    
    Write-Host "アプリケーション情報:"
    try {
        koyeb apps describe $APP_NAME
    } catch {
        Write-Host "アプリが見つかりません"
    }
    
    Write-Host ""
    Write-Host "サービス情報:"
    try {
        koyeb services describe $SERVICE_NAME
    } catch {
        Write-Host "サービスが見つかりません"
    }
    
    Write-Host ""
    Write-Host "最新のデプロイメント:"
    try {
        koyeb deployments list --service $SERVICE_NAME --limit 3
    } catch {
        Write-Host "デプロイメント情報を取得できません"
    }
}

# ログの表示
function Show-Logs {
    Write-Header "📝 サービスログ"
    
    Write-Info "最新のログを表示しています..."
    try {
        koyeb services logs $SERVICE_NAME --since 30m
    } catch {
        Write-Error "ログの取得に失敗しました: $_"
    }
}

# サービスの削除
function Remove-Service {
    Write-Header "🗑️ サービスを削除しています..."
    
    Write-Warning "この操作はサービス '$SERVICE_NAME' を完全に削除します。"
    $response = Read-Host "続行しますか? (y/N)"
    
    if ($response -match "^[Yy]$") {
        try {
            koyeb services delete $SERVICE_NAME
            Write-Success "サービスを削除しました"
            
            # アプリが空になった場合は削除するか確認
            try {
                $servicesJson = koyeb services list --app $APP_NAME --output json | ConvertFrom-Json
                $serviceCount = $servicesJson.services.Count
                
                if ($serviceCount -eq 0) {
                    $response = Read-Host "アプリ '$APP_NAME' も削除しますか? (y/N)"
                    
                    if ($response -match "^[Yy]$") {
                        try {
                            koyeb apps delete $APP_NAME
                            Write-Success "アプリを削除しました"
                        } catch {
                            Write-Warning "アプリの削除に失敗しました: $_"
                        }
                    }
                }
            } catch {
                Write-Warning "サービス数の確認に失敗しました"
            }
        } catch {
            Write-Error "サービスの削除に失敗しました: $_"
        }
    } else {
        Write-Info "削除をキャンセルしました"
    }
}

# ヘルスチェック
function Test-Health {
    Write-Header "🏥 ヘルスチェックを実行しています..."
    
    try {
        $serviceJson = koyeb services describe $SERVICE_NAME --output json | ConvertFrom-Json
        $healthUrl = $serviceJson.public_domain
        
        if ($healthUrl -and $healthUrl -ne "null") {
            Write-Info "ヘルスチェックURL: https://$healthUrl/health"
            
            try {
                $response = Invoke-RestMethod -Uri "https://$healthUrl/health" -Method Get -TimeoutSec 30
                Write-Success "ヘルスチェック成功"
            } catch {
                Write-Warning "ヘルスチェック失敗 - サービスが完全に起動していない可能性があります"
            }
        } else {
            Write-Warning "パブリックドメインが見つかりません"
        }
    } catch {
        Write-Warning "ヘルスチェックの実行に失敗しました: $_"
    }
}

# メイン処理
function Main {
    Write-Header "🚀 Discord Bot Enterprise - Koyeb デプロイスクリプト (PowerShell)"
    Write-Host ""
    
    if ($Help) {
        Show-Help
        return
    }
    
    # 前提条件チェック
    Test-Prerequisites
    
    # コマンド実行
    switch ($Command.ToLower()) {
        "deploy" {
            Manage-Secrets
            Deploy-App
            Test-Deployment
            Test-Health
            Show-Status
        }
        "redeploy" {
            Redeploy-Service
            Test-Deployment
            Test-Health
        }
        "status" {
            Show-Status
        }
        "logs" {
            Show-Logs
        }
        "delete" {
            Remove-Service
        }
        "secrets" {
            Manage-Secrets
        }
        default {
            Write-Error "不明なコマンド: $Command"
        }
    }
    
    Write-Host ""
    Write-Success "操作が完了しました！"
}

# スクリプト実行
try {
    Main
} catch {
    Write-Error "スクリプトの実行中にエラーが発生しました: $_"
} 