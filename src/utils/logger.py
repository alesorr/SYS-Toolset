"""
============================================================
 File: logger.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2025-01-10

 Description:
     Logger minimale per output a console. Pensato per
     debugging interno e tracing delle esecuzioni.
============================================================
"""

from datetime import datetime
from pathlib import Path
from config import settings

# Assicura che la cartella logs esista
log_file_path = Path(settings.LOG_FILE_PATH)
log_file_path.parent.mkdir(parents=True, exist_ok=True)

def log(message):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {message}"
    
    # Stampa a console
    print(line)
    
    # Scrive su file
    with log_file_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")