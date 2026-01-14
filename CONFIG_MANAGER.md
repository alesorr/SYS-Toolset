# ConfigManager - Sistema di Configurazione Centralizzato

## 🎯 Cos'è

`ConfigManager` è una classe **singleton** che gestisce centralizzato la configurazione dell'app.

Legge da `config.ini` e fornisce un'interfaccia semplice per accedere alle impostazioni.

## 📍 Ricerca del config.ini

L'app cerca automaticamente il file in questo ordine:

1. **Cartella dell'exe** (se compilato) ← Primaria per distribuzione
2. `config/` nella cartella dell'exe
3. Root del progetto (cartella padre di src)
4. `src/config/`

Questo significa che **funziona ovunque** si trovi l'app.

## 🔧 Come usarlo

### Importazione
```python
from config.config import ConfigManager

# Singleton - una sola istanza in tutta l'app
config = ConfigManager()
```

### Accesso semplice a path
```python
config.scripts_dir    # Path object a cartella script
config.docs_dir       # Path object a cartella docs
config.logs_dir       # Path object a cartella logs
```

### Accesso a settings
```python
config.app_title      # string
config.app_version    # string
config.window_size    # tuple (width, height)
config.debug          # bool
```

### Accesso generico
```python
# Get string
value = config.get('SECTION', 'key')
value = config.get('SECTION', 'key', fallback='default')

# Get int
value = config.get_int('SECTION', 'key', fallback=10)

# Get bool
value = config.get_bool('SECTION', 'key', fallback=False)

# Get path
path = config.get_path('SECTION', 'key')  # Path object
```

## 📄 Struttura config.ini

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

[LOGGING]
level = INFO
format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## 💡 Percorsi Relativi vs Assoluti

### Percorsi Relativi (Consigliati)
```ini
scripts_directory = scripts
```

Automaticamente relativi a:
- **Python**: Cartella root del progetto
- **EXE**: Cartella dell'exe

### Percorsi Assoluti
```ini
scripts_directory = C:\Data\Scripts
```

Usati così come scritti.

### Avanzato: Percorsi con .
```ini
docs_directory = ../shared_docs
```

Supporta anche `..` per andare su di livello.

## 🛠️ Aggiungere Nuove Configurazioni

### Step 1: Modifica config.ini
```ini
[MY_SECTION]
my_setting = my_value
my_number = 42
my_flag = true
```

### Step 2: Accedi dalla code
```python
config = ConfigManager()

# String
setting = config.get('MY_SECTION', 'my_setting')

# Int
number = config.get_int('MY_SECTION', 'my_number')

# Bool
flag = config.get_bool('MY_SECTION', 'my_flag')
```

### Step 3 (Opzionale): Aggiungi property
```python
# In config.py
@property
def my_setting(self):
    return self.get('MY_SECTION', 'my_setting', 'default_value')
```

Poi accedi con:
```python
config = ConfigManager()
value = config.my_setting
```

## 📝 Localizzazione del File

### Per Esecuzione Python
```
C:\dev\SYS-Toolset\
├── config/
│   └── config.ini        ← Qui cerca il file
├── src/
│   ├── app.py
│   └── ...
└── ...
```

Avvia con:
```powershell
cd C:\dev\SYS-Toolset
python src/app.py
```

### Per EXE Compilato
```
C:\Program Files\SystemToolset\
├── SystemToolset.exe
├── config/
│   └── config.ini        ← Qui cerca il file
├── scripts/
└── docs/
```

Avvia con:
```powershell
C:\Program Files\SystemToolset\SystemToolset.exe
```

## 🔍 Debug: Visualizzare Config Caricato

```python
from config.config import ConfigManager

config = ConfigManager()

# Stampa informazioni di debug
if config.debug:
    config.print_info()
    # Output:
    # [CONFIG] Config file: C:\dev\SYS-Toolset\config\config.ini
    # [CONFIG] Scripts directory: C:\dev\SYS-Toolset\scripts
    # [CONFIG] Docs directory: C:\dev\SYS-Toolset\docs
    # [CONFIG] Logs directory: C:\dev\SYS-Toolset\logs
    # [CONFIG] Debug mode: ENABLED
```

## ⚙️ Integrazione nella GUI

### main_window.py
```python
from config.config import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self, repository):
        super().__init__()
        self.config = ConfigManager()
        
        # Usa la config per titolo e dimensioni
        self.setWindowTitle(self.config.app_title)
        width, height = self.config.window_size
        self.setGeometry(100, 100, width, height)
        
        # Usa la config per i percorsi
        script_path = os.path.join(str(self.config.scripts_dir), 
                                   script['path'])
```

## 🚀 Vantaggi del ConfigManager

✅ **Centralizzato**: Un'unica fonte di verità  
✅ **Flessibile**: Modificabile senza riconiare  
✅ **Percorsi intelligenti**: Relativi e assoluti supportati  
✅ **Singleton**: Istanza unica in tutta l'app  
✅ **Fallback**: Default values se config non trovato  
✅ **Type-safe**: Conversione automatica int/bool  
✅ **Distribuibile**: Funziona Python + EXE  

## 📋 Scenario di Utilizzo

### Sviluppo locale
```
C:\dev\SYS-Toolset\config\config.ini
(scripts relativi a C:\dev\SYS-Toolset\)
```

### Produzione USB
```
D:\SystemToolset\config\config.ini
(scripts relativi a D:\SystemToolset\)
```

### Produzione Network
```
\\server\apps\SystemToolset\config\config.ini
(scripts relativi a \\server\apps\SystemToolset\)
```

Stesso config.ini, stessa app - **funziona ovunque!**

## 🎓 Esempio Completo

```python
from config.config import ConfigManager
from pathlib import Path

# Carica la configurazione
config = ConfigManager()

# Stampa info debug
if config.debug:
    config.print_info()

# Accedi ai path
scripts = config.scripts_dir
docs = config.docs_dir
logs = config.logs_dir

# Crea directories se non esistono
scripts.mkdir(parents=True, exist_ok=True)
docs.mkdir(parents=True, exist_ok=True)
logs.mkdir(parents=True, exist_ok=True)

# Accedi alle impostazioni app
print(f"App: {config.app_title} v{config.app_version}")
print(f"Window: {config.window_size}")
print(f"Debug mode: {config.debug}")

# Accedi a custom settings
my_value = config.get('MY_SECTION', 'my_key', fallback='default')
print(f"My setting: {my_value}")
```

## ⚠️ Gotcha Comuni

### Percorso non trovato
```python
# ❌ SBAGLIATO
path = config.scripts_dir
os.chdir(path)  # Potrebbe non funzionare se string

# ✅ CORRETTO
path = config.scripts_dir
os.chdir(str(path))  # Converti Path a string
```

### Config.ini non trovato
```python
# ❌ SBAGLIATO
# Avvio da C:\dev\app\src\gui.py
# app cerca config in C:\dev\app\src\config.ini ❌

# ✅ CORRETTO
# Avvio da C:\dev\app\src\app.py
# app cambia directory a C:\dev\app\
# app cerca config in C:\dev\app\config\config.ini ✅
```

Assicurati di avviare da `src/app.py` o `src/main.py` dalla root!

## 📞 Supporto

Per problemi con la configurazione:

1. Verifica che `config.ini` esista nel posto giusto
2. Controlla la sintassi (ini format)
3. Stampa debug: `config.print_info()`
4. Controlla logs se creati

---

**Data:** 2026-01-12  
**Versione:** 1.0.0
