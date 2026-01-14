"""
============================================================
 File: splash_screen.py
 Author: Internal Systems Automation Team
 Created: 2026-01-13

 Description:
     Splash screen professionale con progress bar per il
     caricamento dell'applicazione. Parametri configurabili
     tramite config.ini.
============================================================
"""

from PyQt6.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont


class SplashScreen(QSplashScreen):
    """Splash screen con progress bar e messaggi di caricamento"""
    
    def __init__(self, config=None):
        # Importa config se necessario
        if config is None:
            from config.config import ConfigManager
            config = ConfigManager()
        
        self.config = config
        
        # Ottieni dimensioni e colori dalla configurazione
        width, height = self.config.splash_size
        bg_color = self.config.splash_bg_color
        
        # Crea un pixmap vuoto per lo sfondo
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(bg_color))
        
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        
        # Widget centrale
        self.central_widget = QWidget(self)
        self.central_widget.setGeometry(0, 0, width, height)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(20)
        
        # Titolo applicazione
        title_label = QLabel(self.config.splash_title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont(self.config.splash_font_family, 
                          self.config.splash_title_font_size, 
                          QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.config.splash_title_color};")
        layout.addWidget(title_label)
        
        # Sottotitolo
        subtitle_label = QLabel(self.config.splash_subtitle)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont(self.config.splash_font_family, 
                             self.config.splash_subtitle_font_size)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet(f"color: {self.config.splash_subtitle_color};")
        layout.addWidget(subtitle_label)
        
        # Spaziatore
        layout.addStretch()
        
        # Messaggio di stato
        self.status_label = QLabel("Inizializzazione...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont(self.config.splash_font_family, 
                           self.config.splash_status_font_size)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(f"color: {self.config.splash_status_color};")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {self.config.splash_progress_bg};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self.config.splash_progress_color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Versione
        version_label = QLabel(f"v{self.config.app_version}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_font = QFont(self.config.splash_font_family, 
                            self.config.splash_version_font_size)
        version_label.setFont(version_font)
        version_label.setStyleSheet(f"color: {self.config.splash_version_color};")
        layout.addWidget(version_label)
        
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint
        )
    
    def show_message(self, message, progress=None):
        """Aggiorna il messaggio di stato e opzionalmente la progress bar"""
        self.status_label.setText(message)
        if progress is not None:
            self.progress_bar.setValue(progress)
        self.repaint()
        
    def set_progress(self, value):
        """Imposta il valore della progress bar"""
        self.progress_bar.setValue(value)
        self.repaint()
