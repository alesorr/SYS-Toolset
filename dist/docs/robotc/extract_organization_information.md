# RoboTC - Extract Organization Information

## Descrizione
Estrae le informazioni utente dall'organizzazione nel sistema RoboTC. Questo tool sincronizza i dati utente dalla sorgente centralizzata (Active Directory, LDAP, ecc.) nel database locale.

## Funzionalità
- **Sincronizzazione utenti**: Estrae profili completi da directory centralizzata
- **Sincronizzazione gruppi**: Importa appartenenze ai gruppi e ruoli
- **Deduplicazione**: Rimuove i duplicati e riconcilia i dati
- **Audit trail**: Registra tutte le modifiche per conformità
- **Validazione**: Verifica l'integrità dei dati estratti
- **Report**: Genera rapporti dettagliati delle modifiche

## Funzionamento
1. **Connessione**: Si connette alla sorgente dati (AD/LDAP)
2. **Query**: Recupera tutti gli utenti e i loro attributi
3. **Trasformazione**: Trasforma i dati nel formato locale
4. **Caricamento**: Importa i dati nel database
5. **Riconciliazione**: Aggiorna i dati esistenti, elimina i disattivati
6. **Report**: Genera rapporto dettagliato delle operazioni

## Parametri disponibili
- `-Full`: Esegue un'estrazione completa (impostazione predefinita)
- `-Partial`: Sincronizza solo le modifiche recenti
- `-DryRun`: Simula l'estrazione senza apportare modifiche
- `-OutputPath`: Specifica il percorso per i report

## Quando usarlo
- Regolarmente (settimanale/mensile) per mantenere sincronizzazione
- Dopo modifiche significative all'organizzazione (nuovi utenti, dipartimenti)
- Quando gli utenti segnalano privilegi non aggiornati
- Dopo problemi di sincronizzazione precedenti
- Come parte della procedura di onboarding/offboarding

## Tempo di esecuzione
Varia in base alle dimensioni dell'organizzazione:
- Organizzazione piccola (< 500 utenti): 5-10 minuti
- Organizzazione media (500 - 5.000 utenti): 15-30 minuti
- Organizzazione grande (> 5.000 utenti): 30-60 minuti

## Output atteso
```
[INFO] Connessione alla sorgente dati...
[INFO] Utenti trovati: X.XXX
[INFO] Gruppi trovati: XXX
[INFO] Sincronizzazione in corso...
[INFO] Utenti nuovi: XX
[INFO] Utenti aggiornati: XXX
[INFO] Utenti disattivati: X
[INFO] Errori riscontrati: 0
[DONE] Estrazione completata con successo
Report salvato in: reports/extraction_2026-01-12.txt
```

## Dati estratti
- Nome utente (username)
- Nome completo
- Email
- Numero di telefono
- Dipartimento
- Responsabile
- Attributi personalizzati
- Data inizio/fine occupazione
- Stato (Attivo/Inattivo)

## Sincronizzazione vs Estrazione
### Estrazione Completa (-Full)
- Sincronizza TUTTI gli utenti
- Richiede più tempo
- Consigliato per:
  - Problemi di sincronizzazione
  - Manutenzione programmata
  - Primo avvio

### Estrazione Parziale (-Partial)
- Sincronizza solo modifiche recenti
- Più veloce
- Consigliato per:
  - Sincronizzazione giornaliera
  - Cambio attributi singoli utenti
  - Allineamento rapido

## Troubleshooting
### Errore di connessione
- Verificare credenziali di accesso
- Controllare connettività di rete verso directory centralizzata
- Verificare firewall e proxy settings

### Utenti non sincronizzati
- Verificare che l'utente esista nella sorgente dati
- Controllare i filtri LDAP
- Verificare i permessi di lettura

### Performance lenta
- Ridurre il numero di attributi sincronizzati
- Aumentare il timeout di connessione
- Eseguire durante orari off-peak

### Conflitti di dati
- Usare DryRun per anteprima modifiche
- Verificare le regole di riconciliazione
- Contattare l'admin per risoluzione manuale

## Conformità e Audit
- Tutti gli accessi sono registrati
- Le modifiche sono tracciate nel log
- Report disponibili per audit
- Retention policy: 90 giorni

## Pianificazione consigliata
- **Giornaliero**: Estrazione parziale (off-hours)
- **Settimanale**: Estrazione completa (fine settimana)
- **Mensile**: Revisione manuale e riconciliazione

## Contatti
Per problemi di sincronizzazione, contattare il team Directory Services.
