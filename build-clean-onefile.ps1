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

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Build Script Completato!" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
