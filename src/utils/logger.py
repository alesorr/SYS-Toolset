"""
============================================================
 File: logger.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2026-01-13

 Description:
     Sistema di logging professionale con support a console e file.
============================================================
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

class AppLogger:
    """Logger centralizzato per l'applicazione"""
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance
    
    def _setup_logger(self):
        """Configura il logger"""
        self._logger = logging.getLogger('SystemToolset')
        self._logger.setLevel(logging.DEBUG)
        
        # Evita duplicate handlers
        if self._logger.handlers:
            return
        
        # Formato del log
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # File handler
        try:
            # Usa dist/logs quando in esecuzione come EXE, altrimenti logs nella root del progetto
            if getattr(sys, 'frozen', False):
                # In modalità frozen (PyInstaller), sys.executable punta all'EXE in dist
                base_dir = Path(sys.executable).parent
                log_dir = base_dir / "logs"
            else:
                # In modalità Python, __file__ è disponibile: risali alla root del progetto
                log_dir = Path(__file__).parent.parent.parent / "logs"
            log_dir.mkdir(exist_ok=True, parents=True)
            
            log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
            
            self._logger.debug(f"Log file: {log_file}")
        except Exception as e:
            self._logger.warning(f"Impossibile creare file di log: {e}")
    
    def debug(self, msg):
        self._logger.debug(msg)
    
    def info(self, msg):
        self._logger.info(msg)
    
    def warning(self, msg):
        self._logger.warning(msg)
    
    def error(self, msg):
        self._logger.error(msg)
    
    def critical(self, msg):
        self._logger.critical(msg)

# Istanza globale
logger = AppLogger()
