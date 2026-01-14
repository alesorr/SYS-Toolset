# Script Collection

Questa directory contiene l'intera raccolta di script operativi
utilizzati dal Team IT System Operations.

Ogni sottocartella rappresenta una categoria funzionale (esempio:
Dispatcher, Indexer, Other) e contiene una combinazione di script
PowerShell, Batch, Bash o Python utilizzati per automatizzare
attività ripetitive e processi operativi.

## Struttura
- Ogni categoria ha una propria cartella.
- Ogni script deve avere un README dedicato.
- Il file `index.json` definisce quali script vengono mostrati nel toolset.

## Linee guida
- Gli script devono essere idempotenti quando possibile.
- Evitare hardcoded values.
- Usare naming consistente.
- Fornire sempre descrizione, parametri e note operative nel README.