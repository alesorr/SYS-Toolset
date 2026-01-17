<#
.SYNOPSIS
    Build script rapido per SYS Toolset Management
    
.DESCRIPTION
    Esegue automaticamente la build con pulizia completa e modalità OneFile
    
.NOTES
    File: build-clean-onefile.ps1
    Author: System Automation Team
    Created: 2026-01-14
#>

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   SYS Toolset Management - Quick Build" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Pulizia build precedenti
Write-Host "Pulizia build precedenti..." -ForegroundColor Yellow
Remove-Item -Path "build" -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path "*.spec" -ErrorAction SilentlyContinue
Write-Host "[OK] Directory di build puliti" -ForegroundColor Green

# Build con PyInstaller direttamente
Write-Host ""
Write-Host "Avvio build con PyInstaller..." -ForegroundColor Yellow

$PyInstallerArgs = @(
    "src/app.py",
    "--name=SystemToolset",
    "--distpath=dist",
    "--workpath=build",
    "--specpath=.",
    "--onefile",
    "--windowed",
    "--collect-all=PyQt6",
    "--collect-submodules=gui",
    "--hidden-import=config.config",
    "--hidden-import=config.setting",
    "--hidden-import=gui",
    "--hidden-import=gui.main_window",
    "--hidden-import=gui.splash_screen",
    "--hidden-import=db",
    "--hidden-import=db.script_repository",
    "--hidden-import=menu",
    "--hidden-import=menu.tool_menu",
    "--hidden-import=utils",
    "--hidden-import=utils.logger",
    "--hidden-import=utils.file_loader",
    "--hidden-import=models",
    "--hidden-import=models.script_model",
    "--paths=src",
    "--noupx",
    "--add-data=config/config.ini:config",
    "--add-data=scripts:scripts",
    "--add-data=docs:docs",
    "--add-data=src/gui:gui",
    "--noconfirm"
)

$PyInstallerCmd = "python -m PyInstaller " + ($PyInstallerArgs -join " ")
Invoke-Expression $PyInstallerCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Build fallito!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] Build completato con successo!" -ForegroundColor Green

# Verifica che config.ini sia stato copiato correttamente
Write-Host ""
Write-Host "Verificando configurazione..." -ForegroundColor Cyan
if (Test-Path "dist/config/config.ini") {
    Write-Host "[OK] Config.ini presente in dist/config/" -ForegroundColor Green
} else {
    Write-Host "[!] Config.ini mancante, copiando manualmente..." -ForegroundColor Yellow
    New-Item -Path "dist/config" -ItemType Directory -Force | Out-Null
    Copy-Item -Path "config/config.ini" -Destination "dist/config/config.ini" -Force
    Write-Host "[OK] Config.ini copiato in dist/config/" -ForegroundColor Green
}

# Crea cartella schedules in dist se non esiste
Write-Host ""
Write-Host "Configurando directory schedules..." -ForegroundColor Cyan
if (-not (Test-Path "dist/schedules")) {
    New-Item -Path "dist/schedules" -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Directory dist/schedules creata" -ForegroundColor Green
} else {
    Write-Host "[OK] Directory dist/schedules già esistente" -ForegroundColor Green
}

# Copia file di scheduling esistenti se presenti
if (Test-Path "schedules/*.json") {
    Copy-Item -Path "schedules/*.json" -Destination "dist/schedules/" -Force
    $jsonCount = (Get-ChildItem "schedules/*.json" | Measure-Object).Count
    Write-Host "[OK] $jsonCount file(s) di configurazione scheduling copiati" -ForegroundColor Green
} else {
    Write-Host "[INFO] Nessuna configurazione scheduling da copiare" -ForegroundColor Yellow
}

# Crea cartella workflows in dist se non esiste
Write-Host ""
Write-Host "Configurando directory workflows..." -ForegroundColor Cyan
if (-not (Test-Path "dist/workflows")) {
    New-Item -Path "dist/workflows" -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Directory dist/workflows creata" -ForegroundColor Green
} else {
    Write-Host "[OK] Directory dist/workflows già esistente" -ForegroundColor Green
}

# Copia file di workflow esistenti se presenti
if (Test-Path "workflows/*.json") {
    Copy-Item -Path "workflows/*.json" -Destination "dist/workflows/" -Force
    $workflowCount = (Get-ChildItem "workflows/*.json" | Measure-Object).Count
    Write-Host "[OK] $workflowCount file(s) di workflow copiati" -ForegroundColor Green
} else {
    Write-Host "[INFO] Nessun workflow da copiare" -ForegroundColor Yellow
}

# Copia cartella docs in dist
Write-Host ""
Write-Host "Configurando directory docs..." -ForegroundColor Cyan
if (-not (Test-Path "dist/docs")) {
    New-Item -Path "dist/docs" -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Directory dist/docs creata" -ForegroundColor Green
}

if (Test-Path "docs") {
    Copy-Item -Path "docs" -Destination "dist/" -Recurse -Force
    Write-Host "[OK] Directory docs copiata in dist/" -ForegroundColor Green
} else {
    Write-Host "[WARN] Directory docs non trovata nella radice del progetto" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Build Script Completato!" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
