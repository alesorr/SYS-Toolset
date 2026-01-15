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

# Esegui build con parametri Clean e OneFile
& "$PSScriptRoot\build.ps1" -Clean -OneFile

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

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Build Script Completato!" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
