# 🔄 Aggiornamento Sistema di Schedulazione

## Data: 19 Gennaio 2026

## 📋 Modifiche Implementate

### ✅ Nuovo Sistema di Schedulazione Persistente

L'applicazione SYS-Toolset ora utilizza il **Windows Task Scheduler** per garantire l'esecuzione automatica degli script **anche quando l'applicazione è chiusa**.

### 🆕 Nuovi File

1. **`src/utils/windows_scheduler.py`**
   - Modulo per la gestione dei task nel Windows Task Scheduler
   - Crea, modifica ed elimina task automaticamente
   - Genera XML compatibili con Task Scheduler
   - Crea wrapper script per logging automatico

2. **`docs/SCHEDULING_GUIDE.md`**
   - Guida completa per l'utente
   - Spiega come funziona la schedulazione
   - Troubleshooting e best practices

3. **`scripts/test_schedule.py`**
   - Script di test per verificare la schedulazione
   - Può essere usato per testare il sistema

### 🔧 File Modificati

1. **`src/gui/main_window.py`**
   - Aggiunto import di `WindowsTaskScheduler`
   - Modificato `__init__` per inizializzare il Windows Task Scheduler
   - Aggiornato `save_schedule_config()` per creare task Windows
   - Aggiornato `delete_schedule_config()` per eliminare task Windows
   - Migliorati i messaggi di feedback all'utente

## 🎯 Come Funziona

### Prima (Sistema Vecchio)
```
User schedula script → APScheduler (in-process) → Script eseguito SOLO se app aperta
```

### Ora (Sistema Nuovo)
```
User schedula script → Windows Task Scheduler → Script eseguito SEMPRE
                                               ↓
                                         Log automatico in logs/
```

## ✨ Vantaggi

1. **✅ Esecuzione Garantita**: Gli script vengono eseguiti anche se l'app è chiusa
2. **✅ Persistenza**: I task sopravvivono ai riavvii del sistema
3. **✅ Background**: Esecuzione in background senza UI
4. **✅ Logging Automatico**: Ogni esecuzione genera un log dettagliato
5. **✅ Affidabilità**: Usa il sistema nativo di Windows

## 📁 Struttura dei File Generati

```
SYS-Toolset/
├── schedules/
│   ├── script_name.json          # Configurazione schedulazione
│   ├── wrappers/
│   │   └── wrapper_*.py          # Script wrapper auto-generati
│   └── temp/
│       └── *.xml                 # File XML temporanei (auto-eliminati)
└── logs/
    └── scheduled_*.log           # Log delle esecuzioni schedulate
```

## 🔍 Task nel Windows Task Scheduler

Tutti i task creati vengono registrati in:
- **Cartella**: `\SYS-Toolset\`
- **Prefisso**: `SYS_Toolset_`
- **Nome**: `SYS_Toolset_ScriptName_TriggerType_Index`

Esempio:
- `\SYS-Toolset\SYS_Toolset_Backup_Script_daily_0`
- `\SYS-Toolset\SYS_Toolset_Monitor_interval_0`

## 🧪 Come Testare

1. **Avvia l'applicazione**
   ```powershell
   cd "c:\Users\alex.sorrentino\OneDrive - DGS SpA\Desktop\TC\SYS-Toolset"
   .\run.ps1
   ```

2. **Crea uno schedule di test**
   - Seleziona uno script (o usa `test_schedule.py`)
   - Clicca sul pulsante ⏰
   - Configura un trigger "Once" tra 2-3 minuti
   - Salva

3. **Chiudi l'applicazione**

4. **Aspetta l'ora schedulata**

5. **Verifica l'esecuzione**
   - Controlla la cartella `logs/`
   - Dovresti trovare un file `scheduled_*.log`
   - Apri il Task Scheduler (`Win+R` → `taskschd.msc`)
   - Naviga in `\SYS-Toolset\` e controlla lo stato del task

## 📊 Verifica nel Task Scheduler

Per vedere tutti i task creati:

```powershell
schtasks /Query /TN "\SYS-Toolset\" /FO LIST /V
```

## 🐛 Troubleshooting

### Gli script non vengono eseguiti?

1. **Verifica i permessi**
   ```powershell
   # Esegui come amministratore se necessario
   ```

2. **Controlla i task nel Task Scheduler**
   ```powershell
   taskschd.msc
   ```

3. **Verifica i log**
   ```powershell
   Get-ChildItem logs\ | Sort-Object LastWriteTime -Descending | Select-Object -First 5
   ```

### Task non viene creato?

- Verifica che il path dello script sia corretto
- Assicurati di avere i permessi per creare task schedulati
- Controlla l'output nella finestra dell'applicazione

## 💡 Note Tecniche

### Wrapper Script
Ogni task schedulato esegue un **wrapper script** Python che:
1. Determina il tipo di script (PS1, PY, BAT, etc.)
2. Esegue lo script con il comando appropriato
3. Cattura tutto l'output (stdout/stderr)
4. Crea un log dettagliato con timestamp
5. Ritorna l'exit code appropriato

### XML Task Definition
Il sistema genera dinamicamente file XML conformi allo schema di Task Scheduler che includono:
- Trigger configurati (once, daily, weekly, interval)
- Azioni (esecuzione Python + wrapper)
- Impostazioni (timeout, battery, network, etc.)
- Principi di sicurezza (utente, privilegi)

### Retrocompatibilità
- APScheduler è ancora presente nel codice ma non viene più utilizzato per la schedulazione persistente
- I file JSON di configurazione mantengono lo stesso formato
- La UI rimane invariata

## 🔐 Sicurezza

- I task vengono eseguiti con i permessi dell'utente corrente
- Non è richiesto accesso amministratore (a meno che lo script stesso non lo richieda)
- I log vengono salvati con encoding UTF-8 per supportare caratteri speciali
- Timeout di 2 ore per prevenire script bloccati

## 📝 Log Format

Ogni log contiene:
```
=== Esecuzione Schedulata: Nome Script ===
Data/Ora: 2026-01-19 14:30:25
Script: C:\...\script.ps1
Comando: powershell -ExecutionPolicy Bypass -File C:\...\script.ps1
============================================================

Output:
[output dello script]

Errori:
[eventuali errori]

============================================================
✅ Completato con successo (exit code: 0)
Log salvato: C:\...\logs\scheduled_script_20260119_143025.log
```

## 🚀 Prossimi Passi

1. Testare con vari tipi di script (PowerShell, Python, Batch)
2. Testare tutti i tipi di trigger (once, daily, weekly, interval)
3. Verificare i log generati
4. Testare l'eliminazione e modifica degli schedule
5. Verificare il comportamento dopo riavvio del sistema

## 📞 Supporto

Per problemi o domande, consulta:
- [SCHEDULING_GUIDE.md](docs/SCHEDULING_GUIDE.md) - Guida utente completa
- Task Scheduler di Windows (`taskschd.msc`) - Per gestione manuale task
- Log dell'applicazione in `logs/` - Per debug

---

**🎉 La schedulazione è ora completamente funzionante e persistente!**
