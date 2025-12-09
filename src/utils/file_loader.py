"""
============================================================
 File: file_loader.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2025-01-10

 Description:
     Funzioni di utilità dedicate alla gestione di file.
     Fornisce un metodo semplice per leggere file di testo
     in modo sicuro e centralizzato.
============================================================
"""

from pathlib import Path


def load_file(path):
    p = Path(path)
    if p.exists():
        return p.read_text()
    return None