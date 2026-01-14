# 🚀 COME CREARE L'EXE - Quick Reference

## Comando rapido
```powershell
cd C:\Users\alex.sorrentino\OneDrive - DGS SpA\Desktop\TC\SYS-Toolset
pip install -r requirements.txt
.\build.ps1
dist\SystemToolset\SystemToolset.exe
```

## Cosa cambia tra versioni

### Versione Python (Sviluppo)
```
python src/app.py
```
- Perfetto per sviluppo
- Richiede Python installato
- File config.ini deve essere in `config/`

### Versione EXE (Produzione)
```
dist\SystemToolset\SystemToolset.exe
```
- Completamente standalone
- Nessuna dipendenza esterna
- File config.ini deve stare accanto all'exe
- Distribuzione facile (copia cartella)

## File di Configurazione - IMPORTANTE ⚠️

### Dove deve stare
- **Per Python**: `config/config.ini` nella root
- **Per EXE**: `config/config.ini` nella stessa cartella dell'exe

### Cosa contiene
```ini
[PATHS]
scripts_directory = scripts       # ← Relativo all'app
docs_directory = docs             # ← Relativo all'app
logs_directory = logs             # ← Relativo all'app

[APP]
window_width = 1200
window_height = 700
debug = false
```

### Percorsi relativi
Sono **relativi alla cartella dell'applicazione**:
- Se app è in `C:\Program Files\SystemToolset\`
- Allora `scripts_directory = scripts` significa `C:\Program Files\SystemToolset\scripts\`

## Struttura EXE finale

```
C:\Program Files\SystemToolset\
├── SystemToolset.exe             ← Doppio click!
├── config/
│   └── config.ini                ← VITALE!
├── scripts/
│   ├── dispatcher/
│   ├── indexer/
│   └── RoboTC/
└── docs/
    ├── dispatcher/
    ├── indexer/
    └── robotc/
```

## Opzioni di compilazione

```powershell
.\build.ps1                  # Standard (directory)
.\build.ps1 -OneFile         # Singolo file (più lento)
.\build.ps1 -Console         # Mostra console per debug
.\build.ps1 -Clean           # Pulisci e ricompila
.\build.ps1 -Clean -OneFile  # Combina opzioni
```

## Distribuzione

### Opzione 1: Cartella portabile (USB, cloud)
```powershell
# Copia questa cartella:
dist\SystemToolset\

# L'utente:
# 1. Estrae la cartella
# 2. Doppio click su SystemToolset.exe
# 3. Funziona! (nessuna installazione)
```

### Opzione 2: Share di rete
```powershell
# Admin copia:
xcopy /E /I dist\SystemToolset \\server\apps\SystemToolset

# Utenti creano collegamento a:
\\server\apps\SystemToolset\SystemToolset.exe
```

### Opzione 3: Installer
Usa Inno Setup, NSIS, o WiX per creare un .msi

## ConfigManager - Come funziona

```python
from config.config import ConfigManager

config = ConfigManager()

# Percorsi - gestiti automaticamente
scripts = config.scripts_dir       # Path object
docs = config.docs_dir

# Settings
title = config.app_title           # string
width, height = config.window_size # tuple (int, int)
is_debug = config.debug            # bool

# Generico
value = config.get('SECTION', 'key', fallback='default')
```

### Ricerca automatica config.ini
1. Cartella dell'exe
2. `config/` nella cartella dell'exe
3. Root del progetto
4. `src/config/`

Perfetto per:
- Exe in C:\Program Files\ cerca in C:\Program Files\config\config.ini
- Python in C:\dev\app\ cerca in C:\dev\app\config\config.ini

## Checklist pre-rilascio

- [ ] `pip install -r requirements.txt`
- [ ] `.\build.ps1 -Clean`
- [ ] Verifica che `dist\SystemToolset\config\config.ini` esista
- [ ] Verifica che `dist\SystemToolset\scripts\` abbia i file
- [ ] Verifica che `dist\SystemToolset\docs\` abbia le doc
- [ ] Prova l'exe da PowerShell: `dist\SystemToolset\SystemToolset.exe`
- [ ] Copia tutta la cartella `dist\SystemToolset\` al server

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| "config.ini not found" | Verifica che sia nella cartella dell'exe |
| "scripts directory not found" | Verifica che `scripts/` sia accanto all'exe |
| L'exe non si avvia | Ricompila: `.\build.ps1 -Clean -Console` |
| Errore PyQt6 | `pip install PyQt6 --upgrade` |
| L'exe è lento | Ricompila senza `-OneFile`, usa versione directory |

## File chiave della soluzione

```
src/
├── app.py              ← Entry point (usa questo!)
├── config/config.py    ← ConfigManager singleton
└── gui/main_window.py  ← UI principale

config/config.ini       ← CONFIGURAZIONE CENTRALIZZATA

build.ps1              ← Script compilazione
```

---

**Ricorda:** Il file `config.ini` è il cuore della configurazione!  
Modifica quello per adattare l'app a diversi ambienti senza riconiarlo.

Data: 2026-01-12
