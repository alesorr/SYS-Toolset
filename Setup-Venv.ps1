<#
============================================================
 File: Setup-Venv.ps1
 Author: Internal Systems Automation Team
 Created: 2025-01-11

 Description:
     Script PowerShell per creare un virtual environment
     dedicato al Toolset CLI ed installare automaticamente
     tutte le dipendenze elencate in requirements.txt.

     Questo script è pensato per essere eseguito una volta
     da ogni sviluppatore o membro del team al primo setup.
============================================================
#>

Write-Host "=== CLI Toolset - Environment Setup ===" -ForegroundColor Cyan

$VenvPath = ".\venv"

# 1. Create venv
if (!(Test-Path $VenvPath)) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $VenvPath
} else {
    Write-Host "[INFO] Virtual environment already exists." -ForegroundColor Yellow
}

# 2. Activate venv
Write-Host "[INFO] Activating venv..." -ForegroundColor Cyan
& "$VenvPath\Scripts\Activate.ps1"

# 3. Upgrade pip safely
Write-Host "[INFO] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# 4. Install requirements
if (Test-Path "./requirements.txt") {
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Cyan
    python -m pip install -r requirements.txt
    Write-Host "[SUCCESS] Requirements installed successfully!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] requirements.txt not found!" -ForegroundColor Red
    exit 1
}

Write-Host "=== Setup Complete! ===" -ForegroundColor Green