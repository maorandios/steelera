# Start frontend + backend as independent Windows processes.
# Backend hot-reload will not take down the Next.js dev server.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendDir = Join-Path $root "backend"
$logDir = Join-Path $root ".dev-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Avoid stale uvicorn workers serving old code on :8000
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'uvicorn main:app.*--port 8000' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

$backendArgs = @(
    "-m", "uvicorn", "main:app",
    "--reload", "--host", "127.0.0.1", "--port", "8000",
    "--reload-delay", "1"
)

Start-Process -FilePath $python -ArgumentList $backendArgs `
    -WorkingDirectory $backendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "backend.log") `
    -RedirectStandardError (Join-Path $logDir "backend.err.log")

Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--prefix", "frontend") `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "frontend.log") `
    -RedirectStandardError (Join-Path $logDir "frontend.err.log")

Write-Host "Steelera dev servers started (independent processes)."
Write-Host "  Frontend: http://localhost:3000"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Logs:     $logDir"
Write-Host "Backend reloads will not stop the frontend."
