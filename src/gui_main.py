"""
============================================================
File: gui_main.py
Author: Internal Systems Automation Team
Created: 2026-01-12

Description:
Entry point per l'applicazione grafica PyQt6.
Sostituisce il menu CLI tradizionale.
============================================================
"""

import sys
from PyQt6.QtWidgets import QApplication
from menu.tool_menu import ToolMenu
from db.script_repository import ScriptRepository
from gui.main_window import MainWindow

def main():
    repo = ScriptRepository(base_path="scripts")
    
    app = QApplication(sys.argv)
    window = MainWindow(repo)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
