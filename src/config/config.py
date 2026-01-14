"""
============================================================
File: config.py
Author: Internal Systems Automation Team
Created: 2026-01-12

Description:
Gestione della configurazione centralizzata dell'applicazione.
Legge da config.ini e fornisce accesso ai settings in tutta l'app.
============================================================
"""

import configparser
from pathlib import Path
import os
import sys
from utils.logger import logger


class ConfigManager:
    """Gestore centralizzato della configurazione dell'applicazione"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Inizializza il configuration manager"""
        logger.debug("Inizializzazione ConfigManager...")
        self._config = configparser.ConfigParser()
        self._config_path = self._find_config_file()
        
        if self._config_path and self._config_path.exists():
            logger.info(f"Config trovato: {self._config_path}")
            self._config.read(self._config_path, encoding='utf-8')
        else:
            logger.warning("Config.ini non trovato, usando defaults")
            self._load_defaults()
    
    def _find_config_file(self):
        """Cerca il file config.ini in varie locazioni"""
        
        # 1. Prova nella cartella dell'eseguibile (per exe)
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            config_file = exe_dir / 'config.ini'
            if config_file.exists():
                return config_file
        
        # 2. Prova nella cartella config/
        config_file = Path('config') / 'config.ini'
        if config_file.exists():
            return config_file
        
        # 3. Prova nella root del progetto
        config_file = Path('config.ini')
        if config_file.exists():
            return config_file
        
        # 4. Prova nella cartella src
        config_file = Path('src') / 'config' / 'config.ini'
        if config_file.exists():
            return config_file
        
        return None
    
    def _load_defaults(self):
        """Carica configurazione di default"""
        self._config['PATHS'] = {
            'scripts_directory': 'scripts',
            'docs_directory': 'docs',
            'logs_directory': 'logs',
        }
        self._config['APP'] = {
            'title': 'System Toolset - GUI Interface',
            'version': '1.0.0',
            'window_width': '1200',
            'window_height': '700',
            'debug': 'false',
        }
        self._config['UI'] = {
            'theme': 'light',
            'font_family': 'Arial',
            'font_size': '10',
        }
    
    def get(self, section, key, fallback=None):
        """Ottiene un valore dalla configurazione"""
        try:
            return self._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_int(self, section, key, fallback=None):
        """Ottiene un valore intero dalla configurazione"""
        try:
            return self._config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_bool(self, section, key, fallback=False):
        """Ottiene un valore booleano dalla configurazione"""
        try:
            return self._config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_path(self, section, key, relative_to=None):
        """Ottiene un percorso, opzionalmente relativo a una cartella"""
        path_str = self.get(section, key)
        if not path_str:
            logger.debug(f"get_path: '{section}.{key}' non trovato in config")
            return None
        
        path = Path(path_str)
        
        # Se il percorso è assoluto, restituiscilo così
        if path.is_absolute():
            logger.debug(f"get_path: '{key}' è assoluto: {path}")
            return path
        
        # Se è relativo e siamo in un exe, fallo relativo alla cartella dell'exe
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent.resolve()
            absolute_path = (exe_dir / path).resolve()
            logger.debug(f"get_path: EXE mode - exe_dir={exe_dir}, relative='{path}', absolute={absolute_path}")
            return absolute_path
        else:
            # Se siamo in Python, usa il path come è (relativo)
            logger.debug(f"get_path: PYTHON mode - relative='{path}'")
            return path.resolve()
    
    @property
    def scripts_dir(self):
        """Directory degli script"""
        path = self.get_path('PATHS', 'scripts_directory')
        if path is None:
            # Fallback: usa 'scripts' relativo alla cartella dell'exe
            if getattr(sys, 'frozen', False):
                path = Path(sys.executable).parent / 'scripts'
                logger.debug(f"[EXE] Scripts dir (fallback): {path}")
            else:
                path = Path('scripts')
                logger.debug(f"[PYTHON] Scripts dir: {path}")
        else:
            logger.debug(f"Scripts dir (from config): {path}")
        
        logger.debug(f"Scripts dir final: {path} (exists: {path.exists()})")
        return path
    
    @property
    def docs_dir(self):
        """Directory della documentazione"""
        path = self.get_path('PATHS', 'docs_directory')
        if path is None:
            if getattr(sys, 'frozen', False):
                path = Path(sys.executable).parent / 'docs'
            else:
                path = Path('docs')
        return path
    
    @property
    def logs_dir(self):
        """Directory dei log"""
        path = self.get_path('PATHS', 'logs_directory')
        if path is None:
            if getattr(sys, 'frozen', False):
                path = Path(sys.executable).parent / 'logs'
            else:
                path = Path('logs')
        return path
    
    @property
    def app_title(self):
        """Titolo dell'applicazione"""
        return self.get('APP', 'title', 'System Toolset - GUI Interface')
    
    @property
    def app_version(self):
        """Versione dell'applicazione"""
        return self.get('APP', 'version', '1.0.0')
    
    @property
    def window_size(self):
        """Dimensione della finestra (width, height)"""
        width = self.get_int('APP', 'window_width', 1200)
        height = self.get_int('APP', 'window_height', 700)
        return (width, height)
    
    @property
    def debug(self):
        """Modalità debug attiva"""
        return self.get_bool('APP', 'debug', False)
    
    @property
    def config_file(self):
        """Percorso del file di configurazione"""
        return self._config_path
    
    def print_info(self):
        """Stampa informazioni di configurazione (debug)"""
        print(f"[CONFIG] Config file: {self._config_path}")
        print(f"[CONFIG] Scripts directory: {self.scripts_dir}")
        print(f"[CONFIG] Docs directory: {self.docs_dir}")
        print(f"[CONFIG] Logs directory: {self.logs_dir}")
        if self.debug:
            print("[CONFIG] Debug mode: ENABLED")
