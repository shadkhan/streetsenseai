<#
.SYNOPSIS
    Start or stop the full StreetSense AI local dev environment.

.EXAMPLE
    .\scripts\dev.ps1 start          # start everything (4 windows)
    .\scripts\dev.ps1 start -Ngrok   # start + ngrok window for SM webhooks
    .\scripts\dev.ps1 stop           # stop everything + docker-compose down

.NOTES
    Requires: Docker Desktop, uv, pnpm, ngrok (optional for -Ngrok flag)
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop")]
    [string]$Command = "start",

    [switch]$Ngrok
)

# ── Paths ─────────────────────────��───────────────────────���────────────────────

$repoRoot = Split-Path $PSScriptRoot -Parent
$apiDir   = Join-Path $repoRoot "apps\api"
$webDir   = Join-Path $repoRoot "apps\web"
$infraDir = Join-Path $repoRoot "infra"
$pidFile  = Join-Path $repoRoot ".dev-pids.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

function Write-Step([string]$msg) {
    Write-Host "  [>] $msg" -ForegroundColor Yellow
}

function Open-ServiceWindow([string]$title, [string]$workDir, [string]$cmd) {
    $script = "& { `$host.UI.RawUI.WindowTitle = '$title'; Set-Location '$workDir'; $cmd }"
    $proc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $script -PassThru
    return $proc.Id
}

function Kill-Tree([int]$procId) {
    # /F = force, /T = include child processes
    $null = & taskkill /F /T /PID $procId 2>&1
}

# ── Start ──────────────────────────────────────────────────────────────────────

function Start-Dev {
    Write-Host ""
    Write-Host "  StreetSense AI -- starting local dev environment" -ForegroundColor Cyan
    Write-Host ""

    # 1. Infrastructure (detached -- no window needed)
    Write-Step "Infrastructure: PostgreSQL 16 + PostGIS, Redis 7 (docker-compose)"
    Push-Location $infraDir
    docker-compose up -d
    Pop-Location

    # Brief pause so Postgres is ready before the API tries to connect
    Start-Sleep -Seconds 3

    $pids = @{}

    # 2. FastAPI
    Write-Step "FastAPI backend   -->  http://localhost:8000/docs"
    $pids.api = Open-ServiceWindow "StreetSense -- FastAPI :8000" $apiDir "uv run uvicorn main:app --reload --port 8000"
    Start-Sleep -Milliseconds 500

    # 3. Celery worker
    Write-Step "Celery worker"
    $pids.celery = Open-ServiceWindow "StreetSense -- Celery worker" $apiDir "uv run celery -A tasks worker --loglevel=info"
    Start-Sleep -Milliseconds 500

    # 4. Next.js frontend
    Write-Step "Next.js frontend  -->  http://localhost:3000"
    $pids.web = Open-ServiceWindow "StreetSense -- Next.js :3000" $webDir "pnpm dev"
    Start-Sleep -Milliseconds 500

    # 5. ngrok (optional)
    if ($Ngrok) {
        Write-Step "ngrok             -->  http://127.0.0.1:4040 (ngrok UI)"
        $pids.ngrok = Open-ServiceWindow "StreetSense -- ngrok" $repoRoot "ngrok http 8000"
    }

    # Persist PIDs for the stop command
    $pids | ConvertTo-Json | Set-Content -Path $pidFile -Encoding utf8

    Write-Host ""
    Write-Host "  All services started." -ForegroundColor Green
    Write-Host ""
    Write-Host "  API docs   -->  http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Frontend   -->  http://localhost:3000"      -ForegroundColor White

    if ($Ngrok) {
        Write-Host "  ngrok UI   -->  http://127.0.0.1:4040"     -ForegroundColor White
        Write-Host ""
        Write-Host "  SM webhook URLs (swap in your ngrok domain):" -ForegroundColor DarkGray
        Write-Host "    Permit      https://<ngrok>/webhooks/permits"    -ForegroundColor DarkGray
        Write-Host "    Activity    https://<ngrok>/webhooks/activities" -ForegroundColor DarkGray
        Write-Host "    Section 58  https://<ngrok>/webhooks/section58"  -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "  To stop:  .\scripts\dev.ps1 stop" -ForegroundColor DarkGray
    Write-Host ""
}

# ── Stop ───────────────────────────────────────────────────────────────────────

function Stop-Dev {
    Write-Host ""
    Write-Host "  StreetSense AI -- stopping local dev environment" -ForegroundColor Cyan
    Write-Host ""

    if (Test-Path $pidFile) {
        $pids = Get-Content -Path $pidFile -Raw | ConvertFrom-Json

        foreach ($svc in @("api", "celery", "web", "ngrok")) {
            $id = $pids.$svc
            if ($id) {
                $running = Get-Process -Id $id -ErrorAction SilentlyContinue
                if ($running) {
                    Kill-Tree $id
                    Write-Step "Stopped $svc (PID $id)"
                } else {
                    Write-Host "  [ ] $svc already stopped" -ForegroundColor DarkGray
                }
            }
        }

        Remove-Item $pidFile -Force
    } else {
        Write-Host "  No .dev-pids.json found -- services may already be down." -ForegroundColor DarkGray
    }

    Write-Step "Infrastructure: docker-compose down"
    Push-Location $infraDir
    docker-compose down
    Pop-Location

    Write-Host ""
    Write-Host "  All services stopped." -ForegroundColor Green
    Write-Host ""
}

# ── Dispatch ───────────────────────────────────────────────────────────────────

switch ($Command) {
    "start" { Start-Dev }
    "stop"  { Stop-Dev  }
}
