"""
============================================================
File: main.py
Author: Internal Systems Automation Team
Created: 2025-01-10
Last Updated: 2025-01-10

Description:
Entry point principale del Toolset CLI. Inizializza il
repository degli script, costruisce il menu interattivo
e avvia l'interfaccia utente basata su curses.

Questo file rappresenta il punto di ingresso ufficiale
dell'applicazione ed è responsabile dell'orchestrazione
iniziale dell'intero flusso.
============================================================
"""

from menu.tool_menu import ToolMenu
from db.script_repository import ScriptRepository

def main():
    repo = ScriptRepository()
    menu = ToolMenu(repo)
    menu.start()

if __name__ == "__main__":
    main()