"""
============================================================
File: app.py (Entry point alternativo per EXE)
Author: Internal Systems Automation Team
Created: 2026-01-12

Description:
Entry point alternativo che funziona bene sia da Python
che quando compilato in EXE con PyInstaller.
Gestisce automaticamente i percorsi.
============================================================
"""

import sys
import os
from pathlib import Path

# Aggiungi la cartella src al path se eseguito da Python
if not getattr(sys, 'frozen', False):
    src_path = Path(__file__).parent / 'src'
    if src_path.exists():
        sys.path.insert(0, str(src_path))

# Imposta la working directory corretta
if getattr(sys, 'frozen', False):
    # Se eseguito come exe, usa la cartella dell'exe
    os.chdir(Path(sys.executable).parent)
    print(f"[APP] Running as EXE, working dir: {os.getcwd()}")
else:
    # Se eseguito come script, usa la cartella del progetto
    os.chdir(Path(__file__).parent)
    print(f"[APP] Running as Python script, working dir: {os.getcwd()}")

# Adesso importa il logger
from utils.logger import logger

logger.info("="*60)
logger.info("Startup della applicazione")
logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
logger.info(f"Working dir: {os.getcwd()}")
logger.info(f"Python: {sys.version}")
logger.info("="*60)

# Ora importa l'app
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from config.config import ConfigManager
from db.script_repository import ScriptRepository
from gui.main_window import MainWindow
from gui.splash_screen import SplashScreen


def main():
    # Crea l'applicazione
    app = QApplication(sys.argv)
    
    # Mostra la splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    # Fase 1: Caricamento configurazione
    splash.show_message("Caricamento configurazione...", 10)
    config = ConfigManager()
    if config.debug:
        config.print_info()
    
    # Fase 2: Inizializzazione repository
    splash.show_message("Scansione moduli e script...", 30)
    app.processEvents()
    repo = ScriptRepository(base_path=str(config.scripts_dir))
    
    # Verifica che gli script siano stati caricati (solo warning, non bloccare)
    if not repo.get_categories():
        logger.warning("Nessuna categoria di script trovata in fase di startup")
        logger.warning(f"Cerco in: {config.scripts_dir}")
        # Non usciamo, permettiamo all'app di avviarsi comunque
    
    # Fase 3: Inizializzazione interfaccia grafica
    splash.show_message("Inizializzazione interfaccia grafica...", 60)
    app.processEvents()
    window = MainWindow(repo)
    
    # Fase 4: Caricamento componenti
    splash.show_message("Caricamento componenti...", 80)
    app.processEvents()
    
    # Fase 5: Finalizzazione
    splash.show_message("Avvio completato!", 100)
    app.processEvents()
    
    # Chiudi la splash dopo un breve delay
    def show_window():
        window.show()
        splash.finish(window)
    
    QTimer.singleShot(500, show_window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"ERRORE CRITICO durante l'avvio: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
