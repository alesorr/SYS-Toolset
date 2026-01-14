# Build script per creare l'eseguibile .exe
# Questo script crea un file eseguibile standalone usando PyInstaller

param(
    [Switch]$Clean,
    [Switch]$OneFile,
    [Switch]$Console
)

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   System Toolset - Build EXE (PyInstaller)" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

Write-Host "`nPrerequisiti: pip install -r requirements.txt" -ForegroundColor Cyan

# Step 1: Verifica PyInstaller
Write-Host "`n[1/4] Verificando PyInstaller..." -ForegroundColor Yellow
pip show pyinstaller > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] PyInstaller non trovato, installazione in corso..." -ForegroundColor Yellow
    pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [X] Errore nell'installazione di PyInstaller!" -ForegroundColor Red
        Write-Host "  Prova manualmente: pip install pyinstaller" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  [OK] PyInstaller installato" -ForegroundColor Green
} else {
    Write-Host "  [OK] PyInstaller trovato" -ForegroundColor Green
}

# Step 2: Pulizia build precedenti
if ($Clean) {
    Write-Host "`n[2/4] Pulizia build precedenti..." -ForegroundColor Yellow
    Remove-Item -Path "build" -Recurse -ErrorAction SilentlyContinue
    Remove-Item -Path "dist" -Recurse -ErrorAction SilentlyContinue
    Remove-Item -Path "*.spec" -ErrorAction SilentlyContinue
    Write-Host "[OK] Directory di build puliti" -ForegroundColor Green
} else {
    Write-Host "`n[2/4] Saltando pulizia (usa -Clean per forzare)" -ForegroundColor Yellow
}

# Configura opzioni PyInstaller
$PyInstallerArgs = @(
    "src/app.py",
    "--name=SystemToolset",
    # "--icon=icon.ico",  # Aggiungi il tuo icon.ico se desideri
    "--distpath=dist",
    "--workpath=build",
    "--specpath=.",
    "--onefile",
    "--windowed",
    "--collect-all=PyQt6",
    "--hidden-import=config.config",
    "--add-data=config/config.ini:config",
    "--add-data=scripts:scripts",
    "--add-data=docs:docs",
    "--noconfirm"
)

# Versione a file singolo vs directory
if ($OneFile) {
    Write-Host "`n[3/4] Compilando come file singolo..." -ForegroundColor Yellow
    Write-Host "      (questo richiede più tempo)" -ForegroundColor Gray
} else {
    Write-Host "`n[3/4] Compilando come directory..." -ForegroundColor Yellow
    $PyInstallerArgs = $PyInstallerArgs -replace "--onefile", ""
}

# Modalità console
if ($Console) {
    Write-Host "  Modalità: Console visibile" -ForegroundColor Yellow
    $PyInstallerArgs = $PyInstallerArgs -replace "--windowed", ""
} else {
    Write-Host "  Modalità: GUI senza console" -ForegroundColor Yellow
}

# Esegui PyInstaller
Write-Host ""
$PyInstallerCmd = "python -m PyInstaller " + ($PyInstallerArgs -join " ")
Invoke-Expression $PyInstallerCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Build completato con successo!" -ForegroundColor Green
    Write-Host "`n[4/4] Verificando output..." -ForegroundColor Yellow
    
    if (Test-Path "dist/SystemToolset.exe") {
        Write-Host "[OK] Eseguibile creato: dist/SystemToolset.exe" -ForegroundColor Green
        $ExeSize = (Get-Item "dist/SystemToolset.exe").Length / 1MB
        Write-Host "  Dimensione: $([Math]::Round($ExeSize, 2)) MB" -ForegroundColor Gray
    } elseif (Test-Path "dist/SystemToolset") {
        Write-Host "[OK] Directory creata: dist/SystemToolset/" -ForegroundColor Green
        Write-Host "  Eseguibile: dist/SystemToolset/SystemToolset.exe" -ForegroundColor Gray
    }
    
    Write-Host "`nProssimi passaggi:" -ForegroundColor Yellow
    Write-Host "  1. Copia l'intera cartella 'dist/' dove desideri" -ForegroundColor Gray
    Write-Host "  2. Doppio click su SystemToolset.exe per avviare l'app" -ForegroundColor Gray
    Write-Host ""
    
    # Copia automaticamente i file necessari
    Write-Host "Copiando assets necessari..." -ForegroundColor Cyan
    
    # Pulisci le cartelle di destinazione
    Remove-Item -Path "dist/scripts" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "dist/docs" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "dist/logs" -Recurse -Force -ErrorAction SilentlyContinue
    
    # Copia i file
    Copy-Item -Path "config/config.ini" -Destination "dist/" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "src/scripts" -Destination "dist/scripts" -Recurse -Force
    Copy-Item -Path "src/docs" -Destination "dist/docs" -Recurse -Force
    
    # Crea cartella logs vuota in dist
    New-Item -Path "dist/logs" -ItemType Directory -Force | Out-Null
    
    Write-Host "[OK] Assets copiati in dist/" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "   Build completato con successo!" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
} else {
    Write-Host "`n[ERRORE] Build fallito!" -ForegroundColor Red
    Write-Host "Verifica gli errori sopra e riprova" -ForegroundColor Red
    exit 1
}
