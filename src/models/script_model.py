"""
============================================================
 File: script_model.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2025-01-10

 Description:
     Modello dati che rappresenta uno script gestito dal
     toolset. Incapsula nome, descrizione, categoria,
     percorso fisico e parametri accettati.
============================================================
"""

class Script:
    def __init__(self, name, description, category, path, params=None):
        self.name = name
        self.description = description
        self.category = category
        self.path = path
        self.params = params or []