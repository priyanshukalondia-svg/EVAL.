# run.ps1
# Script to setup and start the AI Recruitment Platform

param (
    [string]$Action = "dev", # Options: dev, setup, clean
    [string]$Provider = "gemini" # Options: gemini, openai, anthropic
)

$RootDir = Get-Location

if ($Action -eq "setup") {
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host "Setting up AI Recruitment Platform..." -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green

    # Install root dependencies
    Write-Host "Installing root dependencies..." -ForegroundColor Cyan
    npm install

    # Setup Backend
    Write-Host "Setting up backend in apps/api..." -ForegroundColor Cyan
    if (-not (Test-Path "apps/api")) {
        New-Item -ItemType Directory -Path "apps/api" -Force | Out-Null
    }
    cd apps/api
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "Activating virtual environment and installing python dependencies..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    cd $RootDir

    # Setup Frontend
    Write-Host "Setting up Next.js frontend in apps/web..." -ForegroundColor Cyan
    if (-not (Test-Path "apps/web")) {
        Write-Host "Please initialize Next.js app in apps/web first" -ForegroundColor Yellow
    } else {
        cd apps/web
        npm install
        cd $RootDir
    }

    Write-Host "Setup complete!" -ForegroundColor Green
}
elseif ($Action -eq "dev") {
    Write-Host "Starting development servers..." -ForegroundColor Green
    npm run dev
}
elseif ($Action -eq "clean") {
    Write-Host "Cleaning build and virtual environments..." -ForegroundColor Yellow
    Remove-Item -Recurve -Force apps/api/.venv -ErrorAction SilentlyContinue
    Remove-Item -Recurve -Force apps/api/__pycache__ -ErrorAction SilentlyContinue
    Remove-Item -Recurve -Force apps/web/.next -ErrorAction SilentlyContinue
    Remove-Item -Recurve -Force apps/web/node_modules -ErrorAction SilentlyContinue
    Remove-Item -Recurve -Force node_modules -ErrorAction SilentlyContinue
    Write-Host "Clean complete!" -ForegroundColor Green
}
