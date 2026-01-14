# Dispatcher - RestartDispatcher

## Descrizione
Riavvia il servizio Dispatcher del sistema. Questo tool è essenziale per ripristinare il corretto funzionamento del dispatcher quando presenta malfunzionamenti o per applicare aggiornamenti di configurazione.

## Funzionalità
- **Avvio graceful**: Arresta il servizio in modo controllato
- **Verifica stato**: Controlla che il servizio sia completamente fermato prima di riavviarlo
- **Logging**: Registra tutte le operazioni per tracciamento
- **Validazione**: Verifica il corretto avvio del servizio dopo il riavvio

## Parametri disponibili
- `-Force`: Forza il riavvio senza conferma
- `-Verbose`: Mostra output dettagliato durante l'esecuzione

## Quando usarlo
- Il dispatcher non risponde alle richieste
- Dopo modifiche alla configurazione del dispatcher
- Per applicare patch o aggiornamenti
- Quando il sistema operativo consiglia un riavvio dei servizi

## Tempo di esecuzione
Circa 30-60 secondi, a seconda del carico del sistema.

## Output atteso
- Messaggio di conferma del completamento
- Stato finale del servizio (Running/Stopped)
- Qualsiasi errore o avviso riscontrato durante l'esecuzione

## Troubleshooting
### Il servizio non si avvia
- Verificare i permessi di amministrazione
- Controllare i log del dispatcher per errori di configurazione
- Assicurarsi che la porta non sia in uso da altro processo

### Timeout durante il riavvio
- Aumentare il timeout di attesa
- Controllare le risorse di sistema (CPU, memoria)
- Verificare la connettività di rete

## Contatti
Per problemi persistenti, contattare il team di System Administration.
