# System Toolset - Interfaccia Grafica

## Panoramica
L'applicazione è stata trasformata da un'interfaccia CLI (Command Line Interface) a un'interfaccia grafica moderna basata su **PyQt6**.

## Struttura del progetto

```
SYS-Toolset/
├── src/
│   ├── main.py                 # Entry point CLI (ancora disponibile)
│   ├── gui_main.py            # Entry point GUI (NUOVO)
│   ├── gui/                   # Modulo interfaccia grafica (NUOVO)
│   │   ├── __init__.py
│   │   └── main_window.py     # Finestra principale dell'applicazione
│   ├── menu/
│   │   └── tool_menu.py       # Menu CLI (ancora supportato)
│   ├── db/
│   │   └── script_repository.py
│   └── ...
├── docs/                      # NUOVO - Documentazione per ogni tool
│   ├── dispatcher/
│   │   └── restartdispatcher.md
│   ├── indexer/
│   │   └── reindexdata.md
│   └── robotc/
│       ├── extract_organization_information.md
│       └── user_management.md
├── scripts/
│   ├── dispatcher/
│   ├── indexer/
│   ├── RoboTC/
│   └── index.json
└── requirements.txt           # Aggiornato con PyQt6
```

## Come avviare l'applicazione

### Versione Grafica (CONSIGLIATO)
```powershell
cd C:\path\to\SYS-Toolset
python src/gui_main.py
```

### Versione CLI (Legacy)
```powershell
cd C:\path\to\SYS-Toolset
python src/main.py
```

## Installazione dipendenze

Prima di avviare l'applicazione, installa le dipendenze:

```powershell
pip install -r requirements.txt
```

## Caratteristiche della GUI

### 1. **Selezione Categoria**
- Elenco intuitivo di tutte le categorie di tool disponibili
- Selezione con click del mouse
- Indicatore visivo della categoria attiva

### 2. **Lista Script**
- Visualizza tutti gli script della categoria selezionata
- Nome descrittivo e breve descrizione
- Selezione facile e veloce

### 3. **Dettagli Script**
- Nome e descrizione completa dello script
- Bottoni di azione:
  - **Esegui Script** (▶): Avvia l'esecuzione
  - **Documentazione** (📖): Visualizza la documentazione MD integrata

### 4. **Output Esecuzione**
- Visualizzazione in tempo reale dell'output dello script
- Differenziazione tra output (bianco) ed errori (rosso)
- Scroll automatico
- Font monospace per chiarezza

### 5. **Viewer Documentazione**
- Visualizzazione diretta dei file MD
- Supporto per formattazione markdown
- Dialog separato, non invasivo

## Documentazione disponibile

Ogni tool ha una documentazione completa in formato Markdown con:

### Dispatcher - RestartDispatcher
- [restartdispatcher.md](../docs/dispatcher/restartdispatcher.md)
- Funzioni, parametri, quando usarlo, troubleshooting

### Indexer - ReindexData
- [reindexdata.md](../docs/indexer/reindexdata.md)
- Procedure, tempistiche, monitoraggio, manutenzione

### RoboTC - Extract Organization Information
- [extract_organization_information.md](../docs/robotc/extract_organization_information.md)
- Sincronizzazione, estrazione, reconciliazione dati

### RoboTC - User Management
- [user_management.md](../docs/robotc/user_management.md)
- Creazione utenti, modifica, bulk operations, audit

## Requisiti di sistema

- **Windows 7+** (o Linux/macOS)
- **Python 3.8+**
- **PyQt6** (installato via requirements.txt)
- **Permessi amministratore** (per eseguire script di sistema)

## Guida utente

### Eseguire uno script
1. Seleziona una **categoria** dal pannello sinistro
2. Seleziona uno **script** dalla lista
3. Clicca su **▶ Esegui Script**
4. Attendi il completamento (visualizzato nell'area output)

### Visualizzare la documentazione
1. Seleziona uno **script**
2. Clicca su **📖 Visualizzazione Documentazione**
3. Una finestra separata mostra la documentazione formattata
4. Chiudi la finestra quando finito

### Monitorare l'esecuzione
- L'output è visualizzato in tempo reale
- Errori sono evidenziati in rosso
- Al completamento, vedrai il messaggio "✅ Esecuzione completata"

## Architettura

### Componenti principali

#### `MainWindow`
Classe principale dell'interfaccia grafica che gestisce:
- Layout e widget
- Interazione utente
- Coordinamento con il repository

#### `ScriptExecutorThread`
Thread dedicato per eseguire gli script:
- Non blocca l'interfaccia
- Comunica l'output via signal Qt
- Gestisce errori e eccezioni

#### `DocumentationViewer`
Dialog modale per visualizzare la documentazione:
- Rendering markdown
- Scroll automatico
- Tema coerente con l'app

### Database degli script
Il file `scripts/index.json` contiene la definizione di:
- Categorie disponibili
- Script per categoria
- Descrizioni e parametri

Formato:
```json
{
    "NomeCategoria": [
        {
            "name": "Nome Script",
            "description": "Descrizione breve",
            "path": "percorso/script.ps1",
            "params": ["parametro1", "parametro2"]
        }
    ]
}
```

## Estensioni future

### Possibili miglioramenti
1. **Favoriti**: Salva gli script usati di frequente
2. **Cronologia**: Visualizza gli script eseguiti recentemente
3. **Parametri personalizzati**: UI per inserire parametri script
4. **Export log**: Salva l'output dell'esecuzione su file
5. **Tema scuro**: Modalità dark theme per ridurre l'affaticamento
6. **Cercare**: Field di ricerca per trovare script rapidamente
7. **Notifiche**: Avviso audio/popup al completamento
8. **Schedulazione**: Pianificazione automatica degli script

## Troubleshooting

### L'applicazione non si avvia
```powershell
# Verifica l'installazione di Python
python --version

# Installa le dipendenze
pip install -r requirements.txt

# Prova da riga di comando
python src/gui_main.py
```

### Errore "No module named PyQt6"
```powershell
pip install PyQt6 --upgrade
```

### Gli script non si eseguono
- Verificare i permessi (admin se richiesto)
- Controllare il percorso dello script in `index.json`
- Verificare che il file dello script esista

### La documentazione non si visualizza
- Verificare che il file MD esista in `/docs`
- Controllare il naming del file (minuscole, underscores)
- Provare il path manuale nel dialog

## Contatti e Supporto

Per problemi o suggerimenti:
- Team: Internal Systems Automation Team
- Data creazione: 2026-01-12
- Ultima modifica: 2026-01-12
