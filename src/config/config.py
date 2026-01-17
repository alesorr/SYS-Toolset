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
        
        # 1. Se è un exe frozen, cerca SOLO in exe_dir/config/config.ini
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            config_file = exe_dir / 'config' / 'config.ini'
            logger.debug(f"[CONFIG] Frozen exe - cerco config.ini in: {config_file}")
            if config_file.exists():
                logger.info(f"[CONFIG] Trovato config.ini in: {config_file}")
                return config_file
            else:
                logger.error(f"[CONFIG] Config.ini NON trovato in: {config_file}")
                return None
        
        # 2. Prova nella cartella config/
        config_file = Path('config') / 'config.ini'
        logger.debug(f"[CONFIG] Cerco in: {config_file.absolute()}")
        if config_file.exists():
            logger.info(f"[CONFIG] Trovato config.ini in: {config_file.absolute()}")
            return config_file
        
        # 3. Prova nella root del progetto
        config_file = Path('config.ini')
        logger.debug(f"[CONFIG] Cerco in: {config_file.absolute()}")
        if config_file.exists():
            logger.info(f"[CONFIG] Trovato config.ini in: {config_file.absolute()}")
            return config_file
        
        # 4. Prova nella cartella src
        config_file = Path('src') / 'config' / 'config.ini'
        logger.debug(f"[CONFIG] Cerco in: {config_file.absolute()}")
        if config_file.exists():
            logger.info(f"[CONFIG] Trovato config.ini in: {config_file.absolute()}")
            return config_file
        
        logger.warning("[CONFIG] Nessun config.ini trovato in tutte le locazioni")
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
        self._config['DIALOGS'] = {
            'edit_script_width': '1300',
            'edit_script_height': '900',
            'add_script_width': '1300',
            'add_script_height': '900',
            'add_module_width': '600',
            'add_module_height': '600',
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
    
    def _get_screen_size(self):
        """Ottiene la dimensione dello schermo"""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QScreen
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                return (geometry.width(), geometry.height())
        except:
            pass
        # Fallback a dimensioni standard se non riesce
        return (1920, 1080)
    
    def _calculate_dialog_size(self, width_key, height_key, default_width_percent, default_height_percent):
        """Calcola dimensioni dialog basate su percentuale schermo o pixel assoluti"""
        screen_width, screen_height = self._get_screen_size()
        
        # Prova prima con chiavi percentuali
        width_percent = self.get(f'DIALOGS', f'{width_key}_percent')
        height_percent = self.get(f'DIALOGS', f'{height_key}_percent')
        
        # Debug
        if self.debug:
            print(f"[CONFIG DEBUG] Calculating dialog size for {width_key}")
            print(f"[CONFIG DEBUG] Screen size: {screen_width}x{screen_height}")
            print(f"[CONFIG DEBUG] width_percent from config: {width_percent}")
            print(f"[CONFIG DEBUG] height_percent from config: {height_percent}")
        
        if width_percent and height_percent:
            try:
                w_pct = float(width_percent)
                h_pct = float(height_percent)
                width = int(screen_width * w_pct)
                height = int(screen_height * h_pct)
                if self.debug:
                    print(f"[CONFIG DEBUG] Calculated from percent: {width}x{height}")
                return (width, height)
            except Exception as e:
                if self.debug:
                    print(f"[CONFIG DEBUG] Error parsing percent values: {e}")
                pass
        
        # Fallback a valori assoluti o default percentuali
        width = self.get_int('DIALOGS', width_key, int(screen_width * default_width_percent))
        height = self.get_int('DIALOGS', height_key, int(screen_height * default_height_percent))
        if self.debug:
            print(f"[CONFIG DEBUG] Fallback to absolute/default: {width}x{height}")
        return (width, height)
    
    @property
    def edit_script_dialog_size(self):
        """Dimensione dialog modifica script (width, height)"""
        return self._calculate_dialog_size('edit_script_width', 'edit_script_height', 0.65, 0.70)
    
    @property
    def add_script_dialog_size(self):
        """Dimensione dialog aggiungi script (width, height)"""
        return self._calculate_dialog_size('add_script_width', 'add_script_height', 0.65, 0.70)
    
    @property
    def add_module_dialog_size(self):
        """Dimensione dialog aggiungi modulo (width, height)"""
        width = self.get_int('DIALOGS', 'add_module_width', 600)
        height = self.get_int('DIALOGS', 'add_module_height', 400)
        return (width, height)
    
    @property
    def documentation_dialog_size(self):
        """Dimensione dialog documentazione (width, height)"""
        return self._calculate_dialog_size('documentation_width', 'documentation_height', 0.70, 0.75)
    
    @property
    def code_viewer_dialog_size(self):
        """Dimensione dialog visualizzatore codice (width, height)"""
        return self._calculate_dialog_size('code_viewer_width', 'code_viewer_height', 0.75, 0.80)
    
    # EMAIL PROPERTIES
    @property
    def email_enabled(self):
        """Verifica se l'invio email è abilitato"""
        return self._config.getboolean('EMAIL', 'enabled', fallback=False)
    
    @property
    def smtp_server(self):
        """Server SMTP"""
        return self._config.get('EMAIL', 'smtp_server', fallback='smtp.gmail.com')
    
    @property
    def smtp_port(self):
        """Porta SMTP"""
        return self._config.getint('EMAIL', 'smtp_port', fallback=587)
    
    @property
    def use_tls(self):
        """Usa TLS per SMTP"""
        return self._config.getboolean('EMAIL', 'use_tls', fallback=True)
    
    @property
    def sender_email(self):
        """Email del mittente"""
        return self._config.get('EMAIL', 'sender_email', fallback='')
    
    @property
    def sender_password(self):
        """Password email del mittente"""
        return self._config.get('EMAIL', 'sender_password', fallback='')
    
    @property
    def default_recipients(self):
        """Lista destinatari di default"""
        recipients_str = self._config.get('EMAIL', 'default_recipients', fallback='')
        return [r.strip() for r in recipients_str.split(',') if r.strip()]
    
    @property
    def default_email_subject(self):
        """Oggetto email di default"""
        return self._config.get('EMAIL', 'default_subject', fallback='[SYS Toolset] Esecuzione {script_name}')
    
    @property
    def default_email_body(self):
        """Corpo email di default"""
        return self._config.get('EMAIL', 'default_body', fallback='Report di esecuzione:\n\n{output}')
    
    def print_info(self):
        """Stampa informazioni di configurazione (debug)"""
        print(f"[CONFIG] Config file: {self._config_path}")
        print(f"[CONFIG] Scripts directory: {self.scripts_dir}")
        print(f"[CONFIG] Docs directory: {self.docs_dir}")
        print(f"[CONFIG] Logs directory: {self.logs_dir}")
        if self.debug:
            print("[CONFIG] Debug mode: ENABLED")
