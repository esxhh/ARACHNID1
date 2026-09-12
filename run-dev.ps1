$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$shell = Join-Path $PSHOME "powershell.exe"

Write-Host "Starting Django control plane on http://127.0.0.1:8001"
Start-Process $shell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\backend\django'; & '$python' manage.py runserver 127.0.0.1:8001"

Write-Host "Starting FastAPI dashboard on http://127.0.0.1:8000"
& $python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
