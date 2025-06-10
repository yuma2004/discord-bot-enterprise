# Discord Bot Enterprise - Supabase CLI セットアップスクリプト (Windows PowerShell)
# このスクリプトはローカル開発環境を簡単にセットアップします

param(
    [switch]$Force,
    [switch]$SkipChecks
)

# エラー時に停止
$ErrorActionPreference = "Stop"

Write-Host "🚀 Discord Bot Enterprise セットアップを開始します..." -ForegroundColor Cyan

# 関数定義
function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param($Message)
    Write-Host "ℹ️ $Message" -ForegroundColor Blue
}

function Test-Command {
    param($CommandName)
    return (Get-Command $CommandName -ErrorAction SilentlyContinue) -ne $null
}

# 管理者権限チェック
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "管理者権限が推奨されます。一部の操作が失敗する可能性があります。"
}

if (-not $SkipChecks) {
    # 前提条件のチェック
    Write-Host ""
    Write-Host "📋 前提条件をチェックしています..." -ForegroundColor Cyan

    # Node.js のチェック
    if (-not (Test-Command "node")) {
        Write-Error "Node.js がインストールされていません。Node.js 16以上をインストールしてください。"
        Write-Host "ダウンロード: https://nodejs.org/"
        exit 1
    }

    $nodeVersion = (node --version) -replace 'v', ''
    $nodeMajor = [int]($nodeVersion.Split('.')[0])
    if ($nodeMajor -lt 16) {
        Write-Error "Node.js のバージョンが古すぎます (現在: v$nodeVersion)。Node.js 16以上が必要です。"
        exit 1
    }
    Write-Success "Node.js v$nodeVersion が利用可能です"

    # Python のチェック
    $pythonCommand = $null
    if (Test-Command "python") {
        $pythonCommand = "python"
    } elseif (Test-Command "python3") {
        $pythonCommand = "python3"
    } elseif (Test-Command "py") {
        $pythonCommand = "py"
    }

    if (-not $pythonCommand) {
        Write-Error "Python 3 がインストールされていません。Python 3.8以上をインストールしてください。"
        Write-Host "ダウンロード: https://www.python.org/downloads/"
        exit 1
    }

    $pythonVersion = (& $pythonCommand --version 2>&1) -replace 'Python ', ''
    $pythonParts = $pythonVersion.Split('.')
    $pythonMajor = [int]$pythonParts[0]
    $pythonMinor = [int]$pythonParts[1]

    if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 8)) {
        Write-Error "Python のバージョンが古すぎます (現在: $pythonVersion)。Python 3.8以上が必要です。"
        exit 1
    }
    Write-Success "Python $pythonVersion が利用可能です"

    # Docker のチェック
    if (-not (Test-Command "docker")) {
        Write-Error "Docker がインストールされていません。Docker Desktop をインストールして起動してください。"
        Write-Host "ダウンロード: https://www.docker.com/products/docker-desktop"
        exit 1
    }

    try {
        docker ps | Out-Null
        Write-Success "Docker が利用可能です"
    } catch {
        Write-Error "Docker が起動していません。Docker Desktop を起動してください。"
        exit 1
    }

    # Git のチェック
    if (-not (Test-Command "git")) {
        Write-Warning "Git がインストールされていません。バージョン管理を行う場合はGitをインストールしてください。"
    } else {
        Write-Success "Git が利用可能です"
    }
}

Write-Host ""

# Supabase CLI のセットアップ
Write-Host "🔧 Supabase CLI をセットアップしています..." -ForegroundColor Cyan

if (-not (Test-Command "supabase")) {
    Write-Info "Supabase CLI をインストールしています..."
    
    if (Test-Command "npm") {
        try {
            npm install -g supabase
            Write-Success "Supabase CLI のインストールが完了しました"
        } catch {
            Write-Error "Supabase CLI のインストールに失敗しました: $_"
            exit 1
        }
    } elseif (Test-Command "choco") {
        try {
            choco install supabase -y
            Write-Success "Supabase CLI のインストールが完了しました"
        } catch {
            Write-Error "Supabase CLI のインストールに失敗しました: $_"
            exit 1
        }
    } else {
        Write-Error "npm または Chocolatey が利用できません。手動でSupabase CLIをインストールしてください。"
        Write-Host "インストール手順: https://supabase.com/docs/guides/cli"
        exit 1
    }
} else {
    Write-Success "Supabase CLI は既にインストールされています"
}

# Supabase CLI のバージョン確認
try {
    $supabaseVersion = supabase --version 2>$null
    Write-Success "Supabase CLI バージョン: $supabaseVersion"
} catch {
    $supabaseVersion = "unknown"
    Write-Warning "Supabase CLI のバージョンを取得できませんでした"
}

Write-Host ""

# プロジェクトの依存関係セットアップ
Write-Host "📦 プロジェクトの依存関係をセットアップしています..." -ForegroundColor Cyan

# Node.js の依存関係
if (Test-Path "package.json") {
    Write-Info "Node.js の依存関係をインストールしています..."
    try {
        npm install
        Write-Success "Node.js 依存関係のインストールが完了しました"
    } catch {
        Write-Error "Node.js 依存関係のインストールに失敗しました: $_"
        exit 1
    }
} else {
    Write-Warning "package.json が見つかりません。npm install をスキップします。"
}

# Python の依存関係
if (Test-Path "requirements.txt") {
    Write-Info "Python の依存関係をインストールしています..."
    
    # 仮想環境の作成
    if (-not (Test-Path "venv")) {
        Write-Info "Python 仮想環境を作成しています..."
        try {
            & $pythonCommand -m venv venv
            Write-Success "Python 仮想環境を作成しました"
        } catch {
            Write-Error "仮想環境の作成に失敗しました: $_"
            exit 1
        }
    }
    
    # 仮想環境のアクティベート
    $activateScript = "venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Info "仮想環境をアクティベートしています..."
        & $activateScript
        
        # pip のアップグレード
        python -m pip install --upgrade pip
        
        # 依存関係のインストール
        try {
            pip install -r requirements.txt
            Write-Success "Python 依存関係のインストールが完了しました"
        } catch {
            Write-Error "Python 依存関係のインストールに失敗しました: $_"
            exit 1
        }
    } else {
        Write-Error "仮想環境のアクティベートスクリプトが見つかりません"
        exit 1
    }
} else {
    Write-Warning "requirements.txt が見つかりません。pip install をスキップします。"
}

Write-Host ""

# Supabase プロジェクトの初期化
Write-Host "🏗️ Supabase プロジェクトを初期化しています..." -ForegroundColor Cyan

if (-not (Test-Path "supabase\config.toml")) {
    Write-Info "Supabase プロジェクトを初期化しています..."
    try {
        supabase init
        Write-Success "Supabase プロジェクトの初期化が完了しました"
    } catch {
        Write-Error "Supabase プロジェクトの初期化に失敗しました: $_"
        exit 1
    }
} else {
    Write-Success "Supabase プロジェクトは既に初期化されています"
}

Write-Host ""

# 環境変数ファイルのセットアップ
Write-Host "⚙️ 環境変数をセットアップしています..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path "env_local_example.txt") {
        Write-Info "環境変数ファイルを作成しています..."
        try {
            Copy-Item "env_local_example.txt" ".env"
            Write-Success "環境変数ファイル (.env) を作成しました"
            Write-Warning "⚠️ .env ファイルを編集して、必要な設定値を入力してください"
        } catch {
            Write-Error "環境変数ファイルの作成に失敗しました: $_"
            exit 1
        }
    } else {
        Write-Warning "env_local_example.txt が見つかりません。手動で .env ファイルを作成してください。"
    }
} else {
    Write-Success "環境変数ファイル (.env) は既に存在します"
}

Write-Host ""

# Supabase ローカル環境の起動
Write-Host "🚀 Supabase ローカル環境を起動しています..." -ForegroundColor Cyan

Write-Info "Supabase ローカル環境を起動中... (初回は時間がかかります)"
try {
    supabase start
    Write-Success "Supabase ローカル環境が起動しました"
} catch {
    Write-Error "Supabase ローカル環境の起動に失敗しました: $_"
    Write-Info "Docker Desktop が起動していることを確認してから再試行してください。"
    exit 1
}

Write-Host ""

# データベースマイグレーションの実行
Write-Host "🗄️ データベースマイグレーションを実行しています..." -ForegroundColor Cyan

if (Test-Path "supabase\migrations\20240101000000_init_discord_bot.sql") {
    Write-Info "初期マイグレーションを適用しています..."
    try {
        supabase db reset --db-url "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        Write-Success "データベースマイグレーションが完了しました"
    } catch {
        Write-Warning "マイグレーションの適用に失敗しました。手動で実行してください。"
    }
} else {
    Write-Warning "マイグレーションファイルが見つかりません。手動でマイグレーションを実行してください。"
}

Write-Host ""

# セットアップ完了
Write-Host "🎉 セットアップが完了しました！" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "1. .env ファイルを編集して Discord Bot Token を設定してください" -ForegroundColor Blue
Write-Host "2. Supabase Studio (http://127.0.0.1:54323) でデータベースを確認してください" -ForegroundColor Blue
Write-Host "3. 以下のコマンドで Bot を起動してください:" -ForegroundColor Blue
Write-Host ""
Write-Host "  # 仮想環境をアクティベート" -ForegroundColor Yellow
Write-Host "  venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Bot を起動" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "便利なコマンド:" -ForegroundColor Cyan
Write-Host "  npm run studio     - Supabase Studio を開く" -ForegroundColor Blue
Write-Host "  npm run status     - Supabase の状態を確認" -ForegroundColor Blue
Write-Host "  npm run stop       - Supabase を停止" -ForegroundColor Blue
Write-Host "  npm run logs       - Supabase のログを表示" -ForegroundColor Blue
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green 