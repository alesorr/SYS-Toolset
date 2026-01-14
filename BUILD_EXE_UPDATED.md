# Compilazione a .EXE - Guida Completa

## Panoramica

Questo documento descrive come compilare l'applicazione System Toolset in un eseguibile Windows (.exe) standalone usando PyInstaller.

## Prerequisiti

- **Windows 7+**
- **Python 3.8+** installato e nel PATH
- **Git** (opzionale, per clonare il repo)

## Processo di Build Automatico

Lo script `build.ps1` automatizza completamente il processo:

```powershell
[1/6] Setup Virtual Environment
   - Crea venv se non esiste
   - Attiva la virtual environment
   
[2/6] Installazione dipendenze
   - Installa tutti i package da requirements.txt
   - PyQt6, Rich, PyInstaller, ecc.
   
[3/6] Verificazione PyInstaller
   - Controlla se PyInstaller è installato
   - Installa se mancante
   
[4/6] Pulizia build precedenti (opzionale)
   - Rimuove directory build/ dist/
   - Usa flag -Clean per forzare
   
[5/6] Compilazione PyInstaller
   - Esegue PyInstaller con tutte le configurazioni
   - Incorpora assets (scripts, docs, config)
   - Crea l'eseguibile finale
   
[6/6] Verifica e output
   - Controlla il risultato
   - Mostra percorso eseguibile finale
```

## Come eseguire il Build

### Opzione 1: Build standard (CONSIGLIATO)
```powershell
cd C:\path\to\SYS-Toolset
.\build.ps1
```

Questo farà:
1. ✓ Setup venv (se non esiste)
2. ✓ Installa dipendenze
3. ✓ Compila in exe
4. ✓ Produce: `dist/SystemToolset.exe`

### Opzione 2: Build con pulizia totale
```powershell
.\build.ps1 -Clean
```
Utile se hai problemi con build precedenti.

### Opzione 3: Build come file singolo (più lento)
```powershell
.\build.ps1 -OneFile
```
Crea un singolo .exe (~150 MB) invece di directory.

### Opzione 4: Build con console visibile (debug)
```powershell
.\build.ps1 -Console
```
Mostra finestra console se ci sono errori.

## Cosa fa il build.ps1

```powershell
# 1. SETUP VENV (NUOVO!)
if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\Activate.ps1

# 2. INSTALL DEPENDENCIES (NUOVO!)
pip install -r requirements.txt --quiet

# 3. VERIFICA PYINSTALLER
pip show pyinstaller  # se non esiste, lo installa

# 4. PULIZIA (Opzionale)
# Remove-Item build, dist, *.spec

# 5. PYINSTALLER
pyinstaller src/app.py `
  --name=SystemToolset `
  --windowed `
  --onefile `
  --collect-all=PyQt6 `
  --add-data="config/config.ini:config" `
  --add-data="scripts:scripts" `
  --add-data="docs:docs"
```

## Configurazione Centralizzata

Il file `config/config.ini` gestisce tutte le impostazioni:

```ini
[paths]
scripts_path = scripts
docs_path = docs
config_path = config

[settings]
timeout_seconds = 300
log_level = INFO
```

Quando crei l'exe, il file config.ini viene incluso automaticamente e deve rimanere nella stessa cartella dell'eseguibile.

## Output della Compilazione

Dopo il build completato con successo:

```
╔════════════════════════════════════════════════════════════╗
║   System Toolset - Build EXE (PyInstaller)                ║
╚════════════════════════════════════════════════════════════╝

[1/6] Setup Virtual Environment...
  → Creazione venv...
  ✓ venv creato

[2/6] Installazione dipendenze...
  ✓ Dipendenze installate

[3/6] Verificando PyInstaller...
  ✓ PyInstaller già presente

[4/6] Compilando come directory...

[5/6] Modalità: GUI senza console

✓ Build completato con successo!

[6/6] Verificando output...
✓ Directory creata: dist/SystemToolset/
  Eseguibile: dist/SystemToolset/SystemToolset.exe

[7/7] Istruzioni per l'uso:
  1. Copia l'intera cartella 'dist/SystemToolset' dove desideri
  2. Assicurati che 'config.ini' sia nella stessa cartella dell'exe
  3. Doppio click su SystemToolset.exe per avviare l'app

╔════════════════════════════════════════════════════════════╗
║   Build completato con successo!                           ║
╚════════════════════════════════════════════════════════════╝
```

## Distribuzione dell'EXE

### Metodo 1: Directory Completa (CONSIGLIATO)

```
1. Naviga in dist/SystemToolset/
2. Copia l'intera cartella dove desideri
3. Verifica che config.ini sia presente
4. Doppio click su SystemToolset.exe
```

Struttura finale:
```
SystemToolset/
├── SystemToolset.exe         ← Eseguibile principale
├── config.ini                ← File configurazione
├── scripts/                  ← Tutti gli script
├── docs/                     ← Documentazione
└── [altre dipendenze]
```

### Metodo 2: File Singolo

Se usi `.\build.ps1 -OneFile`:

```
1. Copia dist/SystemToolset.exe dove desideri
2. Copia config.ini nella stessa cartella
3. Doppio click per avviare
```

**Pro**: Un singolo file  
**Contro**: Più grande (~150 MB) e più lento al primo avvio

## Cosa è incluso nell'EXE

✓ Python 3.13+ embeddato  
✓ PyQt6 completo  
✓ Rich library  
✓ Tutti gli script in scripts/  
✓ Tutta la documentazione in docs/  
✓ File di configurazione  
✓ Nessuna dipendenza esterna richiesta  

## Requisiti di Sistema

- **OS**: Windows 7+
- **Memoria**: 200+ MB RAM libera
- **Disco**: 100-150 MB spazio libero (file singolo) o 50-80 MB (directory)
- **Permessi**: Admin (per eseguire script di sistema)

## Troubleshooting

### Errore "venv non trovato"
```powershell
# Il build.ps1 lo crea automaticamente, ma se non funziona:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\build.ps1
```

### Errore "dependencies not installed"
```powershell
# Assicurati che pip aggiorna:
python -m pip install --upgrade pip
.\build.ps1 -Clean
```

### PyInstaller fallisce
```powershell
# Reinstalla dalla cartella corretta:
.\venv\Scripts\pip install --upgrade pyinstaller
.\build.ps1 -Clean
```

### L'app non trova i file
- ✓ Verifica che `config.ini` sia nella stessa cartella dell'exe
- ✓ Controlla che `scripts/` e `docs/` siano in `dist/SystemToolset/`
- ✓ Verifica i path in config.ini

### Errore "No module named PyQt6"
```powershell
# PyInstaller non ha raccolto PyQt6, prova:
.\build.ps1 -Clean
# Se ancora fallisce:
pip install --upgrade PyQt6
.\build.ps1
```

## Personalizzazione

### Cambiare l'icona dell'applicazione
1. Prepara un file `icon.ico` (32x32 o 256x256)
2. Sostituisci il file `icon.ico` nella root
3. Esegui: `.\build.ps1 -Clean`

### Cambiare il nome dell'eseguibile
Modifica `build.ps1`, riga con `--name=`:
```powershell
"--name=MioToolset"  # Cambia da SystemToolset
```

### Cambiare la modalità (file singolo vs directory)
Modifica `build.ps1`:
```powershell
"--onefile",      # Togli il # per file singolo
"--windowed",     # Togli il # per nascondere console
```

### Aggiungere file al package
Modifica `build.ps1`, add a `--add-data`:
```powershell
"--add-data=scripts:scripts",
"--add-data=docs:docs",
"--add-data=config/config.ini:config",
"--add-data=my_new_folder:my_new_folder"  # ← Aggiungi qui
```

## Redistribuzione

Quando distribuisci l'eseguibile a terzi:

1. **Crea un ZIP** dell'intera cartella `dist/SystemToolset/`
2. **Includi un README** con istruzioni:
   ```
   System Toolset v1.0
   
   Come installare:
   1. Estrai il ZIP
   2. Doppio click su SystemToolset.exe
   
   Requisiti: Windows 7+, 150 MB disco
   ```
3. **Specifica di non modificare config.ini**
4. **Aggiungi il tuo nome/organizzazione**

## Performance

| Metrica | Valore |
|---------|--------|
| Tempo primo build | 3-5 minuti |
| Tempo rebuild | 30-60 secondi |
| Dimensione (file singolo) | 100-150 MB |
| Dimensione (directory) | 50-80 MB |
| Tempo avvio primo | 2-3 secondi |
| Tempo avvio successivi | < 1 secondo |
| Utilizzo RAM runtime | 150-200 MB |

## Automatizzazione

Puoi creare un file batch per facilitare il build:

**build.bat** (per chi preferisce batch):
```batch
@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File build.ps1 %*
pause
```

Poi puoi semplicemente fare doppio click su build.bat.

## Support e Debug

Se il build continua a fallire:

1. **Verifica Python**:
   ```powershell
   python --version  # Deve essere 3.8+
   pip --version
   ```

2. **Verifica percorsi**:
   ```powershell
   ls requirements.txt
   ls src/app.py
   ls config/config.ini
   ```

3. **Prova build manuale**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install pyinstaller
   pyinstaller src/app.py --windowed --onefile
   ```

4. **Chiedi aiuto** con output completo del build

## Domande Frequenti

**D: Posso eseguire l'exe senza installare Python?**  
R: Sì! L'exe contiene Python embedded. Non è necessaria alcuna installazione.

**D: Quanto spazio occupa?**  
R: Circa 100-150 MB per file singolo, 50-80 MB per directory completa.

**D: Posso redistribuire l'exe?**  
R: Sì, purché rispetti le licenze (PyQt6, Rich, ecc.). Aggiungi una nota.

**D: Come aggiorno se cambio il codice?**  
R: Modifica il codice e esegui `.\build.ps1 -Clean` per ricompilare.

**D: Posso lanciare l'exe da una rete/USB?**  
R: Sì! L'exe è completamente standalone. Funziona da qualsiasi posizione.

**D: È il primo build che prende più tempo?**  
R: Sì! Primo build 3-5 minuti, rebuild < 1 minuto.

## Versioni future

Miglioramenti possibili:
- [ ] Auto-update tramite launcher
- [ ] Installer MSI
- [ ] Firma digitale codice
- [ ] Compressione UPX
- [ ] Versioni per Linux/Mac
