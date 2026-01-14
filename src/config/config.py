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
            'title': 'SYS Toolset Management',
            'version': '1.0.0',
            'window_width': '1200',
            'window_height': '700',
            'debug': 'false',
        }
        self._config['SPLASH'] = {
            'title': 'SYS Toolset Management Console',
            'subtitle': 'Automation & Management Platform',
            'width': '500',
            'height': '300',
            'background_color': '#2D2D30',
            'title_color': '#FFFFFF',
            'subtitle_color': '#CCCCCC',
            'progress_color': '#0078D4',
            'font_family': 'Segoe UI',
            'title_font_size': '24',
        }
        self._config['COLORS'] = {
            'primary_color': '#2196F3',
            'success_color': '#4CAF50',
            'warning_color': '#FF9800',
            'led_color': '#B3E5FC',
            'lhd_color': '#C8E6C9',
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
        return self.get('APP', 'title', 'SYS Toolset Management')
    
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
    
    # ===== SPLASH SCREEN PROPERTIES =====
    
    @property
    def splash_title(self):
        """Titolo dello splash screen"""
        return self.get('SPLASH', 'title', 'SYS Toolset Management Console')
    
    @property
    def splash_subtitle(self):
        """Sottotitolo dello splash screen"""
        return self.get('SPLASH', 'subtitle', 'Automation & Management Platform')
    
    @property
    def splash_size(self):
        """Dimensione splash screen (width, height)"""
        width = self.get_int('SPLASH', 'width', 500)
        height = self.get_int('SPLASH', 'height', 300)
        return (width, height)
    
    @property
    def splash_bg_color(self):
        """Colore sfondo splash screen"""
        return self.get('SPLASH', 'background_color', '#2D2D30')
    
    @property
    def splash_title_color(self):
        """Colore titolo splash screen"""
        return self.get('SPLASH', 'title_color', '#FFFFFF')
    
    @property
    def splash_subtitle_color(self):
        """Colore sottotitolo splash screen"""
        return self.get('SPLASH', 'subtitle_color', '#CCCCCC')
    
    @property
    def splash_status_color(self):
        """Colore messaggio di stato splash screen"""
        return self.get('SPLASH', 'status_color', '#AAAAAA')
    
    @property
    def splash_version_color(self):
        """Colore versione splash screen"""
        return self.get('SPLASH', 'version_color', '#666666')
    
    @property
    def splash_progress_color(self):
        """Colore barra progresso splash screen"""
        return self.get('SPLASH', 'progress_color', '#0078D4')
    
    @property
    def splash_progress_bg(self):
        """Colore sfondo barra progresso"""
        return self.get('SPLASH', 'progress_background', '#3C3C3C')
    
    @property
    def splash_font_family(self):
        """Font family splash screen"""
        return self.get('SPLASH', 'font_family', 'Segoe UI')
    
    @property
    def splash_title_font_size(self):
        """Dimensione font titolo splash"""
        return self.get_int('SPLASH', 'title_font_size', 24)
    
    @property
    def splash_subtitle_font_size(self):
        """Dimensione font sottotitolo splash"""
        return self.get_int('SPLASH', 'subtitle_font_size', 10)
    
    @property
    def splash_status_font_size(self):
        """Dimensione font status splash"""
        return self.get_int('SPLASH', 'status_font_size', 9)
    
    @property
    def splash_version_font_size(self):
        """Dimensione font versione splash"""
        return self.get_int('SPLASH', 'version_font_size', 8)
    
    # ===== COLOR THEME PROPERTIES =====
    
    def get_color(self, color_key, fallback='#2196F3'):
        """Ottiene un colore dalla sezione COLORS"""
        return self.get('COLORS', color_key, fallback)
    
    @property
    def primary_color(self):
        """Colore primario tema"""
        return self.get_color('primary_color', '#2196F3')
    
    @property
    def primary_hover(self):
        """Colore primario hover"""
        return self.get_color('primary_hover', '#1976D2')
    
    @property
    def primary_pressed(self):
        """Colore primario pressed"""
        return self.get_color('primary_pressed', '#0D47A1')
    
    @property
    def success_color(self):
        """Colore success"""
        return self.get_color('success_color', '#4CAF50')
    
    @property
    def success_hover(self):
        """Colore success hover"""
        return self.get_color('success_hover', '#45a049')
    
    @property
    def success_pressed(self):
        """Colore success pressed"""
        return self.get_color('success_pressed', '#3d8b40')
    
    @property
    def warning_color(self):
        """Colore warning"""
        return self.get_color('warning_color', '#FF9800')
    
    @property
    def warning_hover(self):
        """Colore warning hover"""
        return self.get_color('warning_hover', '#F57C00')
    
    @property
    def warning_pressed(self):
        """Colore warning pressed"""
        return self.get_color('warning_pressed', '#E65100')
    
    @property
    def led_color(self):
        """Colore label LED"""
        return self.get_color('led_color', '#B3E5FC')
    
    @property
    def lhd_color(self):
        """Colore label LHD"""
        return self.get_color('lhd_color', '#C8E6C9')
    
    # ===== DIALOG DIMENSIONS =====
    
    @property
    def edit_script_dialog_size(self):
        """Dimensione dialog modifica script (width, height)"""
        width = self.get_int('DIALOGS', 'edit_script_width', 900)
        height = self.get_int('DIALOGS', 'edit_script_height', 700)
        return (width, height)
    
    @property
    def add_script_dialog_size(self):
        """Dimensione dialog aggiungi script (width, height)"""
        width = self.get_int('DIALOGS', 'add_script_width', 750)
        height = self.get_int('DIALOGS', 'add_script_height', 650)
        return (width, height)
    
    @property
    def add_module_dialog_size(self):
        """Dimensione dialog aggiungi modulo (width, height)"""
        width = self.get_int('DIALOGS', 'add_module_width', 500)
        height = self.get_int('DIALOGS', 'add_module_height', 200)
        return (width, height)
    
    def print_info(self):
        """Stampa informazioni di configurazione (debug)"""
        print(f"[CONFIG] Config file: {self._config_path}")
        print(f"[CONFIG] Scripts directory: {self.scripts_dir}")
        print(f"[CONFIG] Docs directory: {self.docs_dir}")
        print(f"[CONFIG] Logs directory: {self.logs_dir}")
        if self.debug:
            print("[CONFIG] Debug mode: ENABLED")
