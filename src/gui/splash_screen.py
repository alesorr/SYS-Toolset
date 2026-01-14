"""
============================================================
 File: splash_screen.py
 Author: Internal Systems Automation Team
 Created: 2026-01-13

 Description:
     Splash screen professionale con progress bar per il
     caricamento dell'applicazione.
============================================================
"""

from PyQt6.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont


class SplashScreen(QSplashScreen):
    """Splash screen con progress bar e messaggi di caricamento"""
    
    def __init__(self):
        # Crea un pixmap vuoto per lo sfondo
        pixmap = QPixmap(500, 300)
        pixmap.fill(QColor(45, 45, 48))  # Sfondo scuro professionale
        
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        
        # Widget centrale
        self.central_widget = QWidget(self)
        self.central_widget.setGeometry(0, 0, 500, 300)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(20)
        
        # Titolo applicazione
        title_label = QLabel("System Toolset")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title_label)
        
        # Sottotitolo
        subtitle_label = QLabel("Automation & Management Platform")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont("Segoe UI", 10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(subtitle_label)
        
        # Spaziatore
        layout.addStretch()
        
        # Messaggio di stato
        self.status_label = QLabel("Inizializzazione...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont("Segoe UI", 9)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #AAAAAA;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #3C3C3C;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Versione
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_font = QFont("Segoe UI", 8)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #666666;")
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
