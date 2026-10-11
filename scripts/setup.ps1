# One-time setup for Windows (PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Backend: virtualenv + deps"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }

Write-Host "==> Frontend: deps"
Push-Location frontend; npm install; Pop-Location
if (!(Test-Path frontend\.env.local)) { Copy-Item frontend\.env.local.example frontend\.env.local }

Write-Host "Done. Backend: uvicorn app.main:app --reload (from backend/).  Frontend: npm run dev (from frontend/)."
Write-Host "MetaTrader5 live execution requires Windows + a running MT5 terminal; install the MetaTrader5 package to enable it."
