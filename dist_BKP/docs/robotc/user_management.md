# RoboTC - User Management

## Descrizione
Aggiorna, crea e rimuove le proprietà degli utenti nel sistema RoboTC. Questo tool fornisce un'interfaccia centralizzata per la gestione completa del ciclo di vita degli utenti.

## Funzionalità
- **Creazione utenti**: Crea nuovi profili utente con attributi personalizzati
- **Modifica proprietà**: Aggiorna qualsiasi attributo utente
- **Assegnazione ruoli**: Gestisce i ruoli e i permessi degli utenti
- **Bulk operations**: Operazioni di massa su più utenti
- **Deprovisioning**: Disattiva o elimina utenti
- **Audit**: Traccia tutte le modifiche e i responsabili
- **Template**: Crea utenti da template predefiniti

## Funzionamento
1. **Selezione operazione**: Scegli tra creazione, modifica o eliminazione
2. **Identificazione utente**: Specifica l'utente target (username, email, ID)
3. **Modifica dati**: Inserisci i nuovi dati o proprietà
4. **Validazione**: Sistema valida le modifiche
5. **Applicazione**: Le modifiche vengono applicate
6. **Conferma**: Messaggio di successo o errore

## Operazioni supportate

### Creazione Utente
```
Nome: [Input richiesto]
Cognome: [Input richiesto]
Email: [Input richiesto]
Username: [Auto-generato o manuale]
Dipartimento: [Selezione da lista]
Responsabile: [Selezione da lista]
Ruolo: [Selezione da lista]
Data inizio: [Input data]
```

### Modifica Proprietà
Proprietà modificabili:
- Email
- Numero telefonico
- Indirizzo
- Dipartimento
- Responsabile
- Titolo professionale
- Attributi personalizzati
- Data fine incarico

### Rimozione/Disattivazione
Opzioni:
- **Soft delete**: Disattiva l'utente (reversibile)
- **Hard delete**: Elimina completamente l'utente
- **Offboarding**: Completa il processo di uscita

## Parametri disponibili
- `-Full`: Operazione completa con validazioni estese
- `-DryRun`: Simula l'operazione senza applicare modifiche
- `-Force`: Ignora avvisi non critici (usare con cautela)
- `-BatchFile`: File CSV per operazioni di massa

## Quando usarlo
- Onboarding di nuovo personale
- Cambio dipartimento/ruolo di un dipendente
- Aggiornamento dati di contatto
- Rimozione utenti (offboarding)
- Modifica autorizzazioni e permessi
- Operazioni di massa (import bulk)

## Tempo di esecuzione
- Creazione singolo utente: < 1 minuto
- Modifica singolo utente: < 30 secondi
- Bulk operations (100 utenti): 5-10 minuti
- Disattivazione: < 30 secondi

## Output atteso
```
[INFO] Operazione: MODIFICA UTENTE
[INFO] Target: john.doe@company.com
[INFO] Proprietà modificate:
  - Email: john.doe@company.com
  - Dipartimento: IT
  - Ruolo: Senior Developer
[INFO] Validazione: OK
[DONE] Modifica applicata con successo
Change ID: CHG-2026-001234
Timestamp: 2026-01-12 14:30:45
```

## Validazioni applicate
- **Email**: Formato valido e unicità
- **Username**: Rispetta policy di naming
- **Ruoli**: Validazione autorizzazioni
- **Data**: Coerenza con timeline
- **Attributi personalizzati**: Formato e vincoli

## File batch per operazioni di massa
Formato CSV supportato:
```
Operation,Username,Email,Department,Role,FirstName,LastName
CREATE,jsmith,jsmith@company.com,IT,Developer,John,Smith
MODIFY,mdavis,mdavis@company.com,HR,Manager,Mary,Davis
DEACTIVATE,rbrown,,,,Robert,Brown
```

## Troubleshooting
### Errore di validazione email
- Verificare che l'email sia unica nel sistema
- Controllare il formato (deve contenere @)
- Verificare che il dominio sia valido

### Username già in uso
- Generare automaticamente aggiungendo suffisso
- Verificare utenti disattivati con lo stesso nome
- Contattare l'admin per conflitti persistenti

### Permesso negato
- Verificare i permessi dell'operatore
- Utenti admin possono modificare senza restrizioni
- Utenti standard hanno restrizioni su alcune proprietà

### Offboarding incompleto
- Verificare che tutti i sistemi siano stati sincronizzati
- Controllare i log per errori di propagazione
- Manualmente terminare le sessioni attive se necessario

## Best practices

### Onboarding
1. Creare utente con dati base
2. Assegnare ruolo e dipartimento
3. Configurare permessi specifici
4. Attivare accessi ai sistemi
5. Notificare il manager

### Offboarding
1. Disattivare accessi critico-temporali
2. Trasferire proprietà/deleghe
3. Escludere dalle liste di distribuzione
4. Disattivare l'utente nel sistema
5. Archivio documentazione

### Audit trail
- Tutte le operazioni sono registrate
- Incluse: User, Timestamp, Azione, Parametri
- Retention: 180 giorni
- Disponibili nei report di compliance

## Ruoli disponibili
- **Admin**: Accesso completo al sistema
- **Manager**: Gestione del proprio team
- **User**: Accesso base alle funzionalità
- **Guest**: Accesso limitato, specifico per progetto
- **Custom**: Ruoli personalizzati definibili

## Pianificazione consigliata
- **Giornaliero**: Check utenti nuovi/rimossi
- **Settimanale**: Revisione attributi
- **Mensile**: Audit permessi e ruoli
- **Trimestrale**: Pulizia account inattivi

## Contatti
Per supporto nella gestione utenti, contattare il team Identity & Access Management.
