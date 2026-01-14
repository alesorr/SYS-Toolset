Set-Location -Path $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python non trovato nel PATH" -ForegroundColor Red
    exit 1
}

python src\gui_main.py
