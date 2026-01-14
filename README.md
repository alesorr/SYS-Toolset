# System Toolset - Guida Completa (CLI → GUI → EXE)

## 📋 Indice
1. [Panoramica](#panoramica)
2. [Architettura](#architettura)
3. [Come avviare](#come-avviare)
4. [Da CLI a GUI](#da-cli-a-gui)
5. [Creare l'EXE](#creare-lexe)
6. [Configurazione Centralizzata](#configurazione-centralizzata)

---

## Panoramica

Questo progetto è stato trasformato da un'applicazione CLI semplice a una **GUI moderna e distribuibile come EXE standalone**.

### Timeline della trasformazione

```
V1: CLI semplice (main.py con Rich)
  ↓
V2: GUI moderna (PyQt6 con documentazione integrata)
  ↓
V3: EXE standalone (distribuzione senza Python)
```

---

## Architettura

### Struttura del Progetto

```
SYS-Toolset/
├── src/
│   ├── app.py                    ← Entry point universale (Python + EXE)
│   ├── main.py                   ← CLI tradizionale
│   ├── gui_main.py              ← GUI (legacy, usare app.py)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config.py            ← ConfigManager (NUOVO - singleton)
│   │   └── setting.py
│   ├── gui/
│   │   ├── __init__.py
│   │   └── main_window.py       ← Interfaccia PyQt6
│   ├── db/
│   │   └── script_repository.py
│   ├── menu/
│   │   └── tool_menu.py
│   └── utils/
│
├── config/
│   └── config.ini               ← CONFIGURAZIONE CENTRALIZZATA (NUOVO)
│
├── docs/                        ← Documentazione Markdown per ogni tool
│   ├── dispatcher/
│   ├── indexer/
│   └── robotc/
│
├── scripts/                     ← Script da eseguire
│   ├── dispatcher/
│   ├── indexer/
│   └── RoboTC/
│
├── build.ps1                    ← Script di compilazione EXE (NUOVO)
├── BUILD_EXE.md                ← Guida compilazione EXE (NUOVO)
├── requirements.txt            ← Dipendenze (aggiunto PyInstaller)
└── README.md                   ← Questo file
```

---

## Come avviare

### Opzione 1: Versione GUI Python (CONSIGLIATO in sviluppo)
```powershell
cd C:\path\to\SYS-Toolset
pip install -r requirements.txt
python src/app.py
```

### Opzione 2: Versione CLI Python (Legacy)
```powershell
python src/main.py
```

### Opzione 3: Versione EXE (CONSIGLIATO in produzione)
```powershell
# Compila prima
.\build.ps1

# Avvia l'exe
dist\SystemToolset\SystemToolset.exe
```

---

## Da CLI a GUI

### Cosa è cambiato

| Aspetto | CLI | GUI |
|--------|-----|-----|
| **Framework** | Rich console | PyQt6 |
| **Interfaccia** | Menu testuale | Interfaccia grafica moderna |
| **Documentazione** | File MD separati | Viewer integrato |
| **Esecuzione** | Sincrone, blocca UI | Async in thread separato |
| **Configurazione** | Hardcoded o flag | File config.ini centralizzato |
| **Distribuzione** | Solo Python | Exe standalone |

### Feature della GUI

✅ **Selezione intuitiva categorie/script**  
✅ **Output in tempo reale**  
✅ **Documentazione integrata (markdown viewer)**  
✅ **Thread separato (non blocca UI)**  
✅ **Contrasto e leggibilità ottimali**  
✅ **Tema consistente**

---

## Creare l'EXE

### Quick Start (5 minuti)

```powershell
# 1. Installa dipendenze (una volta)
pip install -r requirements.txt

# 2. Compila
.\build.ps1

# 3. Prova
dist\SystemToolset\SystemToolset.exe
```

### Opzioni di Compilazione

```powershell
# Compila come directory (più veloce, consigliato)
.\build.ps1

# Compila come singolo file (più lento)
.\build.ps1 -OneFile

# Compila con console visibile (per debug)
.\build.ps1 -Console

# Pulisci e ricompila
.\build.ps1 -Clean

# Combina opzioni
.\build.ps1 -Clean -OneFile
```

### Distribuzione dell'EXE

L'exe è **completamente standalone**. Puoi:
- Copiarla su una USB
- Mandarla via email
- Metterla su un drive di rete
- Creare un installer

Nessuna installazione di Python richiesta.

### Struttura dopo la compilazione

```
dist/SystemToolset/
├── SystemToolset.exe       ← Eseguibile (doppio click!)
├── config/
│   └── config.ini          ← IMPORTANTE: Configurazione
├── scripts/                ← Tutti gli script
├── docs/                   ← Tutta la documentazione
└── PyQt6/                  ← Librerie (auto-incluso)
```

---

## Configurazione Centralizzata

### File config.ini

Il file `config/config.ini` è il **cuore della configurazione**:

```ini
[PATHS]
scripts_directory = scripts
docs_directory = docs
logs_directory = logs

[APP]
title = System Toolset - GUI Interface
version = 1.0.0
window_width = 1200
window_height = 700
debug = false

[UI]
theme = light
font_family = Arial
font_size = 10

[EXECUTION]
timeout_seconds = 300
show_timestamps = true
log_execution = true
```

### Come funziona il ConfigManager

```python
from config.config import ConfigManager

config = ConfigManager()  # Singleton - una sola istanza

# Accesso semplice
scripts = config.scripts_dir      # Path object
docs = config.docs_dir
title = config.app_title
debug = config.debug

# Accesso generico
value = config.get('SECTION', 'key', fallback='default')
```

### Percorsi Relativi vs Assoluti

Il ConfigManager è intelligente:
- **Se percorso assoluto**: Usalo così
- **Se percorso relativo**: Fallo relativo alla cartella dell'app
  - Python: relativo alla root del progetto
  - EXE: relativo alla cartella dell'exe

### Ricerca del config.ini

L'app cerca il file in questo ordine:
1. **Stessa cartella dell'exe** ← Primaria per EXE
2. `config/` nella cartella dell'exe
3. Root del progetto
4. `src/config/`

---

## Dettagli Tecnici

### Dipendenze

```
PyQt6>=6.0.0      - Framework GUI
PyInstaller>=6.0.0 - Compilazione EXE
rich              - Output console migliorato (legacy)
colorama          - Colori console (legacy)
```

### File Chiave

#### `src/config/config.py`
- Singleton ConfigManager
- Gestisce config.ini
- Fornisce accesso centralizzato
- Supporta percorsi relativi/assoluti

#### `src/gui/main_window.py`
- Interfaccia principale PyQt6
- ScriptExecutorThread per esecuzione non-blocking
- DocumentationViewer per file MD
- Integrazione con ConfigManager

#### `src/app.py`
- Entry point universale
- Funziona sia da Python che EXE
- Gestisce automaticamente i percorsi
- Verifica config e script

#### `build.ps1`
- Script PowerShell per compilare l'exe
- Usa PyInstaller
- Include file necessari (config.ini, scripts, docs)
- Opzioni di compilazione flessibili

---

## Troubleshooting

### La GUI non si avvia da Python
```powershell
# Installa dipendenze
pip install -r requirements.txt

# Verifica che config.ini esista
Test-Path config/config.ini

# Verifica che scripts esista
Test-Path scripts
```

### L'EXE non funziona
```powershell
# 1. Verifica che config.ini sia nella cartella dell'exe
# 2. Verifica che scripts/ e docs/ esistano accanto all'exe
# 3. Ricompila da zero
.\build.ps1 -Clean
```

### "No module named config"
```powershell
# Il file config.ini non è stato incluso nel build
# Ricompila con:
.\build.ps1 -Clean
```

### Performance lenta dell'EXE
- Prima esecuzione è lenta (caricamento Python)
- Le successive sono più veloci (cache)
- In produzione, pre-caldi l'exe con un'esecuzione test

---

## Workflow di Sviluppo

### Sviluppo locale
```powershell
cd src
python app.py
```

### Testing prima di rilasciare
```powershell
# Test GUI
python src/app.py

# Compila e testa EXE
.\build.ps1
dist\SystemToolset\SystemToolset.exe
```

### Rilascio in produzione
```powershell
# Compila versione finale
.\build.ps1 -Clean

# Copia dist/SystemToolset/ al server di distribuzione
xcopy /E /I dist\SystemToolset \\server\releases\SystemToolset_v1.0.0
```

---

## Domande Frequenti

### D: Posso modificare config.ini per cambiare percorsi?
**R:** Sì! Modifica `config/config.ini` e riavvia l'app. Perfetto per adattarsi a diversi ambienti.

### D: Come aggiungo un nuovo script?
**R:** 
1. Copia lo script in `scripts/categoria/`
2. Aggiungi entry a `scripts/index.json`
3. Se vuoi documentazione, crea file .md in `docs/categoria/`

### D: Posso customizzare l'interfaccia grafica?
**R:** Modifica `src/gui/main_window.py`:
- Colori in `apply_styles()`
- Layout in `initUI()`
- Font in `config.ini` [UI]

### D: Come distribisco l'app in azienda?
**R:** Copia `dist/SystemToolset/` su uno share di rete:
```powershell
\\server\apps\SystemToolset\SystemToolset.exe
```
Gli utenti creano un collegamento sul desktop.

### D: Posso fare un installer (.msi/.exe)?
**R:** Sì! Usa Inno Setup, NSIS, o WiX per creare un installer che copia i file di `dist/SystemToolset/`.

---

## Roadmap Futuri

- [ ] Autoupdate automatico
- [ ] Dark mode
- [ ] Ricerca script
- [ ] Favoriti/cronologia
- [ ] Export log
- [ ] Notifiche audio
- [ ] Schedulazione script

---

## Contatti

**Team:** Internal Systems Automation Team  
**Data creazione:** 2026-01-12  
**Versione:** 1.0.0

Per domande o problemi, contattare il team di sviluppo.
