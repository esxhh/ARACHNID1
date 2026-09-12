$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$shell = Join-Path $PSHOME "powershell.exe"
if (-not (Test-Path $python)) { throw "Virtual environment not found at $python" }

if (-not $env:DJANGO_SECRET_KEY) {
    throw "Set DJANGO_SECRET_KEY before starting production services."
}

$env:DJANGO_DEBUG = "0"
$env:DJANGO_ALLOWED_HOSTS = if ($env:DJANGO_ALLOWED_HOSTS) { $env:DJANGO_ALLOWED_HOSTS } else { "127.0.0.1,localhost" }

Push-Location (Join-Path $PSScriptRoot "backend\django")
& $python manage.py migrate --noinput
& $python manage.py collectstatic --noinput
Pop-Location

$djangoCommand = "Set-Location '$PSScriptRoot\backend\django'; `$env:DJANGO_DEBUG='0'; `$env:DJANGO_SECRET_KEY='$env:DJANGO_SECRET_KEY'; `$env:DJANGO_ALLOWED_HOSTS='$env:DJANGO_ALLOWED_HOSTS'; & '$python' -m uvicorn config.asgi:application --host 0.0.0.0 --port 8001 --workers 2"
Start-Process $shell -ArgumentList "-NoExit", "-Command", $djangoCommand

Write-Host "Django control plane: http://127.0.0.1:8001/admin/"
Write-Host "FastAPI dashboard: http://127.0.0.1:8000"
& $python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
