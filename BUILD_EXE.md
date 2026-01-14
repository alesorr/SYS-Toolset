# System Toolset - Creazione Eseguibile .EXE

## Panoramica
Questo documento spiega come trasformare l'applicazione PyQt6 in un eseguibile standalone (.exe) distribuibile.

## Architettura: Cosa cambia

### Prima (Versione Python)
```
Sistema utente
  ↓
Python (deve essere installato)
  ↓
Ambiente virtuale
  ↓
Script main.py
  ↓
Applicazione grafica
```

### Dopo (Versione EXE)
```
Sistema utente
  ↓
SystemToolset.exe (autonomo, nessuna dipendenza)
  ↓
PyQt6 embedded (incluso nell'exe)
  ↓
Python embedded (incluso nell'exe)
  ↓
Applicazione grafica
```

## Struttura dei file

Dopo la compilazione in exe, la struttura sarà:

```
dist/
├── SystemToolset/
│   ├── SystemToolset.exe          ← Eseguibile principale
│   ├── config/
│   │   └── config.ini             ← File configurazione (IMPORTANTE!)
│   ├── scripts/                   ← Tutti gli script
│   ├── docs/                      ← Tutta la documentazione
│   └── PyQt6/                     ← Librerie PyQt6 (auto-incluso)
```

## Come costruire l'EXE

### Prerequisiti
- Python 3.8+
- Tutte le dipendenze installate (pip install -r requirements.txt)

### Step 1: Installa le dipendenze di build
```powershell
cd C:\path\to\SYS-Toolset
pip install -r requirements.txt
```

### Step 2: Crea l'eseguibile
```powershell
.\build.ps1
```

#### Opzioni di build:
```powershell
# Build standard (directory con file separati)
.\build.ps1

# Build monolite (singolo file exe, più lento)
.\build.ps1 -OneFile

# Build con console visibile (per debug)
.\build.ps1 -Console

# Pulisci build precedenti e ricompila
.\build.ps1 -Clean

# Combina opzioni
.\build.ps1 -Clean -OneFile

cd "C:\Users\alex.sorrentino\OneDrive - DGS SpA\Desktop\TC\SYS-Toolset" ; Remove-Item -Path "dist", "build" -Recurse -Force -ErrorAction SilentlyContinue; .\build.ps1 -Clean -OneFile 2>&1 | Select-Object -Last 10
```

### Step 3: Usa l'eseguibile
L'eseguibile sarà in `dist/SystemToolset/`

```powershell
cd dist/SystemToolset
.\SystemToolset.exe
```

## File di Configurazione (CRUCIALE)

### Dove si trova
L'applicazione cerca il file `config.ini` in questo ordine:
1. **Stessa cartella dell'exe** ← Posizione primaria
2. Cartella `config/` nella cartella dell'exe
3. Root del progetto
4. Cartella `src/config/`

### Come funziona il percorso relativo
Quando distribuisci l'exe, i percorsi in `config.ini` sono relativi alla cartella dell'exe:

```ini
[PATHS]
scripts_directory = scripts
docs_directory = docs
logs_directory = logs
```

Se l'exe è in `C:\Program Files\SystemToolset\`, allora:
- Scripts: `C:\Program Files\SystemToolset\scripts\`
- Docs: `C:\Program Files\SystemToolset\docs\`
- Logs: `C:\Program Files\SystemToolset\logs\`

### Distribuzione consigliata
Mantieni questa struttura:
```
C:\Program Files\SystemToolset\
├── SystemToolset.exe
├── config.ini
├── scripts/
│   ├── dispatcher/
│   ├── indexer/
│   ├── RoboTC/
│   └── index.json
└── docs/
    ├── dispatcher/
    ├── indexer/
    └── robotc/
```

## Dettagli Tecnici

### Cosa include PyInstaller
L'exe compilato contiene:
- Interprete Python completo
- Tutte le librerie Python richieste (PyQt6, etc.)
- File di configurazione
- Script e documentazione

### Dimensione dell'exe
- Modalità directory: ~150-200 MB (consigliato)
- Modalità singolo file: ~200-250 MB (più lento all'avvio)

### Tempo di avvio
- Prima volta: 3-5 secondi (caricamento Python)
- Successivi: 1-2 secondi (cache)

## Configurazione Centralizzata

### Come funziona
Il file `src/config/config.py` contiene una classe `ConfigManager` singleton che:

1. Legge il file `config.ini`
2. Fornisce un accesso centralizzato ai settings
3. Gestisce automaticamente i percorsi relativi/assoluti
4. Fornisce default se config non trovato

### Uso nella code
```python
from config.config import ConfigManager

config = ConfigManager()

# Accesso ai percorsi
scripts_dir = config.scripts_dir
docs_dir = config.docs_dir
logs_dir = config.logs_dir

# Accesso ai settings
title = config.app_title
debug = config.debug
window_size = config.window_size
```

### Aggiungere nuove configurazioni
Modifica `config/config.ini`:
```ini
[MIA_SEZIONE]
mio_setting = valore
```

Leggi dalla code:
```python
config = ConfigManager()
valore = config.get('MIA_SEZIONE', 'mio_setting')
valore_int = config.get_int('MIA_SEZIONE', 'mio_setting', fallback=10)
```

## Distribuzione

### Opzione 1: Cartella Portabile
1. Compila con `.\build.ps1`
2. Copia `dist/SystemToolset/` in una USB o cloud
3. L'utente estrae e clicca SystemToolset.exe
4. Nessuna installazione richiesta

### Opzione 2: Installer
Puoi creare un installer usando NSIS o Inno Setup:
```powershell
# Esempio con Inno Setup
# Crea un file .iss e esegui
"C:\Program Files (x86)\Inno Setup 6\iscc.exe" installer.iss
```

### Opzione 3: Distribuzione su Network
Copia `dist/SystemToolset/` su un share di rete:
```powershell
xcopy /E /I dist\SystemToolset \\server\apps\SystemToolset
# Gli utenti creano un collegamento al .exe
```

## Troubleshooting

### "config.ini not found"
- Verifica che `config.ini` sia nella stessa cartella dell'exe
- O nella cartella `config/` accanto all'exe
- O modifica il codice per specificare il percorso assoluto

### "Scripts directory not found"
- Verifica che `scripts/` sia nella stessa cartella dell'exe
- Controlla che il percorso in `config.ini` sia corretto
- Ricrea con: `.\build.ps1 -Clean`

### L'exe non si avvia
- Prova con: `.\build.ps1 -Console` per vedere i messaggi di errore
- Verifica che PyQt6 sia installato: `pip install PyQt6`
- Controlla i log in `logs/` se creato

### Slow performance
- Ricompila con versione directory (non `-OneFile`)
- Aumenta la RAM disponibile durante il build
- Usa SSD per il disco di build

## Automazione della distribuzione

### Script per distribuire l'exe
```powershell
# deploy.ps1
$SourcePath = "dist\SystemToolset"
$DestPath = "\\server\apps\SystemToolset"

Remove-Item -Path $DestPath -Recurse -ErrorAction SilentlyContinue
Copy-Item -Path $SourcePath -Destination $DestPath -Recurse

Write-Host "✓ Deployment completato" -ForegroundColor Green
```

### Creare shortcut sul desktop
```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\SystemToolset.lnk")
$Shortcut.TargetPath = "C:\Program Files\SystemToolset\SystemToolset.exe"
$Shortcut.Save()
```

## Aggiornamenti futuri

### Versionamento
Modifica `src/config/setting.py`:
```ini
[APP]
version = 1.0.0
```

### Gestione degli aggiornamenti
Considera uno script che:
1. Controlla la versione online
2. Scarica automaticamente la versione nuova
3. Backup della versione precedente
4. Restart dell'app

## Contatti e Supporto

Per problemi nella compilazione o distribuzione, contattare il team Development.

---

**Ultima modifica:** 2026-01-12  
**Versione:** 1.0.0
