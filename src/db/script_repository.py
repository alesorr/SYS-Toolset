"""
============================================================
 File: script_repository.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2025-01-10

 Description:
     Questo modulo gestisce il caricamento degli script
     disponibili tramite file index.json. Fornisce accesso
     strutturato a categorie e script, astrando completamente
     da filesystem e struttura fisica delle cartelle.
============================================================
"""

import json
from pathlib import Path


class ScriptRepository:
    def __init__(self, base_path="scripts"):
        self.base_path = Path(base_path)
        self.index = self._load_index()

    def _load_index(self):
        index_file = self.base_path / "index.json"
        if index_file.exists():
            return json.loads(index_file.read_text())
        return {}

    def get_categories(self):
        return list(self.index.keys())

    def get_scripts_by_category(self, category):
        return self.index.get(category, [])