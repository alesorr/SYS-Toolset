# Schedulazione Script - Guida Utente

## 📅 Come Funziona la Schedulazione

La schedulazione degli script in SYS-Toolset utilizza il **Windows Task Scheduler** per garantire l'esecuzione automatica degli script, **anche quando l'applicazione è chiusa**.

## ✅ Caratteristiche Principali

### Esecuzione Persistente
- ✅ Gli script vengono eseguiti **anche se l'applicazione è spenta**
- ✅ Gli script vengono eseguiti **in background**
- ✅ Viene creato automaticamente un **log dettagliato** per ogni esecuzione
- ✅ Supporto per **molteplici tipi di schedulazione**

### Tipi di Schedulazione Supportati

1. **Once (Una Tantum)**
   - Esegue lo script una sola volta alla data/ora specificata
   
2. **Daily (Giornaliero)**
   - Esegue lo script ogni giorno alla stessa ora
   
3. **Weekly (Settimanale)**
   - Esegue lo script in giorni specifici della settimana alla stessa ora
   
4. **Interval (A Intervalli)**
   - Esegue lo script a intervalli regolari (minuti, ore, giorni)

## 📝 Come Schedulare uno Script

1. **Seleziona lo script** dalla lista
2. Clicca sul pulsante **⏰** (Schedule)
3. Configura la schedulazione:
   - Abilita lo scheduling con il checkbox
   - Scegli il tipo di trigger
   - Imposta data/ora o giorni
   - Puoi aggiungere più trigger per lo stesso script
4. Clicca su **Salva**

## 📄 Log delle Esecuzioni

Ogni volta che uno script schedulato viene eseguito, viene creato automaticamente un file di log nella cartella `logs/`:

```
logs/
  scheduled_NomeScript_20260119_143025.log
  scheduled_NomeScript_20260119_143526.log
  ...
```

Il log contiene:
- Data e ora di esecuzione
- Comando eseguito
- Output dello script
- Eventuali errori
- Exit code

## 🔧 Gestione dei Task

### Visualizzare i Task Attivi
Puoi visualizzare tutti i task schedulati aprendo il **Task Scheduler di Windows**:
1. Premi `Win + R`
2. Digita `taskschd.msc`
3. Naviga in `Libreria Utilità di pianificazione` → `SYS-Toolset`

### Disabilitare uno Schedule
1. Apri di nuovo la configurazione dello schedule (pulsante ⏰)
2. Deseleziona "Abilita scheduling"
3. Clicca "Salva"

### Eliminare Completamente uno Schedule
1. Apri la configurazione dello schedule
2. Clicca sul pulsante "🗑️ Elimina tutti gli schedule"
3. Conferma

## ⚠️ Note Importanti

1. **Windows Task Scheduler**: La funzionalità richiede Windows e i permessi per creare task schedulati
2. **Path Assoluti**: Gli script vengono eseguiti con path assoluti, quindi funzionano indipendentemente dalla directory corrente
3. **Timeout**: Per sicurezza, ogni esecuzione ha un timeout di 2 ore (modificabile nel Task Scheduler)
4. **Permessi**: Gli script vengono eseguiti con i permessi dell'utente corrente

## 🐛 Troubleshooting

### Lo script non viene eseguito?
1. Verifica che il task esista nel Task Scheduler (`taskschd.msc`)
2. Controlla i log nella cartella `logs/`
3. Verifica che il path dello script sia corretto
4. Assicurati che l'utente abbia i permessi necessari

### I log non vengono creati?
1. Verifica che la cartella `logs/` esista e sia scrivibile
2. Controlla i permessi della cartella

### Il task non si avvia alla data/ora prevista?
1. Verifica che il computer sia acceso
2. Controlla le impostazioni del task nel Task Scheduler
3. Verifica che "Avvia l'attività appena possibile dopo un avvio non effettuato" sia abilitato

## 💡 Esempi di Utilizzo

### Esempio 1: Backup Giornaliero
- Script: `backup_script.ps1`
- Tipo: Daily
- Ora: 02:00 AM
- Risultato: Backup automatico ogni notte alle 2

### Esempio 2: Report Settimanale
- Script: `generate_report.py`
- Tipo: Weekly
- Giorni: Lunedì
- Ora: 09:00 AM
- Risultato: Report generato ogni lunedì mattina

### Esempio 3: Monitoraggio Continuo
- Script: `monitor.ps1`
- Tipo: Interval
- Intervallo: 30 minuti
- Risultato: Controllo ogni mezz'ora

## 🔄 Differenza tra APScheduler e Task Scheduler

| Caratteristica | APScheduler (In-Process) | Windows Task Scheduler |
|---|---|---|
| Esecuzione con app chiusa | ❌ No | ✅ Sì |
| Persistenza tra restart | ❌ No | ✅ Sì |
| Log automatici | ✅ Sì | ✅ Sì |
| Gestione dalla GUI | ✅ Sì | ✅ Sì |
| **USATO ATTUALMENTE** | ❌ No | ✅ **Sì** |

**Nota**: L'applicazione utilizza ora esclusivamente il Windows Task Scheduler per garantire l'esecuzione persistente degli script.
