# Indexer - ReindexData

## Descrizione
Rindicizza completamente tutti i dati nel sistema Indexer. Questo process ricrea tutti gli indici da zero, eliminando frammenti obsoleti e ottimizzando le prestazioni di ricerca.

## Funzionalità
- **Reindex completo**: Ricrea tutti gli indici
- **Ottimizzazione**: Defragmenta gli indici durante il processo
- **Backup automatico**: Crea backup degli indici precedenti prima di procedere
- **Validazione**: Verifica l'integrità degli indici dopo il completamento
- **Rollback**: Consente il rollback in caso di errori

## Parametri disponibili
- `-Full`: Esegue una reindicizzazione completa (consigliato)
- `-Partial`: Reindicizza solo i documenti modificati (più veloce)
- `-Verify`: Verifica l'integrità degli indici dopo il completamento
- `-BackupPath`: Specifica il percorso personalizzato per il backup

## Quando usarlo
- Performance di ricerca degradate
- Dopo importazione massiccia di nuovi documenti
- Come operazione di manutenzione programmata (settimanale/mensile)
- Dopo crash del sistema o interruzioni di corrente
- Quando il database degli indici risulta corrotto

## Tempo di esecuzione
Varia in base alla dimensione del dataset:
- Dataset piccolo (< 100.000 documenti): 5-15 minuti
- Dataset medio (100.000 - 1.000.000): 30-90 minuti
- Dataset grande (> 1.000.000): 2-6 ore

## Impatto sul sistema
- **Alto utilizzo CPU**: Durante il processo di indicizzazione
- **Alto I/O disco**: Lettura dei documenti e scrittura degli indici
- **Memoria**: Incremento significativo durante l'esecuzione
- **Utenti**: È consigliabile eseguire durante gli off-hours

## Output atteso
```
[INFO] Avvio reindicizzazione...
[INFO] Backup indici precedenti completato
[INFO] Reindicizzazione documenti: XX.XXX
[INFO] Ottimizzazione indici in corso...
[INFO] Validazione indici: OK
[DONE] Reindicizzazione completata con successo
```

## Monitoraggio
È possibile monitorare il progresso:
- CPU usage: Deve essere > 70% durante il process
- Disco I/O: Verificare attività di lettura/scrittura
- Log file: Disponibile in `logs/indexer_reindex.log`

## Troubleshooting
### Errore "Insufficient disk space"
- Liberare almeno il 20% dello spazio disco disponibile
- Spostare i file di log su un'altra partizione

### Indici corrotti dopo il reindex
- Ripristinare dal backup automatico
- Riexeguire il processo con parametro `-Verify`

### Processo interrotto
- Non riavviare il processo fino a 5 minuti dopo
- Controllare i log per identificare la causa
- Eseguire il ripristino dal backup

## Piani di manutenzione consigliati
- **Giornaliero**: Nessun reindex richiesto (indicizzazione incrementale)
- **Settimanale**: Reindex parziale per optimize
- **Mensile**: Reindex completo per manutenzione profonda

## Contatti
Per assistenza durante il reindex, contattare il team Database Administration.
