#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Start Search Jobs dev environment (backend + frontend + Celery workers).
.DESCRIPTION
  Launches all three services in separate PowerShell windows:
    1. Backend  (FastAPI / Uvicorn on :8000)
    2. Frontend (Vite dev server on :5173)
    3. Celery   (Background task workers)
  Press a key in this window to stop all services.
.NOTES
  Requires: Python 3.12+, Node 20+, Redis running, Ollama running.
#>

$root = Split-Path -Parent $PSCommandPath
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Search Jobs -- Starting Dev Env" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ---- Check prerequisites ----
Write-Host "== check Redis..." -NoNewline
try {
    $null = redis-cli ping 2>&1
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " NOT RUNNING" -ForegroundColor Yellow
    Write-Host "  -> Start Redis manually or the app will still work (no background tasks)" -ForegroundColor Yellow
}

Write-Host "== check Ollama..." -NoNewline
try {
    $r = curl.exe -s http://localhost:11434/api/tags 2>&1
    if ($r) { Write-Host " OK" -ForegroundColor Green }
    else { throw }
} catch {
    Write-Host " NOT RUNNING" -ForegroundColor Yellow
    Write-Host "  -> Ollama needed for CV parsing and cover letters" -ForegroundColor Yellow
}

Write-Host ""

# ---- Start services ----
Write-Host "== start Backend (FastAPI :8000)..." -ForegroundColor Cyan
$be = Start-Process -PassThru -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Sleep -Seconds 3

Write-Host "== start Frontend (Vite :5173)..." -ForegroundColor Cyan
$fe = Start-Process -PassThru -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev"
Start-Sleep -Seconds 3

Write-Host "== start Celery Workers..." -ForegroundColor Cyan
$celery = Start-Process -PassThru -WindowStyle Normal -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$backend'; python -m celery -A app.celery_app worker --loglevel=info --pool=solo"

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to stop all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# ---- Cleanup ----
Write-Host "== stop Stopping services..." -ForegroundColor Yellow
$be | Stop-Process -Force -ErrorAction SilentlyContinue
$fe | Stop-Process -Force -ErrorAction SilentlyContinue
$celery | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "== done All stopped" -ForegroundColor Green
