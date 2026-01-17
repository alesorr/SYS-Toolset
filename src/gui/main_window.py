"""
============================================================
File: main_window.py
Author: Internal Systems Automation Team
Created: 2026-01-12

Description:
Interfaccia grafica PyQt6 per il Toolset.
Permette la selezione visuale delle categorie, script
e documentazione integrata per ogni strumento.
============================================================
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QMessageBox, QDialog,
    QDialogButtonBox, QScrollArea, QFrame, QProgressBar,
    QLineEdit, QComboBox, QTabWidget, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor
import subprocess
import os
import json
import traceback
from pathlib import Path
from config.config import ConfigManager
from db.script_repository import ScriptRepository

class ScriptExecutorThread(QThread):
    """Thread per eseguire gli script senza bloccare l'UI"""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, script_path, log_file_path=None, params=None, run_as_admin=False):
        super().__init__()
        self.script_path = script_path
        self.log_file_path = log_file_path
        self.params = params or []
        self.run_as_admin = run_as_admin
        self.process = None
        self._stop_requested = False

    def run(self):
        try:
            # Se richiesta esecuzione come admin su Windows
            if self.run_as_admin and os.name == 'nt':
                import ctypes
                # Costruisci il comando
                if self.script_path.endswith(".ps1"):
                    exe = "powershell.exe"
                    params = f"-ExecutionPolicy Bypass -NoProfile -File \"{self.script_path}\" {' '.join(self.params)}"
                elif self.script_path.endswith(".bat") or self.script_path.endswith(".cmd"):
                    exe = self.script_path
                    params = ' '.join(self.params)
                elif self.script_path.endswith(".py"):
                    exe = "python.exe"
                    params = f"-u \"{self.script_path}\" {' '.join(self.params)}"
                else:
                    self.error_signal.emit(f"Tipo di script non supportato: {self.script_path}")
                    self.finished_signal.emit()
                    return
                
                # ShellExecute con "runas" per richiedere privilegi admin
                result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
                if result <= 32:
                    self.error_signal.emit(f"Impossibile eseguire come amministratore. Codice errore: {result}")
                else:
                    self.output_signal.emit("[INFO] Script avviato con privilegi amministrativi")
                    self.output_signal.emit("[AVVISO] L'output real-time non è disponibile per script eseguiti come amministratore")
                self.finished_signal.emit()
                return
            
            # Esecuzione normale (senza privilegi admin)
            # Opzioni per nascondere la finestra della console
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # Costruisci il comando base
            if self.script_path.endswith(".ps1"):
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", self.script_path] + self.params
            elif self.script_path.endswith(".bat") or self.script_path.endswith(".cmd"):
                cmd = [self.script_path] + self.params
            elif self.script_path.endswith(".py"):
                # Aggiungi -u per output unbuffered in Python
                cmd = ["python", "-u", self.script_path] + self.params
            else:
                self.error_signal.emit(f"Tipo di script non supportato: {self.script_path}")
                self.finished_signal.emit()
                return

            # Usa Popen per poter terminare il processo
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered per output real-time
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Leggi output in tempo reale
            while True:
                if self._stop_requested:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                    self.error_signal.emit("\n[INTERRUZIONE] Esecuzione interrotta dall'utente")
                    break
                
                output = self.process.stdout.readline()
                if output:
                    self.output_signal.emit(output.rstrip())
                    if self.log_file_path:
                        self._write_to_log(output.rstrip())
                elif self.process.poll() is not None:
                    break
            
            # Leggi eventuali output rimanenti
            remaining_out, remaining_err = self.process.communicate()
            if remaining_out:
                self.output_signal.emit(remaining_out)
                if self.log_file_path:
                    self._write_to_log(remaining_out)
            if remaining_err:
                self.error_signal.emit(remaining_err)
                if self.log_file_path:
                    self._write_to_log(f"[ERRORE] {remaining_err}")

        except Exception as e:
            error_msg = f"Errore nell'esecuzione dello script: {str(e)}"
            self.error_signal.emit(error_msg)
            if self.log_file_path:
                self._write_to_log(f"[ERRORE] {error_msg}")
        finally:
            self.process = None
            self.finished_signal.emit()
    
    def stop(self):
        """Richiede l'interruzione dell'esecuzione"""
        self._stop_requested = True
    
    def _write_to_log(self, text):
        """Scrive l'output nel file di log specifico"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(text)
                if not text.endswith('\n'):
                    f.write('\n')
        except Exception as e:
            print(f"Errore scrittura log: {e}")


class RefreshThread(QThread):
    """Thread per ricaricare gli script in background"""
    finished_signal = pyqtSignal(list)  # Emette lista di categorie
    error_signal = pyqtSignal(str)

    def __init__(self, config, repository_class):
        super().__init__()
        self.config = config
        self.repository_class = repository_class

    def run(self):
        try:
            # Ricarica il repository creandone uno nuovo con scan delle cartelle
            new_repo = self.repository_class(base_path=str(self.config.scripts_dir), scan_folders=False)
            categories = new_repo.get_categories()
            self.finished_signal.emit(categories)
        except Exception as e:
            self.error_signal.emit(f"Errore nel caricamento degli script: {str(e)}")


class DocumentationViewer(QDialog):
    """Dialog per visualizzare la documentazione di uno script"""
    def __init__(self, title, doc_path, parent=None):
        super().__init__(parent)
        from config.config import ConfigManager
        self.config = ConfigManager()
        self.setWindowTitle(f"Documentazione - {title}")
        width, height = self.config.documentation_dialog_size
        self.resize(width, height)

        layout = QVBoxLayout()
        
        # Leggi e visualizza il file MD
        doc_text = QTextEdit()
        doc_text.setReadOnly(True)
        
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                doc_text.setMarkdown(f.read())
        else:
            doc_text.setText(f"Documentazione non trovata per questo strumento.")

        layout.addWidget(doc_text)

        # Bottone chiudi
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.config = ConfigManager()
        self.executor_thread = None
        self.current_category = None
        self.current_script = None

        self.initUI()
        self.show_config_banner()
    
    def _style_messagebox(self, msg_box):
        """Applica lo stile uniforme a tutti i QMessageBox"""
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: white;
            }}
            QMessageBox QLabel {{
                color: black;
                background-color: white;
                font-size: 10pt;
            }}
            QPushButton {{
                background-color: {self.config.primary_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 80px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.primary_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.config.primary_pressed};
            }}
        """)

    def initUI(self):
        self.setWindowTitle(self.config.app_title)
        width, height = self.config.window_size
        self.setGeometry(100, 100, width, height)

        # Widget principale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ===== PANNELLO SINISTRO: Categorie e Script =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Toolbar con Refresh e Add Module
        toolbar = QHBoxLayout()
        self.add_module_button = QPushButton("+ Module")
        self.add_module_button.setMaximumWidth(100)
        self.add_module_button.setMaximumHeight(28)
        self.add_module_button.clicked.connect(self.on_add_module_clicked)
        self.add_module_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.success_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.success_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.config.success_pressed};
            }}
        """)
        
        self.workflow_button = QPushButton("🔄 Workflow")
        self.workflow_button.setMaximumWidth(110)
        self.workflow_button.setMaximumHeight(28)
        self.workflow_button.clicked.connect(self.on_workflow_clicked)
        self.workflow_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setMaximumWidth(80)
        self.refresh_button.setMaximumHeight(28)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.primary_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.primary_hover};
            }}
            QPushButton:pressed {{
                background-color: #1565C0;
            }}
        """)
        toolbar.addWidget(self.add_module_button)
        toolbar.addWidget(self.workflow_button)
        toolbar.addWidget(self.refresh_button)
        
        # Bottone impostazioni
        self.settings_button = QPushButton("⚙ Impostazioni")
        self.settings_button.setMaximumHeight(28)
        self.settings_button.clicked.connect(self.on_settings_clicked)
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.primary_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.primary_hover};
            }}
            QPushButton:pressed {{
                background-color: #1565C0;
            }}
        """)
        toolbar.addWidget(self.settings_button)
        
        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # Progress bar (nascosta di default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: #f0f0f0; }} QProgressBar::chunk {{ background-color: {self.config.primary_color}; }}")
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Intestazione categorie
        categories_label = QLabel("CATEGORIE")
        categories_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(categories_label)

        # Lista categorie
        self.categories_list = QListWidget()
        self.categories_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.categories_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.categories_list.itemClicked.connect(self.on_category_selected)
        for category in self.repository.get_categories():
            self.categories_list.addItem(category)
        left_layout.addWidget(self.categories_list)

        # Intestazione script
        scripts_header_layout = QHBoxLayout()
        scripts_label = QLabel("SCRIPT")
        scripts_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        scripts_header_layout.addWidget(scripts_label)
        scripts_header_layout.addStretch()
        
        # Pulsante per aggiungere script
        self.add_script_button = QPushButton("+ Script")
        self.add_script_button.setMaximumWidth(80)
        self.add_script_button.setMaximumHeight(24)
        self.add_script_button.setEnabled(False)  # Disabilitato finché non si seleziona una categoria
        self.add_script_button.clicked.connect(self.on_add_script_clicked)
        self.add_script_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        scripts_header_layout.addWidget(self.add_script_button)
        left_layout.addLayout(scripts_header_layout)
        
        # Barra di ricerca per script
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cerca script...")
        self.search_input.setMaximumHeight(30)
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px 10px;
                color: black;
                font-size: 9pt;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
        """)
        left_layout.addWidget(self.search_input)

        # Lista script
        self.scripts_list = QListWidget()
        self.scripts_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scripts_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scripts_list.itemClicked.connect(self.on_script_selected)
        left_layout.addWidget(self.scripts_list)

        main_layout.addWidget(left_panel, 1)

        # ===== PANNELLO DESTRO: Info e Output =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Intestazione dettagli
        details_label = QLabel("DETTAGLI SCRIPT")
        details_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(details_label)

        # Nome script con icona campana
        script_name_layout = QHBoxLayout()
        
        self.script_name_label = QLabel("Seleziona uno script")
        self.script_name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.script_name_label.setStyleSheet(f"color: {self.config.primary_color};")
        script_name_layout.addWidget(self.script_name_label)
        
        # Icona notifica email (campana)
        self.email_notification_button = QPushButton("🔕")
        self.email_notification_button.setEnabled(False)
        self.email_notification_button.setFixedSize(28, 28)
        self.email_notification_button.setToolTip("Configura notifica email per questa esecuzione")
        self.email_notification_button.clicked.connect(self.configure_email_notification)
        self.email_notification_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover:enabled {
                background-color: #f0f0f0;
            }
            QPushButton:pressed:enabled {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)
        script_name_layout.addWidget(self.email_notification_button)
        
        # Icona schedulazione (orologio)
        self.schedule_button = QPushButton("⏰")
        self.schedule_button.setEnabled(False)
        self.schedule_button.setFixedSize(28, 28)
        self.schedule_button.setToolTip("Schedula esecuzione automatica script")
        self.schedule_button.clicked.connect(self.configure_schedule)
        self.schedule_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover:enabled {
                background-color: #f0f0f0;
            }
            QPushButton:pressed:enabled {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)
        script_name_layout.addWidget(self.schedule_button)
        script_name_layout.addStretch()
        
        right_layout.addLayout(script_name_layout)
        
        # Flag per tracciare configurazioni
        self.email_config = None
        self.schedule_config = None

        # Descrizione
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        right_layout.addWidget(self.description_label)

        # Bottoni
        buttons_layout = QHBoxLayout()
        
        self.exec_button = QPushButton("▶ Esegui Script")
        self.exec_button.setEnabled(False)
        self.exec_button.clicked.connect(self.execute_script)
        self.exec_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.exec_button)
        
        self.stop_button = QPushButton("⬛ Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_execution)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.stop_button)

        self.doc_button = QPushButton("📖 Visualizza Documentazione")
        self.doc_button.setEnabled(False)
        self.doc_button.clicked.connect(self.show_documentation)
        self.doc_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.doc_button)
        
        self.view_code_button = QPushButton("👁 Visualizza Codice")
        self.view_code_button.setEnabled(False)
        self.view_code_button.clicked.connect(self.show_script_code)
        self.view_code_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.warning_color};
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover:enabled {{
                background-color: {self.config.warning_hover};
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """)
        buttons_layout.addWidget(self.view_code_button)

        right_layout.addLayout(buttons_layout)

        # Intestazione output
        output_label = QLabel("OUTPUT ESECUZIONE")
        output_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(output_label)

        # Area output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 9))
        self.output_text.setStyleSheet("background-color: white; color: black; border: 1px solid #ddd;")
        right_layout.addWidget(self.output_text)

        main_layout.addWidget(right_panel, 2)
        
        # Footer con versione
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background-color: #f5f5f5; border-top: 1px solid #ddd;")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        
        footer_layout.addStretch()
        
        version_label = QLabel(f"Versione {self.config.app_version}")
        version_label.setStyleSheet("color: #666; font-size: 9pt;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch()
        
        # Aggiungi il footer al layout principale del central_widget
        central_widget_layout = QVBoxLayout()
        central_widget_layout.setContentsMargins(0, 0, 0, 0)
        central_widget_layout.setSpacing(0)
        central_widget_layout.addLayout(main_layout)
        central_widget_layout.addWidget(footer_widget)
        central_widget.setLayout(central_widget_layout)

        # Applica stili
        self.apply_styles()

    def show_config_banner(self):
        """Mostra un banner temporaneo con info sul caricamento del config.ini"""
        from PyQt6.QtCore import QTimer
        
        config_path = self.config.config_file
        
        if config_path and config_path.exists():
            message = f"✓ Config caricato: {config_path}"
            bg_color = "#4CAF50"  # Verde
        else:
            message = "⚠ Config.ini non trovato - Caricati valori di default"
            bg_color = "#FF9800"  # Arancione
        
        # Crea banner
        banner = QLabel(message, self)
        banner.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 12px 20px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 6px;
            }}
        """)
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.adjustSize()
        
        # Posiziona in basso al centro
        banner_width = banner.width() + 40
        banner_height = banner.height()
        x = (self.width() - banner_width) // 2
        y = self.height() - banner_height - 60  # 60px dal basso per stare sopra il footer
        banner.setGeometry(x, y, banner_width, banner_height)
        
        banner.show()
        
        # Auto-chiudi dopo 4 secondi
        QTimer.singleShot(4000, banner.deleteLater)

    def apply_styles(self):
        """Applica uno stile uniforme all'interfaccia"""
        stylesheet = """
            QMainWindow {
                background-color: #ffffff;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: black;
                outline: none;
            }
            QListWidget::item {
                color: black;
                padding: 5px;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
                border: none;
            }
            QListWidget::item:selected:hover {
                background-color: #1976D2;
                color: white;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #2196F3;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1976D2;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #2196F3;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #1976D2;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
                color: white;
                font-weight: bold;
            }
            QLabel {
                color: black;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: black;
            }
        """
        self.setStyleSheet(stylesheet)

    def on_category_selected(self):
        """Gestisce la selezione di una categoria"""
        item = self.categories_list.currentItem()
        if item:
            self.current_category = item.text()
            self.add_script_button.setEnabled(True)
            self.search_input.clear()  # Pulisce la ricerca quando cambi categoria
            self.update_scripts_list()
    
    def on_search_changed(self):
        """Filtra gli script in base alla ricerca"""
        self.update_scripts_list()

    def update_scripts_list(self):
        """Aggiorna la lista degli script in base alla categoria selezionata e al filtro di ricerca"""
        self.scripts_list.clear()
        self.output_text.clear()
        self.script_name_label.setText("Seleziona uno script")
        self.description_label.setText("")
        self.exec_button.setEnabled(False)
        self.doc_button.setEnabled(False)
        self.view_code_button.setEnabled(False)
        self.current_script = None

        if self.current_category:
            scripts = self.repository.get_scripts_by_category(self.current_category)
            search_text = self.search_input.text().lower()
            
            for script in scripts:
                # Filtra in base alla ricerca
                if search_text and search_text not in script['name'].lower():
                    continue
                # Crea widget personalizzato per ogni script con pulsante di cancellazione
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, script)
                
                # Widget contenitore - trasparente per usare lo stile della lista
                widget = QWidget()
                widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                widget.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                        border: none;
                    }
                    QLabel {
                        color: black;
                        background-color: transparent;
                        border: none;
                    }
                """)
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(8, 5, 5, 5)
                layout.setSpacing(8)
                
                # Label con nome script
                label = QLabel(script['name'])
                layout.addWidget(label)
                
                # Etichetta divisione (LED/LHD/ALL) con colori pastello
                division = script.get('division', 'LED')
                division_label = QLabel(division)
                if division == 'LED':
                    bg_color = '#B3E5FC'  # Azzurro pastello
                    text_color = '#01579B'  # Blu scuro
                elif division == 'LHD':
                    bg_color = '#C8E6C9'  # Verde pastello
                    text_color = '#1B5E20'  # Verde scuro
                else:  # ALL
                    bg_color = '#FFE082'  # Giallo/arancio pastello
                    text_color = '#F57F17'  # Arancio scuro
                
                division_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {bg_color};
                        color: {text_color};
                        border-radius: 8px;
                        padding: 2px 10px;
                        font-size: 8pt;
                        font-weight: bold;
                    }}
                """)
                layout.addWidget(division_label)
                layout.addStretch()
                
                # Pulsante modifica
                edit_btn = QPushButton("✎")
                edit_btn.setFixedSize(22, 22)
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        color: #666;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        font-size: 12pt;
                        font-weight: bold;
                        padding: 0px;
                        margin: 0px;
                    }
                    QPushButton:hover {
                        background-color: #2196F3;
                        color: white;
                        border: 1px solid #2196F3;
                    }
                """)
                edit_btn.clicked.connect(lambda checked, s=script: self.on_edit_script_clicked(s))
                layout.addWidget(edit_btn)
                
                # Pulsante cancella minimal e professionale
                delete_btn = QPushButton("×")
                delete_btn.setFixedSize(22, 22)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0;
                        color: #666;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        font-size: 12pt;
                        font-weight: bold;
                        padding: 2px 0px 4px 0px;
                        margin: 0px;
                    }
                    QPushButton:hover {
                        background-color: #f44336;
                        color: white;
                        border: 1px solid #f44336;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, s=script: self.on_delete_script_clicked(s))
                layout.addWidget(delete_btn)
                
                widget.setLayout(layout)
                
                # Aggiungi item alla lista
                self.scripts_list.addItem(item)
                self.scripts_list.setItemWidget(item, widget)
                # Imposta altezza consistente con le categorie
                item.setSizeHint(widget.sizeHint())

    def on_script_selected(self):
        """Gestisce la selezione di uno script"""
        item = self.scripts_list.currentItem()
        if item:
            self.current_script = item.data(Qt.ItemDataRole.UserRole)
            # Mostra il nome del file con estensione invece del nome dello script
            script_path = self.current_script.get('path', '')
            filename = script_path.split('/')[-1] if '/' in script_path else script_path
            self.script_name_label.setText(f"📄 {filename}")
            self.description_label.setText(self.current_script['description'])
            self.exec_button.setEnabled(True)
            self.doc_button.setEnabled(True)
            self.view_code_button.setEnabled(True)
            self.email_notification_button.setEnabled(True)
            self.schedule_button.setEnabled(True)
            self.output_text.clear()
            
            # Reset configurazioni quando si seleziona un nuovo script
            self.email_config = None
            self.schedule_config = None
            
            # Carica configurazioni esistenti e aggiorna icone
            script_name = self.current_script.get('name', 'Script')
            
            # Carica e mostra schedulazione esistente
            existing_schedule = self.load_schedule_config(script_name)
            if existing_schedule and existing_schedule.get('enabled'):
                self.schedule_config = existing_schedule
                self.schedule_button.setText("⏰")
                self.schedule_button.setStyleSheet("""
                    QPushButton {
                        background-color: #FFF9C4;
                        border: none;
                        font-size: 16px;
                        padding: 0px;
                    }
                    QPushButton:hover:enabled {
                        background-color: #FFF59D;
                    }
                    QPushButton:pressed:enabled {
                        background-color: #FFF176;
                    }
                """)
            else:
                # Ripristina icona normale
                self.schedule_button.setText("⏰")
                self.schedule_button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        font-size: 16px;
                        padding: 0px;
                    }
                    QPushButton:hover:enabled {
                        background-color: #f0f0f0;
                    }
                    QPushButton:pressed:enabled {
                        background-color: #e0e0e0;
                    }
                """)

    def execute_script(self):
        """Esegue lo script selezionato"""
        from utils.logger import logger
        from datetime import datetime
        
        if not self.current_script:
            return

        # Ottieni il nome del modulo selezionato
        module_name = self.categories_list.currentItem().text() if self.categories_list.currentItem() else "N/A"
        script_name = self.current_script['name']
        script_path = self.current_script['path']
        
        # Crea un file di log specifico per questa esecuzione
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = self.config.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome file: timestamp_nomemodulo.log
        module_name_clean = module_name.replace(" ", "_").replace("/", "_")
        script_log_file = log_dir / f"{timestamp}_{module_name_clean}.log"
        
        # Scrivi intestazione nel log specifico
        try:
            with open(script_log_file, 'w', encoding='utf-8') as f:
                f.write(f"========================================\n")
                f.write(f"Esecuzione Script\n")
                f.write(f"========================================\n")
                f.write(f"Data/Ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Modulo: {module_name}\n")
                f.write(f"Script: {script_name}\n")
                f.write(f"Path: {script_path}\n")
                f.write(f"========================================\n\n")
            logger.info(f"Log file creato: {script_log_file}")
        except Exception as e:
            logger.error(f"Errore creazione log file: {e}")
            script_log_file = None
        
        # Salva il riferimento al log file per usarlo nei metodi append
        self.current_script_log = script_log_file

        self.output_text.clear()
        initial_msg = f"⏳ Esecuzione in corso: {self.current_script['name']}...\n"
        self.output_text.setText(initial_msg)
        if script_log_file:
            self._write_to_current_log(initial_msg)
        self.exec_button.setEnabled(False)

        # Costruisce il path dello script
        # Normalizza il path sostituendo / con il separatore del sistema operativo
        script_rel_path = self.current_script["path"].replace('/', os.sep)
        script_base_path = os.path.join(str(self.config.scripts_dir), script_rel_path)
        
        # Verifica se il path ha già un'estensione
        _, ext_existing = os.path.splitext(script_base_path)
        
        script_path = None
        if ext_existing in ['.ps1', '.bat', '.py', '.sh', '.exe']:
            # Il path ha già un'estensione valida, usalo direttamente
            if os.path.exists(script_base_path):
                script_path = script_base_path
                logger.info(f"Script trovato con estensione: {script_path}")
        else:
            # Il path non ha estensione, cerca con le estensioni
            for ext in ['.ps1', '.bat', '.py', '.sh', '.exe']:
                candidate = script_base_path + ext
                if os.path.exists(candidate):
                    script_path = candidate
                    logger.info(f"Script trovato: {script_path}")
                    break
        
        if not script_path:
            error_msg = f"Script non trovato: {script_base_path}"
            logger.error(error_msg)
            self.output_text.setText(f"[ERRORE] {error_msg}")
            self.exec_button.setEnabled(True)
            return
        
        logger.info(f"Executing: {script_path}")
        
        # Ottieni parametri salvati nello script (può essere stringa o lista)
        params_raw = self.current_script.get('params', '')
        if isinstance(params_raw, list):
            params = params_raw
        elif isinstance(params_raw, str):
            params = params_raw.split() if params_raw else []
        else:
            params = []
        
        # Ottieni flag run_as_admin
        run_as_admin = self.current_script.get('run_as_admin', False)
        
        # Costruisci e mostra il comando completo
        if script_path.endswith(".ps1"):
            cmd_display = f"powershell -ExecutionPolicy Bypass -NoProfile -File \"{script_path}\""
        elif script_path.endswith(".py"):
            cmd_display = f"python -u \"{script_path}\""
        else:
            cmd_display = f"\"{script_path}\""
        
        if params:
            cmd_display += f" {' '.join(params)}"
            logger.info(f"Parametri: {params}")
        
        if run_as_admin:
            cmd_display = f"[ADMIN] {cmd_display}"
            logger.info("Running as administrator")
        
        # Mostra il comando nell'output
        self.output_text.append(f"\n📌 Comando: {cmd_display}\n")
        if script_log_file:
            self._write_to_current_log(f"\nComando: {cmd_display}\n")
        
        self.executor_thread = ScriptExecutorThread(script_path, str(script_log_file) if script_log_file else None, params, run_as_admin)
        self.executor_thread.output_signal.connect(self.append_output)
        self.executor_thread.error_signal.connect(self.append_error)
        self.executor_thread.finished_signal.connect(self.on_execution_finished)
        self.executor_thread.start()
        
        # Abilita stop e disabilita exec
        self.stop_button.setEnabled(True)
        self.exec_button.setEnabled(False)

    def append_output(self, text):
        """Aggiunge output al text area e al log file"""
        self.output_text.append(text)
        if hasattr(self, 'current_script_log') and self.current_script_log:
            self._write_to_current_log(text)

    def append_error(self, text):
        """Aggiunge errore al text area con styling e al log file"""
        error_msg = f"[ERRORE] {text}"
        self.output_text.append(error_msg)
        if hasattr(self, 'current_script_log') and self.current_script_log:
            self._write_to_current_log(error_msg)

    def on_execution_finished(self):
        """Gestisce la fine dell'esecuzione dello script"""
        completion_msg = "\n[OK] Esecuzione completata"
        self.output_text.append(completion_msg)
        if hasattr(self, 'current_script_log') and self.current_script_log:
            self._write_to_current_log(completion_msg)
            self._write_to_current_log(f"\n{'='*40}\n")
            self.current_script_log = None
        self.exec_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def stop_execution(self):
        """Interrompe l'esecuzione in corso"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.output_text.append("\n[STOP] Interruzione in corso...")
            self.executor_thread.stop()
            self.stop_button.setEnabled(False)
    
    def _write_to_current_log(self, text):
        """Scrive nel file di log corrente dell'esecuzione"""
        if not hasattr(self, 'current_script_log') or not self.current_script_log:
            return
        try:
            with open(self.current_script_log, 'a', encoding='utf-8') as f:
                f.write(text)
                if not text.endswith('\n'):
                    f.write('\n')
        except Exception as e:
            from utils.logger import logger
            logger.error(f"Errore scrittura log: {e}")

    def on_refresh_clicked(self):
        """Gestisce il click sul bottone refresh"""
        from utils.logger import logger
        
        # Salva lo stato corrente prima del refresh
        self.saved_category = self.current_category
        self.saved_script_name = self.current_script['name'] if self.current_script else None
        
        logger.info(f"Refresh clicked! Scripts dir: {self.config.scripts_dir}")
        self.output_text.setText(f"[REFRESH] Usando scripts_dir: {self.config.scripts_dir}")
        
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Crea un thread per il refresh
        self.refresh_thread = RefreshThread(self.config, ScriptRepository)
        self.refresh_thread.finished_signal.connect(self.on_refresh_completed)
        self.refresh_thread.error_signal.connect(self.on_refresh_error)
        self.refresh_thread.start()

    def on_refresh_completed(self, categories):
        """Callback quando il refresh è completato"""
        self.progress_bar.setValue(100)
        
        # Ricarica il repository principale leggendo da index.json
        self.repository = ScriptRepository(base_path=str(self.config.scripts_dir), scan_folders=False)
        
        # Aggiorna la lista categorie (svuota e ripopola)
        self.categories_list.clear()
        self.scripts_list.clear()
        
        repo_categories = self.repository.get_categories()
        if not repo_categories:
            self.output_text.setText("[AVVISO] Nessuna categoria di script trovata!")
            self.output_text.append(f"Cartella cercata: {self.config.scripts_dir}")
        else:
            self.output_text.setText(f"[OK] {len(repo_categories)} categoria(e) caricate\n")
            for category in repo_categories:
                self.categories_list.addItem(category)
        
        # Ripristina lo stato salvato
        if hasattr(self, 'saved_category') and self.saved_category:
            # Trova e seleziona la categoria salvata
            items = self.categories_list.findItems(self.saved_category, Qt.MatchFlag.MatchExactly)
            if items:
                self.categories_list.setCurrentItem(items[0])
                # Trigger manuale per ricaricare gli script della categoria
                self.on_category_selected()
                
                # Ripristina lo script salvato
                if hasattr(self, 'saved_script_name') and self.saved_script_name:
                    for i in range(self.scripts_list.count()):
                        item = self.scripts_list.item(i)
                        # Confronta con il nome dello script salvato
                        script_data = item.data(Qt.ItemDataRole.UserRole)
                        if script_data and script_data.get('name') == self.saved_script_name:
                            self.scripts_list.setCurrentItem(item)
                            self.on_script_selected()
                            break
        
        if not hasattr(self, 'saved_category') or not self.saved_category:
            # Nessuno stato da ripristinare, resetta tutto
            self.script_name_label.setText("Seleziona uno script")
            self.description_label.setText("")
            self.exec_button.setEnabled(False)
            self.doc_button.setEnabled(False)
            self.view_code_button.setEnabled(False)
            self.current_script = None
            self.current_category = None
        
        self.output_text.append("[OK] Script ricaricati!")
        
        # Nascondi progress bar dopo 1 secondo
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.refresh_button.setEnabled(True)

    def on_refresh_error(self, error):
        """Callback quando c'è un errore nel refresh"""
        self.output_text.setText(f"[ERRORE] {error}")
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)

    def show_documentation(self):
        """Mostra la documentazione dello script selezionato"""
        if not self.current_script:
            return

        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()

        # Costruisci il percorso del file MD
        doc_filename = self.current_script['name'].replace(" ", "_").lower() + ".md"
        doc_path = self.config.docs_dir / self.current_category.lower() / doc_filename

        # Fallback se il percorso non esiste
        if not doc_path.exists():
            doc_path = self.config.docs_dir / f"{self.current_script['name']}.md"

        dialog = DocumentationViewer(self.current_script['name'], str(doc_path), self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())
        
        try:
            dialog.exec()
        finally:
            overlay.deleteLater()
    
    def show_script_code(self):
        """Mostra il contenuto del file di script selezionato"""
        if not self.current_script:
            return
        
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()
        
        # Costruisci il percorso del file script
        script_path = self.current_script.get('path', '')
        script_file_path = Path(self.config.scripts_dir) / script_path
        
        if not script_file_path.exists():
            overlay.deleteLater()
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(f"File script non trovato: {script_file_path}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()
            return
        
        # Apri il dialog per visualizzare il codice
        filename = script_path.split('/')[-1] if '/' in script_path else script_path
        dialog = ScriptCodeViewer(filename, str(script_file_path), self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())
        
        try:
            dialog.exec()
        finally:
            overlay.deleteLater()
    
    def configure_email_notification(self):
        """Apre il dialog per configurare la notifica email"""
        if not self.current_script:
            return
        
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()
        
        # Apri il dialog di configurazione email
        dialog = EmailConfigDialog(self, self.config)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Se c'era già una configurazione, ripristinala
        if self.email_config and self.email_config.get('enabled'):
            dialog.recipients_input.setText(", ".join(self.email_config.get('recipients', [])))
            dialog.subject_input.setText(self.email_config.get('subject', ''))
            dialog.body_input.setPlainText(self.email_config.get('body', ''))
        
        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())
        
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.email_config = dialog.email_config
                # Cambia l'icona della campana se l'email è abilitata
                if self.email_config and self.email_config.get('enabled'):
                    self.email_notification_button.setText("🔔")
                    self.email_notification_button.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            font-size: 16px;
                            padding: 0px;
                        }
                        QPushButton:hover:enabled {
                            background-color: #FFE0B2;
                        }
                        QPushButton:pressed:enabled {
                            background-color: #FFCC80;
                        }
                    """)
                    # Messaggio di conferma
                    num_recipients = len(self.email_config.get('recipients', []))
                    self.output_text.append(f"\n✅ Notifica email ATTIVATA per questa esecuzione")
                    self.output_text.append(f"📧 Destinatari: {num_recipients}")
                else:
                    # Ripristina campana disattivata
                    self.email_notification_button.setText("🔕")
                    self.email_notification_button.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            font-size: 16px;
                            padding: 0px;
                        }
                        QPushButton:hover:enabled {
                            background-color: #f0f0f0;
                        }
                        QPushButton:pressed:enabled {
                            background-color: #e0e0e0;
                        }
                        QPushButton:disabled {
                            opacity: 0.5;
                        }
                    """)
                    self.output_text.append(f"\n🔕 Notifica email DISATTIVATA")
        finally:
            overlay.deleteLater()
    
    def configure_schedule(self):
        """Apre il dialog per configurare la schedulazione automatica"""
        if not self.current_script:
            return
        
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()
        
        # Carica configurazione esistente se presente
        script_name = self.current_script.get('name', 'Script')
        existing_config = self.load_schedule_config(script_name)
        
        # Apri il dialog di schedulazione
        dialog = ScheduleDialog(self, script_name, existing_config)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())
        
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.schedule_config = dialog.schedule_config
                
                # Gestisci eliminazione totale
                if self.schedule_config and self.schedule_config.get('delete_all'):
                    self.delete_schedule_config(script_name)
                    self.schedule_config = None
                    # Ripristina icona normale
                    self.schedule_button.setText("⏰")
                    self.schedule_button.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            font-size: 16px;
                            padding: 0px;
                        }
                        QPushButton:hover:enabled {
                            background-color: #f0f0f0;
                        }
                        QPushButton:pressed:enabled {
                            background-color: #e0e0e0;
                        }
                    """)
                    self.output_text.append(f"\n❌ Schedulazione ELIMINATA per lo script '{script_name}'")
                # Salva configurazione
                elif self.schedule_config and self.schedule_config.get('enabled'):
                    self.save_schedule_config(script_name, self.schedule_config)
                    # Cambia l'icona se lo scheduling è abilitato
                    self.schedule_button.setText("⏰")
                    self.schedule_button.setStyleSheet("""
                        QPushButton {
                            background-color: #FFF9C4;
                            border: none;
                            font-size: 16px;
                            padding: 0px;
                        }
                        QPushButton:hover:enabled {
                            background-color: #FFF59D;
                        }
                        QPushButton:pressed:enabled {
                            background-color: #FFF176;
                        }
                    """)
                    # Messaggio di conferma
                    num_triggers = len(self.schedule_config.get('triggers', []))
                    self.output_text.append(f"\n✅ Schedulazione SALVATA")
                    self.output_text.append(f"📝 Task: {self.schedule_config.get('task_name', '')}")
                    self.output_text.append(f"⏰ Trigger configurati: {num_triggers}")
        finally:
            overlay.deleteLater()
    
    def get_schedules_dir(self):
        """Restituisce il percorso della directory schedules"""
        import os
        import sys
        
        # Se eseguito come eseguibile PyInstaller
        if getattr(sys, 'frozen', False):
            # Cerca nella directory dell'eseguibile
            exe_dir = Path(sys.executable).parent
            schedules_dir = exe_dir / "schedules"
        else:
            # Se eseguito come script Python, usa la directory del progetto
            base_dir = Path(__file__).parent.parent.parent
            schedules_dir = base_dir / "schedules"
        
        # Crea la directory se non esiste
        schedules_dir.mkdir(exist_ok=True)
        return schedules_dir
    
    def get_schedule_filepath(self, script_name):
        """Restituisce il percorso del file JSON per lo script"""
        safe_name = script_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        return self.get_schedules_dir() / f"{safe_name}.json"
    
    def save_schedule_config(self, script_name, config):
        """Salva la configurazione di scheduling in un file JSON"""
        import json
        filepath = self.get_schedule_filepath(script_name)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.output_text.append(f"💾 Configurazione salvata in: {filepath}")
        except Exception as e:
            self.output_text.append(f"❌ Errore nel salvataggio: {e}")
    
    def load_schedule_config(self, script_name):
        """Carica la configurazione di scheduling da file JSON"""
        import json
        filepath = self.get_schedule_filepath(script_name)
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            except Exception as e:
                self.output_text.append(f"⚠️ Errore nel caricamento schedulazione: {e}")
        return None
    
    def delete_schedule_config(self, script_name):
        """Elimina il file di configurazione scheduling"""
        filepath = self.get_schedule_filepath(script_name)
        if filepath.exists():
            try:
                filepath.unlink()
                self.output_text.append(f"🗑️ File configurazione eliminato: {filepath}")
            except Exception as e:
                self.output_text.append(f"❌ Errore nell'eliminazione: {e}")
    
    def on_workflow_clicked(self):
        """Apre il dialog per gestire i workflow"""
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()
        
        # Apri il dialog di gestione workflow
        dialog = WorkflowManagerDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())
        
        try:
            dialog.exec()
        finally:
            overlay.deleteLater()
    
    def on_add_module_clicked(self):
        """Apre il dialog per aggiungere un nuovo modulo"""
        # Overlay scuro per mettere in risalto il dialog
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()

        dialog = AddModuleDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Centra il dialog sopra la finestra principale
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())

        try:
            if dialog.exec():
                module_name = dialog.get_module_name()
                self.create_module(module_name)
        finally:
            overlay.hide()
            overlay.deleteLater()

    def on_add_script_clicked(self):
        """Apre il dialog per aggiungere un nuovo script"""
        if not self.current_category:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Seleziona prima una categoria!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()
            return
        
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()

        dialog = AddScriptDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())

        try:
            if dialog.exec():
                script_info = dialog.get_script_info()
                self.create_script(script_info)
        finally:
            overlay.hide()
            overlay.deleteLater()

    def on_settings_clicked(self):
        """Apre il dialog delle impostazioni"""
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()

        dialog = SettingsDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())

        try:
            dialog.exec()
        finally:
            overlay.hide()
            overlay.deleteLater()

    def on_delete_script_clicked(self, script):
        """Gestisce la cancellazione di uno script"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conferma Cancellazione")
        msg_box.setText(f"Sei sicuro di voler cancellare lo script '{script['name']}'?")
        msg_box.setInformativeText("Il file verrà eliminato definitivamente.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        self._style_messagebox(msg_box)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_script(script)
    
    def on_edit_script_clicked(self, script):
        """Apre il dialog per modificare uno script esistente"""
        # Overlay scuro
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.show()
        overlay.raise_()

        dialog = EditScriptDialog(self, script, self.config.scripts_dir, self.current_category)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Centra il dialog
        dialog.adjustSize()
        parent_center = self.frameGeometry().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(parent_center)
        dialog.move(dialog_rect.topLeft())

        try:
            if dialog.exec():
                updated_script_info = dialog.get_script_info()
                self.update_script(script, updated_script_info)
        finally:
            overlay.hide()
            overlay.deleteLater()

    def create_script(self, script_info):
        """Crea un nuovo file di script e aggiorna index.json"""
        from utils.logger import logger
        
        try:
            scripts_dir = Path(self.config.scripts_dir).resolve()
            category_dir = scripts_dir / self.current_category
            
            # Crea il file script
            script_path = category_dir / script_info['filename']
            
            # Verifica se il file esiste già
            if script_path.exists():
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Errore")
                msg_box.setText(f"Il file '{script_info['filename']}' esiste già!")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                self._style_messagebox(msg_box)
                msg_box.exec()
                return
            
            # Crea file con contenuto fornito dall'utente o template base
            if script_info.get('code'):
                # Usa il codice fornito dall'utente
                content = script_info['code']
                logger.info(f"Using user-provided code for script")
            else:
                # Crea template base in base all'estensione
                extension = script_path.suffix.lower()
                if extension == '.ps1':
                    content = f"# {script_info['name']}\n# {script_info['description']}\n\nWrite-Host 'Script {script_info['name']} in esecuzione...'\n"
                elif extension == '.py':
                    content = f"# {script_info['name']}\n# {script_info['description']}\n\nprint('Script {script_info['name']} in esecuzione...')\n"
                elif extension == '.bat':
                    content = f"@echo off\nREM {script_info['name']}\nREM {script_info['description']}\n\necho Script {script_info['name']} in esecuzione...\n"
                else:
                    content = f"# {script_info['name']}\n# {script_info['description']}\n"
            
            script_path.write_text(content, encoding='utf-8')
            logger.info(f"Script file created: {script_path}")
            
            # Aggiorna index.json
            index_file = scripts_dir / "index.json"
            if index_file.exists():
                index = json.loads(index_file.read_text(encoding='utf-8'))
            else:
                index = {}
            
            # Aggiungi lo script alla categoria
            if self.current_category not in index:
                index[self.current_category] = []
            
            # Rimuovi estensione dal path per index.json
            script_path_str = f"{self.current_category}/{script_info['filename']}"
            
            new_script = {
                "name": script_info['name'],
                "description": script_info['description'],
                "path": script_path_str,
                "params": [],
                "division": script_info.get('division', 'LED')
            }
            
            index[self.current_category].append(new_script)
            index_file.write_text(json.dumps(index, indent=4, ensure_ascii=False), encoding='utf-8')
            logger.info(f"Script '{script_info['name']}' added to index.json")
            
            self.output_text.setText(f"[OK] Script '{script_info['name']}' creato con successo!")
            self.output_text.append(f"File: {script_path}")
            
            # Refresh automatico
            QTimer.singleShot(500, self.on_refresh_clicked)
            
        except Exception as e:
            logger.error(f"Errore nella creazione dello script: {e}", exc_info=True)
            error_msg = f"Errore nella creazione dello script:\\n{str(e)}"
            self.output_text.setText(f"[ERRORE] {error_msg}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(error_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()

    def delete_script(self, script):
        """Cancella un file di script, la sua cartella e aggiorna index.json"""
        from utils.logger import logger
        import shutil
        
        try:
            scripts_dir = Path(self.config.scripts_dir).resolve()
            
            # Trova e cancella il file
            script_path = scripts_dir / script['path']
            if script_path.exists():
                script_path.unlink()
                logger.info(f"Script file deleted: {script_path}")
            
            # Rimuovi la cartella dello script se esiste
            # La cartella dovrebbe essere in scripts/{nome_script}/
            script_folder = scripts_dir / script['name']
            if script_folder.exists() and script_folder.is_dir():
                shutil.rmtree(script_folder)
                logger.info(f"Script folder deleted: {script_folder}")
            
            # Aggiorna index.json
            index_file = scripts_dir / "index.json"
            if index_file.exists():
                index = json.loads(index_file.read_text(encoding='utf-8'))
                
                # Rimuovi lo script dalla categoria
                if self.current_category in index:
                    index[self.current_category] = [
                        s for s in index[self.current_category] 
                        if s['name'] != script['name']
                    ]
                    
                    index_file.write_text(json.dumps(index, indent=4, ensure_ascii=False), encoding='utf-8')
                    logger.info(f"Script '{script['name']}' removed from index.json")
            
            self.output_text.setText(f"[OK] Script '{script['name']}' cancellato con successo!")
            
            # Refresh automatico
            QTimer.singleShot(500, self.on_refresh_clicked)
            
        except Exception as e:
            logger.error(f"Errore nella cancellazione dello script: {e}", exc_info=True)
            error_msg = f"Errore nella cancellazione dello script:\\n{str(e)}"
            self.output_text.setText(f"[ERRORE] {error_msg}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(error_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()
    
    def update_script(self, old_script, new_script_info):
        """Aggiorna un file di script esistente e index.json"""
        from utils.logger import logger
        import shutil
        
        try:
            scripts_dir = Path(self.config.scripts_dir).resolve()
            category_dir = scripts_dir / self.current_category
            
            # Trova il file reale (potrebbe avere estensione non specificata in index.json)
            old_script_base = scripts_dir / old_script['path']
            old_script_path = None
            if old_script_base.exists():
                old_script_path = old_script_base.resolve()
            else:
                # Cerca con estensioni comuni
                for ext in ['.ps1', '.bat', '.py', '.sh', '.exe']:
                    candidate = Path(str(old_script_base) + ext)
                    if candidate.exists():
                        old_script_path = candidate.resolve()
                        break
            
            if not old_script_path:
                raise FileNotFoundError(f"Script originale non trovato: {old_script['path']}")
            
            new_script_path = (category_dir / new_script_info['filename']).resolve()
            
            # Se il nome del file è cambiato, rinomina/sposta il file
            if old_script_path != new_script_path:
                if new_script_path.exists():
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setWindowTitle("Errore")
                    msg_box.setText(f"Il file '{new_script_info['filename']}' esiste già!")
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                    self._style_messagebox(msg_box)
                    msg_box.exec()
                    return
                
                # Rinomina il file
                if old_script_path.exists():
                    old_script_path.rename(new_script_path)
                    logger.info(f"Script file renamed: {old_script_path} -> {new_script_path}")
            
            # Aggiorna il contenuto del file se fornito (usa sempre new_script_path)
            if new_script_info.get('code'):
                new_script_path.write_text(new_script_info['code'], encoding='utf-8')
                logger.info(f"Script content updated: {new_script_path}")
            
            # Aggiorna index.json
            index_file = scripts_dir / "index.json"
            if index_file.exists():
                index = json.loads(index_file.read_text(encoding='utf-8'))
                
                # Trova e aggiorna lo script
                if self.current_category in index:
                    for i, s in enumerate(index[self.current_category]):
                        if s['name'] == old_script['name']:
                            index[self.current_category][i] = {
                                "name": new_script_info['name'],
                                "description": new_script_info['description'],
                                "path": f"{self.current_category}/{new_script_info['filename']}",
                                "params": new_script_info.get('params', ''),
                                "division": new_script_info.get('division', 'LED'),
                                "run_as_admin": new_script_info.get('run_as_admin', False)
                            }
                            break
                    
                    index_file.write_text(json.dumps(index, indent=4, ensure_ascii=False), encoding='utf-8')
                    logger.info(f"Script '{new_script_info['name']}' updated in index.json")
            
            self.output_text.setText(f"[OK] Script '{new_script_info['name']}' aggiornato con successo!")
            
            # Refresh automatico
            QTimer.singleShot(500, self.on_refresh_clicked)
            
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dello script: {e}", exc_info=True)
            error_msg = f"Errore nell'aggiornamento dello script:\\n{str(e)}"
            self.output_text.setText(f"[ERRORE] {error_msg}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(error_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()

    def create_module(self, module_name):
        """Crea una nuova categoria di script"""
        from utils.logger import logger
        
        try:
            # Assicurati che scripts_dir sia un Path assoluto
            scripts_dir = Path(self.config.scripts_dir).resolve()
            
            logger.info(f"Creating module '{module_name}' in {scripts_dir}")
            
            # Debug: stampa il path
            self.output_text.setText(f"[CREATE MODULE] Scripts dir: {scripts_dir}")
            self.output_text.append(f"[DEBUG] Exists: {scripts_dir.exists()}")
            
            # Crea la cartella del modulo
            module_dir = scripts_dir / module_name
            self.output_text.append(f"[DEBUG] Module dir sarà: {module_dir}")
            
            module_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Module directory created: {module_dir}")
            self.output_text.append(f"[DEBUG] Cartella creata: {module_dir.exists()}")
            
            # Aggiorna index.json
            index_file = scripts_dir / "index.json"
            if index_file.exists():
                index = json.loads(index_file.read_text(encoding='utf-8'))
                logger.info(f"Index.json trovato: {index_file}")
            else:
                index = {}
                logger.warning(f"Index.json non trovato: {index_file}")
            
            # Aggiungi il nuovo modulo se non esiste
            if module_name not in index:
                index[module_name] = []
                index_file.write_text(json.dumps(index, indent=4, ensure_ascii=False), encoding='utf-8')
                logger.info(f"Module '{module_name}' aggiunto a index.json")
            
            # Messaggio di successo
            self.output_text.setText(f"[OK] Modulo '{module_name}' creato con successo!")
            self.output_text.append(f"Cartella: {module_dir.absolute()}")
            self.output_text.append("Aggiungi file .ps1/.bat/.py nella cartella e usa Refresh")
            
            logger.info(f"Module creation completed for '{module_name}'")
            
            # Refresh automatico
            QTimer.singleShot(500, self.on_refresh_clicked)
        except Exception as e:
            logger.error(f"Errore nella creazione del modulo: {e}", exc_info=True)
            error_msg = f"Errore nella creazione del modulo:\n{str(e)}\n\n{traceback.format_exc()}"
            self.output_text.setText(f"[ERRORE] {error_msg}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(error_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            self._style_messagebox(msg_box)
            msg_box.exec()


class AddModuleDialog(QDialog):
    """Dialog per aggiungere un nuovo modulo"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.module_name = None
        from config.config import ConfigManager
        self.config = ConfigManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Aggiungi Nuovo Modulo")
        width, height = self.config.add_module_dialog_size
        self.resize(width, height)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.move(x, y)
        
        # Stile con sfondo bianco e testi neri
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titolo
        title_label = QLabel("CREA NUOVO MODULO")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Separatore
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(line)
        
        # Nome modulo
        label = QLabel("Nome del modulo:")
        layout.addWidget(label)
        
        # Input field
        from PyQt6.QtWidgets import QLineEdit
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Es: MyModule, DataProcessor, dispatcher, etc")
        layout.addWidget(self.name_input)
        
        # Aggiunge spazio elastico prima dei pulsanti
        layout.addStretch()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

    def get_module_name(self):
        """Ritorna il nome del modulo inserito"""
        return self.name_input.text().strip()

    def accept(self):
        """Valida e accetta il dialog"""
        if not self.get_module_name():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Inserisci un nome per il modulo!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        super().accept()


class AddScriptDialog(QDialog):
    """Dialog per aggiungere un nuovo script"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.script_info = None
        from config.config import ConfigManager
        self.config = ConfigManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Aggiungi Nuovo Script")
        width, height = self.config.add_script_dialog_size
        self.resize(width, height)
        self.setMinimumWidth(800)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.move(x, y)
        
        # Stile con sfondo bianco e testi neri
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
            QTextEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titolo
        title_label = QLabel("CREA NUOVO SCRIPT")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Separatore
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(line)
        
        # Nome script
        name_label = QLabel("Nome dello script:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Es: BackupDatabase, CleanLogs, etc")
        layout.addWidget(self.name_input)
        
        # Nome file (con estensione)
        filename_label = QLabel("Nome file (includi estensione):")
        layout.addWidget(filename_label)
        
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Es: backup.ps1, script.py, run.bat")
        layout.addWidget(self.filename_input)
        
        # Descrizione
        desc_label = QLabel("Descrizione:")
        layout.addWidget(desc_label)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Breve descrizione dello script")
        layout.addWidget(self.desc_input)
        
        # Divisione (LED/LHD)
        division_label = QLabel("Divisione:")
        layout.addWidget(division_label)
        
        self.division_combo = QComboBox()
        self.division_combo.addItems(["LED", "LHD", "ALL"])
        self.division_combo.setStyleSheet("""
            QComboBox {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QComboBox:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
        """)
        layout.addWidget(self.division_combo)
        
        # Codice script (area grande per paste)
        code_label = QLabel("Codice Script (opzionale - puoi fare paste qui):")
        layout.addWidget(code_label)
        
        self.code_input = QTextEdit()
        self.code_input.setPlaceholderText("Incolla qui il codice del tuo script...\n\nSe lasci vuoto, verrà creato un template base.")
        layout.addWidget(self.code_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

    def get_script_info(self):
        """Ritorna le informazioni dello script inserito"""
        return {
            'name': self.name_input.text().strip(),
            'filename': self.filename_input.text().strip(),
            'description': self.desc_input.text().strip() or "Nessuna descrizione",
            'code': self.code_input.toPlainText().strip(),
            'division': self.division_combo.currentText()
        }

    def accept(self):
        """Valida e accetta il dialog"""
        if not self.name_input.text().strip():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Inserisci un nome per lo script!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        if not self.filename_input.text().strip():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Inserisci il nome del file con estensione!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        
        # Valida che il filename abbia un'estensione
        filename = self.filename_input.text().strip()
        if '.' not in filename:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Il nome file deve includere un'estensione (es: .ps1, .py, .bat)")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        
        super().accept()

class EditScriptDialog(QDialog):
    """Dialog per modificare uno script esistente"""
    def __init__(self, parent=None, script=None, scripts_dir="", category=""):
        super().__init__(parent)
        self.script = script
        self.scripts_dir = scripts_dir
        self.category = category
        self.script_info = None
        from config.config import ConfigManager
        self.config = ConfigManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Modifica Script")
        width, height = self.config.edit_script_dialog_size
        self.resize(width, height)
        self.setMinimumWidth(800)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.move(x, y)
        
        # Verifica che lo script sia valido
        if not self.script or not isinstance(self.script, dict):
            self.script = {
                'name': '',
                'path': '',
                'description': '',
                'division': 'LED',
                'params': ''
            }
        
        # Stile con sfondo bianco e testi neri
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
            QTextEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titolo
        title_label = QLabel("MODIFICA SCRIPT")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2196F3;")
        layout.addWidget(title_label)
        
        # Separatore
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(line)
        
        # Nome script
        name_label = QLabel("Nome dello script:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setText(self.script.get('name', ''))
        layout.addWidget(self.name_input)
        
        # Nome file (con estensione)
        filename_label = QLabel("Nome file (includi estensione):")
        layout.addWidget(filename_label)
        
        self.filename_input = QLineEdit()
        # Estrai il filename dal path, cercando il file reale con estensione
        script_path = self.script.get('path', '')
        filename = ''
        if script_path:
            # Costruisci il path completo
            full_path = Path(self.scripts_dir) / script_path
            # Se il file esiste già con estensione, usa quello
            if full_path.exists():
                filename = full_path.name
            else:
                # Cerca il file con estensioni comuni
                for ext in ['.ps1', '.bat', '.py', '.sh', '.exe']:
                    candidate = Path(str(full_path) + ext)
                    if candidate.exists():
                        filename = candidate.name
                        break
                # Se non trovato, usa il nome dal path
                if not filename:
                    filename = Path(script_path).name
        self.filename_input.setText(filename)
        layout.addWidget(self.filename_input)
        
        # Descrizione
        desc_label = QLabel("Descrizione:")
        layout.addWidget(desc_label)
        
        self.desc_input = QLineEdit()
        self.desc_input.setText(self.script.get('description', ''))
        layout.addWidget(self.desc_input)
        
        # Divisione (LED/LHD)
        division_label = QLabel("Divisione:")
        layout.addWidget(division_label)
        
        self.division_combo = QComboBox()
        self.division_combo.addItems(["LED", "LHD", "ALL"])
        current_division = self.script.get('division', 'LED')
        self.division_combo.setCurrentText(current_division)
        self.division_combo.setStyleSheet("""
            QComboBox {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QComboBox:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
        """)
        layout.addWidget(self.division_combo)
        
        # Parametri (opzionali)
        params_label = QLabel("Parametri (opzionali, separati da spazio):")
        layout.addWidget(params_label)
        
        self.params_input = QLineEdit()
        # Gestisci params come stringa o lista
        params = self.script.get('params', '')
        if isinstance(params, list):
            params = ' '.join(params)
        self.params_input.setText(params)
        self.params_input.setPlaceholderText("Es: -arg1 value1 -arg2 value2")
        layout.addWidget(self.params_input)
        
        # Checkbox per esecuzione come amministratore
        from PyQt6.QtWidgets import QCheckBox
        self.admin_checkbox = QCheckBox("Esegui come amministratore")
        self.admin_checkbox.setChecked(self.script.get('run_as_admin', False))
        self.admin_checkbox.setStyleSheet("""
            QCheckBox {
                color: black;
                font-size: 10pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
        """)
        layout.addWidget(self.admin_checkbox)
        
        # Codice script
        code_label = QLabel("Codice Script:")
        layout.addWidget(code_label)
        
        self.code_input = QTextEdit()
        # Carica il contenuto del file esistente
        try:
            script_path = self.script.get('path', '')
            script_file_path = Path(self.scripts_dir) / script_path
            if script_file_path.exists():
                self.code_input.setPlainText(script_file_path.read_text(encoding='utf-8'))
        except Exception:
            pass
        layout.addWidget(self.code_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)

    def get_script_info(self):
        """Ritorna le informazioni dello script aggiornate"""
        return {
            'name': self.name_input.text().strip(),
            'filename': self.filename_input.text().strip(),
            'description': self.desc_input.text().strip() or "Nessuna descrizione",
            'code': self.code_input.toPlainText().strip(),
            'division': self.division_combo.currentText(),
            'params': self.params_input.text().strip(),
            'run_as_admin': self.admin_checkbox.isChecked()
        }

    def accept(self):
        """Valida e accetta il dialog"""
        if not self.name_input.text().strip():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Inserisci un nome per lo script!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        if not self.filename_input.text().strip():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Inserisci il nome del file con estensione!")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        
        # Valida che il filename abbia un'estensione
        filename = self.filename_input.text().strip()
        if '.' not in filename:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Avviso")
            msg_box.setText("Il nome file deve includere un'estensione (es: .ps1, .py, .bat)")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: white;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            msg_box.exec()
            return
        
        super().accept()


class SettingsDialog(QDialog):
    """Dialog per modificare le impostazioni dell'applicazione"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙ Impostazioni Applicazione")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("QDialog { background-color: white; }")
        
        # Path del file config.ini - usa path assoluto dalla root del progetto
        import os
        import sys
        
        # Determina la directory base
        if getattr(sys, 'frozen', False):
            # Se è un eseguibile, usa la directory dell'eseguibile
            base_dir = Path(sys.executable).parent
        else:
            # Se è Python script, usa la directory del progetto
            base_dir = Path(__file__).parent.parent.parent
        
        self.config_path = base_dir / "config" / "config.ini"
        
        # Dizionario per tenere traccia dei campi
        self.fields = {}
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Titolo
        title = QLabel("⚙ Configurazione Applicazione")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; padding: 16px; background-color: #f5f5f5;")
        layout.addWidget(title)
        
        # Scroll area principale per tutte le sezioni
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 14px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background-color: #2196F3;
                border-radius: 7px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1976D2;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # Container per tutte le sezioni
        container = QWidget()
        container.setStyleSheet("background-color: white;")
        container_layout = QVBoxLayout()
        container_layout.setSpacing(20)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # Leggi il file config.ini (disabilita interpolazione per evitare problemi con %)
        import configparser
        config = configparser.ConfigParser(interpolation=None)
        if self.config_path.exists():
            config.read(self.config_path, encoding='utf-8')
        
        # Crea una sezione per ogni gruppo nel config
        for section in config.sections():
            section_widget = self.create_section_widget(config, section)
            container_layout.addWidget(section_widget)
        
        container.setLayout(container_layout)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Info riavvio
        info_label = QLabel("ℹ️ Alcune modifiche potrebbero richiedere il riavvio dell'applicazione")
        info_label.setStyleSheet("""
            color: #666;
            background-color: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #FF9800;
            margin: 10px;
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Bottoni
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(10, 10, 10, 10)
        
        save_button = QPushButton("💾 Salva")
        save_button.clicked.connect(self.save_settings)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        buttons_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Annulla")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def create_section_widget(self, config, section):
        """Crea un widget per una sezione del config"""
        section_widget = QWidget()
        section_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(16, 16, 16, 16)
        section_layout.setSpacing(12)
        
        # Titolo sezione
        section_title = QLabel(section.upper())
        section_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        section_title.setStyleSheet("""
            color: #2196F3;
            background-color: transparent;
            border: none;
            padding-bottom: 8px;
            border-bottom: 2px solid #2196F3;
        """)
        section_layout.addWidget(section_title)
        
        # Aggiungi i campi per ogni chiave della sezione
        for key in config[section]:
            value = config[section][key]
            
            # Container per ogni campo
            field_layout = QHBoxLayout()
            field_layout.setSpacing(12)
            
            # Label con il nome della chiave
            label = QLabel(key.replace('_', ' ').title() + ":")
            label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label.setStyleSheet("color: #333; background-color: transparent; border: none;")
            label.setMinimumWidth(200)
            label.setMaximumWidth(200)
            field_layout.addWidget(label)
            
            # Campo di input
            if value.lower() in ['true', 'false']:
                # Checkbox per booleani
                from PyQt6.QtWidgets import QCheckBox
                input_field = QCheckBox("Abilitato")
                input_field.setChecked(value.lower() == 'true')
                input_field.setStyleSheet("""
                    QCheckBox {
                        color: black;
                        spacing: 8px;
                        background-color: transparent;
                        border: none;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                        border: 2px solid #cccccc;
                        border-radius: 3px;
                        background-color: white;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #2196F3;
                        border-color: #2196F3;
                    }
                """)
                field_layout.addWidget(input_field)
                self.fields[f"{section}.{key}"] = input_field
            elif key.endswith('_color') or value.startswith('#'):
                # Input con preview colore
                input_field = QLineEdit(value)
                input_field.setPlaceholderText("#RRGGBB")
                input_field.setMaximumWidth(150)
                input_field.setStyleSheet("""
                    QLineEdit {
                        background-color: white;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        color: black;
                    }
                    QLineEdit:focus {
                        border: 2px solid #2196F3;
                    }
                """)
                
                color_preview = QLabel("   ")
                color_preview.setStyleSheet(f"background-color: {value}; border: 1px solid #ddd; border-radius: 3px;")
                color_preview.setFixedSize(30, 30)
                
                # Update preview quando cambia il valore
                def update_preview(text, preview=color_preview):
                    if text.startswith('#') and len(text) == 7:
                        preview.setStyleSheet(f"background-color: {text}; border: 1px solid #ddd; border-radius: 3px;")
                input_field.textChanged.connect(update_preview)
                
                field_layout.addWidget(input_field)
                field_layout.addWidget(color_preview)
                self.fields[f"{section}.{key}"] = input_field
            elif value.isdigit():
                # Spinbox per numeri
                from PyQt6.QtWidgets import QSpinBox
                input_field = QSpinBox()
                input_field.setRange(0, 10000)
                input_field.setValue(int(value))
                input_field.setMaximumWidth(150)
                input_field.setStyleSheet("""
                    QSpinBox {
                        background-color: white;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        color: black;
                    }
                    QSpinBox:focus {
                        border: 2px solid #2196F3;
                    }
                """)
                field_layout.addWidget(input_field)
                self.fields[f"{section}.{key}"] = input_field
            else:
                # QLineEdit per stringhe
                input_field = QLineEdit(value)
                input_field.setStyleSheet("""
                    QLineEdit {
                        background-color: white;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        color: black;
                    }
                    QLineEdit:focus {
                        border: 2px solid #2196F3;
                    }
                """)
                field_layout.addWidget(input_field)
                self.fields[f"{section}.{key}"] = input_field
            
            field_layout.addStretch()
            section_layout.addLayout(field_layout)
        
        section_widget.setLayout(section_layout)
        return section_widget
    
    def save_settings(self):
        """Salva le impostazioni nel file config.ini"""
        import configparser
        
        config = configparser.ConfigParser(interpolation=None)
        if self.config_path.exists():
            config.read(self.config_path, encoding='utf-8')
        
        # Aggiorna i valori dal form
        from PyQt6.QtWidgets import QCheckBox, QSpinBox
        for field_key, field_widget in self.fields.items():
            section, key = field_key.split('.', 1)
            
            if isinstance(field_widget, QCheckBox):
                value = 'true' if field_widget.isChecked() else 'false'
            elif isinstance(field_widget, QSpinBox):
                value = str(field_widget.value())
            else:
                value = field_widget.text().strip()
            
            if section in config:
                config[section][key] = value
                print(f"[DEBUG] Updating {section}.{key} = {value}")
        
        # Scrivi il file
        try:
            print(f"[DEBUG] Saving to: {self.config_path}")
            print(f"[DEBUG] File exists: {self.config_path.exists()}")
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print(f"[DEBUG] File saved successfully")
            
            # Messaggio di successo
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Successo")
            msg_box.setText("Impostazioni salvate con successo!")
            msg_box.setInformativeText("Le modifiche saranno applicate al prossimo riavvio dell'applicazione.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg_box.exec()
            self.accept()
            
        except Exception as e:
            # Messaggio di errore
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Errore")
            msg_box.setText(f"Errore nel salvataggio delle impostazioni:\n{str(e)}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    min-width: 80px;
                    font-weight: bold;
                }
            """)
            msg_box.exec()


class ScriptCodeViewer(QDialog):
    """Dialog per visualizzare il codice di uno script"""
    def __init__(self, title, script_path, parent=None):
        super().__init__(parent)
        from config.config import ConfigManager
        self.config = ConfigManager()
        self.setWindowTitle(f"Codice Script - {title}")
        width, height = self.config.code_viewer_dialog_size
        self.resize(width, height)

        layout = QVBoxLayout()
        
        # Leggi e visualizza il file di script
        code_text = QTextEdit()
        code_text.setReadOnly(True)
        code_text.setFont(QFont("Consolas", 10))
        code_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #333;
                padding: 10px;
            }
        """)
        
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    code_text.setPlainText(f.read())
            except Exception as e:
                code_text.setText(f"Errore nella lettura del file: {str(e)}")
        else:
            code_text.setText(f"File non trovato: {script_path}")

        layout.addWidget(code_text)

        # Bottone chiudi
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)


class WorkflowManagerDialog(QDialog):
    """Dialog principale per gestire i workflow"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.workflows = []
        self.initUI()
        self.load_workflows()
    
    def initUI(self):
        self.setWindowTitle("Gestione Workflow")
        self.resize(700, 500)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            dialog_geo = self.frameGeometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
            }
            QListWidget {
                background-color: #f9f9f9;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: black;
                font-size: 10pt;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        from PyQt6.QtWidgets import QPushButton
        
        layout = QVBoxLayout()
        
        # Titolo
        title_label = QLabel("🔄 Gestione Workflow")
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #FF9800; padding-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Descrizione
        desc_label = QLabel("I workflow permettono di eseguire più script in sequenza.\nSeleziona un workflow per modificarlo o eliminarlo.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; padding-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Lista workflow
        self.workflow_list = QListWidget()
        self.workflow_list.itemSelectionChanged.connect(self.on_workflow_selected)
        layout.addWidget(self.workflow_list)
        
        # Bottoni azione
        buttons_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("➕ Nuovo Workflow")
        self.create_btn.clicked.connect(self.create_workflow)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        buttons_layout.addWidget(self.create_btn)
        
        self.edit_btn = QPushButton("✏️ Modifica")
        self.edit_btn.clicked.connect(self.edit_workflow)
        self.edit_btn.setEnabled(False)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Elimina")
        self.delete_btn.clicked.connect(self.delete_workflow)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.delete_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Bottone chiudi
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        close_layout.addWidget(close_btn)
        
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
    
    def get_workflows_dir(self):
        """Restituisce il percorso della directory workflows"""
        import os
        import sys
        
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            workflows_dir = exe_dir / "workflows"
        else:
            base_dir = Path(__file__).parent.parent.parent
            workflows_dir = base_dir / "workflows"
        
        workflows_dir.mkdir(exist_ok=True)
        return workflows_dir
    
    def load_workflows(self):
        """Carica tutti i workflow dalla directory"""
        import json
        
        self.workflow_list.clear()
        self.workflows = []
        
        workflows_dir = self.get_workflows_dir()
        for file in workflows_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                    workflow_data['filename'] = file.name
                    self.workflows.append(workflow_data)
                    
                    # Aggiungi alla lista con formato: Nome (N script)
                    script_count = len(workflow_data.get('scripts', []))
                    item_text = f"📋 {workflow_data['name']} ({script_count} script)"
                    self.workflow_list.addItem(item_text)
            except Exception as e:
                print(f"Errore caricamento workflow {file}: {e}")
    
    def on_workflow_selected(self):
        """Abilita/disabilita bottoni in base alla selezione"""
        has_selection = len(self.workflow_list.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def create_workflow(self):
        """Apre il dialog per creare un nuovo workflow"""
        dialog = WorkflowEditorDialog(self, parent_window=self.parent_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            workflow_data = dialog.get_workflow_data()
            if workflow_data:
                self.save_workflow(workflow_data)
                self.load_workflows()
    
    def edit_workflow(self):
        """Apre il dialog per modificare il workflow selezionato"""
        selected_index = self.workflow_list.currentRow()
        if 0 <= selected_index < len(self.workflows):
            workflow_data = self.workflows[selected_index]
            dialog = WorkflowEditorDialog(self, existing_workflow=workflow_data, parent_window=self.parent_window)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_data = dialog.get_workflow_data()
                if new_data:
                    # Elimina il vecchio file se il nome è cambiato
                    if workflow_data.get('filename'):
                        old_file = self.get_workflows_dir() / workflow_data['filename']
                        if old_file.exists() and new_data['name'] != workflow_data['name']:
                            old_file.unlink()
                    
                    self.save_workflow(new_data)
                    self.load_workflows()
    
    def delete_workflow(self):
        """Elimina il workflow selezionato"""
        selected_index = self.workflow_list.currentRow()
        if 0 <= selected_index < len(self.workflows):
            from PyQt6.QtWidgets import QMessageBox
            
            workflow_data = self.workflows[selected_index]
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Conferma")
            msg.setText(f"Eliminare il workflow '{workflow_data['name']}'?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            reply = msg.exec()
            
            if reply == QMessageBox.StandardButton.Yes:
                if workflow_data.get('filename'):
                    file_path = self.get_workflows_dir() / workflow_data['filename']
                    if file_path.exists():
                        file_path.unlink()
                        self.load_workflows()
    
    def save_workflow(self, workflow_data):
        """Salva il workflow su file JSON"""
        import json
        
        safe_name = workflow_data['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{safe_name}.json"
        filepath = self.get_workflows_dir() / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Errore", f"Impossibile salvare il workflow:\n{e}")


class WorkflowEditorDialog(QDialog):
    """Dialog per creare/modificare un workflow"""
    def __init__(self, parent=None, existing_workflow=None, parent_window=None):
        super().__init__(parent)
        self.existing_workflow = existing_workflow
        self.parent_window = parent_window
        self.workflow_data = None
        self.selected_scripts = []
        self.initUI()
        
        if existing_workflow:
            self.load_existing_workflow()
    
    def initUI(self):
        self.setWindowTitle("Editor Workflow")
        self.resize(900, 600)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            dialog_geo = self.frameGeometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
            }
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #FF9800;
                background-color: white;
            }
            QListWidget {
                background-color: #f9f9f9;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: black;
                font-size: 10pt;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #FF9800;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #FFE0B2;
            }
        """)
        
        from PyQt6.QtWidgets import QPushButton
        
        layout = QVBoxLayout()
        
        # Titolo
        title = "✏️ Modifica Workflow" if self.existing_workflow else "➕ Nuovo Workflow"
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #FF9800; padding-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Nome workflow
        name_label = QLabel("Nome Workflow:")
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Inserisci un nome per il workflow...")
        layout.addWidget(self.name_input)
        
        # Layout orizzontale per liste
        lists_layout = QHBoxLayout()
        
        # Lista script disponibili (sinistra)
        left_panel = QVBoxLayout()
        available_label = QLabel("📚 Script Disponibili")
        available_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        left_panel.addWidget(available_label)
        
        self.available_list = QListWidget()
        self.available_list.itemDoubleClicked.connect(self.add_script_to_workflow)
        left_panel.addWidget(self.available_list)
        
        lists_layout.addLayout(left_panel, 1)
        
        # Bottoni centrali
        center_buttons = QVBoxLayout()
        center_buttons.addStretch()
        
        add_btn = QPushButton("▶")
        add_btn.setMaximumWidth(50)
        add_btn.clicked.connect(self.add_script_to_workflow)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 4px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        center_buttons.addWidget(add_btn)
        
        remove_btn = QPushButton("◀")
        remove_btn.setMaximumWidth(50)
        remove_btn.clicked.connect(self.remove_script_from_workflow)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 4px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        center_buttons.addWidget(remove_btn)
        
        center_buttons.addStretch()
        lists_layout.addLayout(center_buttons)
        
        # Lista script nel workflow (destra)
        right_panel = QVBoxLayout()
        workflow_label = QLabel("🔄 Script nel Workflow")
        workflow_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        right_panel.addWidget(workflow_label)
        
        self.workflow_list = QListWidget()
        right_panel.addWidget(self.workflow_list)
        
        # Bottoni ordinamento
        order_buttons = QHBoxLayout()
        
        up_btn = QPushButton("⬆ Su")
        up_btn.clicked.connect(self.move_script_up)
        up_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        order_buttons.addWidget(up_btn)
        
        down_btn = QPushButton("⬇ Giù")
        down_btn.clicked.connect(self.move_script_down)
        down_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        order_buttons.addWidget(down_btn)
        
        right_panel.addLayout(order_buttons)
        lists_layout.addLayout(right_panel, 1)
        
        layout.addLayout(lists_layout)
        
        # Bottoni finali
        final_buttons = QHBoxLayout()
        final_buttons.addStretch()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        final_buttons.addWidget(cancel_btn)
        
        save_btn = QPushButton("Salva")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        final_buttons.addWidget(save_btn)
        
        layout.addLayout(final_buttons)
        
        self.setLayout(layout)
        
        # Carica gli script disponibili
        self.load_available_scripts()
    
    def load_available_scripts(self):
        """Carica tutti gli script disponibili dall'applicazione"""
        if not self.parent_window or not hasattr(self.parent_window, 'repository'):
            return
        
        all_scripts = self.parent_window.repository.get_all_scripts()
        
        for script in all_scripts:
            script_name = script.get('name', 'Unknown')
            category = script.get('category', 'N/A')
            item_text = f"{script_name} ({category})"
            self.available_list.addItem(item_text)
    
    def load_existing_workflow(self):
        """Carica i dati di un workflow esistente"""
        if not self.existing_workflow:
            return
        
        self.name_input.setText(self.existing_workflow.get('name', ''))
        
        # Carica gli script nel workflow
        for script_info in self.existing_workflow.get('scripts', []):
            self.workflow_list.addItem(script_info)
            self.selected_scripts.append(script_info)
    
    def add_script_to_workflow(self):
        """Aggiunge uno script al workflow"""
        selected_items = self.available_list.selectedItems()
        if selected_items:
            script_text = selected_items[0].text()
            if script_text not in self.selected_scripts:
                self.workflow_list.addItem(script_text)
                self.selected_scripts.append(script_text)
    
    def remove_script_from_workflow(self):
        """Rimuove uno script dal workflow"""
        selected_items = self.workflow_list.selectedItems()
        if selected_items:
            for item in selected_items:
                script_text = item.text()
                row = self.workflow_list.row(item)
                self.workflow_list.takeItem(row)
                if script_text in self.selected_scripts:
                    self.selected_scripts.remove(script_text)
    
    def move_script_up(self):
        """Sposta lo script selezionato verso l'alto"""
        current_row = self.workflow_list.currentRow()
        if current_row > 0:
            item = self.workflow_list.takeItem(current_row)
            self.workflow_list.insertItem(current_row - 1, item)
            self.workflow_list.setCurrentRow(current_row - 1)
            
            # Aggiorna la lista interna
            self.selected_scripts[current_row], self.selected_scripts[current_row - 1] = \
                self.selected_scripts[current_row - 1], self.selected_scripts[current_row]
    
    def move_script_down(self):
        """Sposta lo script selezionato verso il basso"""
        current_row = self.workflow_list.currentRow()
        if current_row < self.workflow_list.count() - 1:
            item = self.workflow_list.takeItem(current_row)
            self.workflow_list.insertItem(current_row + 1, item)
            self.workflow_list.setCurrentRow(current_row + 1)
            
            # Aggiorna la lista interna
            self.selected_scripts[current_row], self.selected_scripts[current_row + 1] = \
                self.selected_scripts[current_row + 1], self.selected_scripts[current_row]
    
    def accept(self):
        """Valida e salva il workflow"""
        name = self.name_input.text().strip()
        
        if not name:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Attenzione")
            msg.setText("Inserisci un nome per il workflow!")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            msg.exec()
            return
        
        if not self.selected_scripts:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Attenzione")
            msg.setText("Aggiungi almeno uno script al workflow!")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            msg.exec()
            return
        
        # Aggiorna la lista degli script dal QListWidget per mantenere l'ordine corrente
        self.selected_scripts = [self.workflow_list.item(i).text() for i in range(self.workflow_list.count())]
        
        self.workflow_data = {
            'name': name,
            'scripts': self.selected_scripts
        }
        
        super().accept()
    
    def get_workflow_data(self):
        """Restituisce i dati del workflow"""
        return self.workflow_data


class EmailConfigDialog(QDialog):
    """Dialog per configurare l'invio email al termine dell'esecuzione"""
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config = config_manager
        self.email_config = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Configura Notifica Email")
        self.resize(600, 500)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            dialog_geo = self.frameGeometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
            }
            QLineEdit, QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QCheckBox {
                color: black;
                font-size: 10pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Titolo
        title_label = QLabel("Configura report email al termine dell'esecuzione")
        title_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #2196F3; padding-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Destinatari
        recipients_label = QLabel("Destinatari (separati da virgola):")
        recipients_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(recipients_label)
        
        self.recipients_input = QLineEdit()
        # Placeholder con valori di esempio dal config
        placeholder_recipients = "email1@example.com, email2@example.com"
        if self.config and self.config.default_recipients:
            placeholder_recipients = ", ".join(self.config.default_recipients)
        self.recipients_input.setPlaceholderText(placeholder_recipients)
        layout.addWidget(self.recipients_input)
        
        # Oggetto
        subject_label = QLabel("Oggetto:")
        subject_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(subject_label)
        
        self.subject_input = QLineEdit()
        # Placeholder con valore dal config
        placeholder_subject = "[SYS Toolset] Esecuzione script"
        if self.config:
            placeholder_subject = self.config.default_email_subject
        self.subject_input.setPlaceholderText(placeholder_subject)
        layout.addWidget(self.subject_input)
        
        # Info sui placeholder
        info_label = QLabel("💡 Puoi usare: {script_name}, {date}, {time}, {status}, {output}")
        info_label.setStyleSheet("color: #666; font-size: 9pt; font-style: italic;")
        layout.addWidget(info_label)
        
        # Corpo
        body_label = QLabel("Corpo del messaggio:")
        body_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(body_label)
        
        self.body_input = QTextEdit()
        # Placeholder con valore dal config
        placeholder_body = "Report di esecuzione:\n\n{output}"
        if self.config:
            placeholder_body = self.config.default_email_body
        self.body_input.setPlaceholderText(placeholder_body)
        self.body_input.setMaximumHeight(150)
        layout.addWidget(self.body_input)
        
        # Info configurazione SMTP
        info_box = QLabel()
        if self.config and self.config.sender_email:
            info_box.setText(f"📧 Mittente configurato: {self.config.sender_email}\n"
                           f"🖥️ Server SMTP: {self.config.smtp_server}:{self.config.smtp_port}")
        else:
            info_box.setText("⚠️ Configurazione SMTP non trovata in config.ini")
        info_box.setStyleSheet("""
            background-color: #E3F2FD;
            border: 1px solid #2196F3;
            border-radius: 4px;
            padding: 10px;
            color: #333;
            font-size: 9pt;
        """)
        layout.addWidget(info_box)
        
        layout.addStretch()
        
        # Bottoni
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _validate_email(self, email):
        """Valida formato email base"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def accept(self):
        """Salva la configurazione email"""
        recipients_text = self.recipients_input.text().strip()
        
        # Se il campo è vuoto, mostra warning
        if not recipients_text:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Campo obbligatorio")
            msg.setText("Il campo destinatari è vuoto!")
            msg.setInformativeText("Inserisci almeno un indirizzo email o premi Cancel per annullare.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg.exec()
            return  # Non chiudere il dialog
        
        # Separa i destinatari
        recipients = [r.strip() for r in recipients_text.split(',') if r.strip()]
        
        # Valida ogni email
        invalid_emails = []
        for email in recipients:
            if not self._validate_email(email):
                invalid_emails.append(email)
        
        # Se ci sono email non valide, mostra errore
        if invalid_emails:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Email non valide")
            msg.setText(f"Le seguenti email non sono valide:\n\n{', '.join(invalid_emails)}")
            msg.setInformativeText("Correggi gli indirizzi email e riprova.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg.exec()
            return  # Non chiudere il dialog
        
        # Se tutto ok, salva la configurazione
        self.email_config = {
            'enabled': True,
            'recipients': recipients,
            'subject': self.subject_input.text(),
            'body': self.body_input.toPlainText()
        }
        
        super().accept()


class ScheduleDialog(QDialog):
    """Dialog per schedulare l'esecuzione automatica di uno script"""
    def __init__(self, parent=None, script_name="", existing_config=None):
        super().__init__(parent)
        self.script_name = script_name
        self.existing_config = existing_config
        self.schedule_config = None
        self.triggers = existing_config.get('triggers', []) if existing_config else []
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle(f"Schedula Script - {self.script_name}")
        self.resize(900, 550)
        
        # Centra rispetto al parent
        if self.parent():
            parent_geo = self.parent().frameGeometry()
            dialog_geo = self.frameGeometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
            }
            QLineEdit, QComboBox, QSpinBox, QTimeEdit, QDateTimeEdit {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px;
                color: black;
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QDateTimeEdit:focus {
                border: 2px solid #2196F3;
                background-color: white;
            }
            QCheckBox {
                color: black;
                font-size: 10pt;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            QRadioButton {
                color: black;
                font-size: 10pt;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #cccccc;
                border-radius: 8px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            QListWidget {
                background-color: #f9f9f9;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: black;
                font-size: 10pt;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        from PyQt6.QtWidgets import QRadioButton, QTimeEdit, QSpinBox, QGroupBox, QDateTimeEdit, QListWidget, QPushButton
        from PyQt6.QtCore import QTime, QDateTime
        
        main_layout = QVBoxLayout()
        
        # Titolo
        title_label = QLabel("⏰ Configura schedulazione automatica")
        title_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #2196F3; padding-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Nome task
        task_name_label = QLabel("Nome attività:")
        task_name_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(task_name_label)
        
        self.task_name_input = QLineEdit()
        default_name = f"SYS_Toolset_{self.script_name.replace(' ', '_')}"
        if self.existing_config:
            self.task_name_input.setText(self.existing_config.get('task_name', default_name))
        else:
            self.task_name_input.setText(default_name)
        self.task_name_input.setPlaceholderText("Nome univoco per l'attività pianificata")
        main_layout.addWidget(self.task_name_input)
        
        # Layout orizzontale: lista trigger a sinistra, form a destra
        h_layout = QHBoxLayout()
        
        # === PANNELLO SINISTRO: Lista Trigger ===
        left_panel = QVBoxLayout()
        
        triggers_label = QLabel("Trigger configurati:")
        triggers_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        left_panel.addWidget(triggers_label)
        
        self.triggers_list = QListWidget()
        self.triggers_list.setMinimumWidth(250)
        self.triggers_list.itemSelectionChanged.connect(self.on_trigger_selected)
        left_panel.addWidget(self.triggers_list)
        
        # Bottoni gestione trigger (sinistra)
        trigger_buttons_layout = QVBoxLayout()
        
        self.add_trigger_btn = QPushButton("➕ Nuovo Trigger")
        self.add_trigger_btn.clicked.connect(self.add_trigger)
        self.add_trigger_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        trigger_buttons_layout.addWidget(self.add_trigger_btn)
        
        self.delete_trigger_btn = QPushButton("🗑️ Elimina Trigger")
        self.delete_trigger_btn.clicked.connect(self.delete_trigger)
        self.delete_trigger_btn.setEnabled(False)
        self.delete_trigger_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        trigger_buttons_layout.addWidget(self.delete_trigger_btn)
        
        left_panel.addLayout(trigger_buttons_layout)
        h_layout.addLayout(left_panel, 1)
        
        # === PANNELLO DESTRO: Form Trigger ===
        right_panel = QVBoxLayout()
        
        form_label = QLabel("Dettagli trigger:")
        form_label.setStyleSheet("font-weight: bold; padding-top: 10px;")
        right_panel.addWidget(form_label)
        
        # Tipo di schedulazione
        schedule_type_group = QGroupBox("Tipo di schedulazione")
        schedule_type_layout = QHBoxLayout()
        
        self.once_radio = QRadioButton("Una volta")
        self.once_radio.setChecked(True)
        self.once_radio.toggled.connect(self.on_schedule_type_changed)
        schedule_type_layout.addWidget(self.once_radio)
        
        self.daily_radio = QRadioButton("Giornaliera")
        self.daily_radio.toggled.connect(self.on_schedule_type_changed)
        schedule_type_layout.addWidget(self.daily_radio)
        
        self.weekly_radio = QRadioButton("Settimanale")
        self.weekly_radio.toggled.connect(self.on_schedule_type_changed)
        schedule_type_layout.addWidget(self.weekly_radio)
        
        schedule_type_group.setLayout(schedule_type_layout)
        right_panel.addWidget(schedule_type_group)
        
        # Data e ora
        datetime_group = QGroupBox("Data e ora esecuzione")
        datetime_layout = QVBoxLayout()
        
        # Data (solo per "una volta")
        self.date_label = QLabel("Data e ora:")
        self.date_label.setStyleSheet("font-weight: bold;")
        datetime_layout.addWidget(self.date_label)
        
        self.date_edit = QDateTimeEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        self.date_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        datetime_layout.addWidget(self.date_edit)
        
        # Ora (per ricorrenze)
        self.time_label = QLabel("Ora:")
        self.time_label.setStyleSheet("font-weight: bold;")
        self.time_label.setVisible(False)
        datetime_layout.addWidget(self.time_label)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setVisible(False)
        datetime_layout.addWidget(self.time_edit)
        
        datetime_group.setLayout(datetime_layout)
        right_panel.addWidget(datetime_group)
        
        # Giorni settimana (solo per settimanale)
        self.weekdays_group = QGroupBox("Giorni della settimana")
        weekdays_layout = QHBoxLayout()
        
        self.weekday_checkboxes = {}
        weekdays = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        weekdays_full = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        for short, full in zip(weekdays, weekdays_full):
            cb = QCheckBox(short)
            cb.setToolTip(full)
            self.weekday_checkboxes[full] = cb
            weekdays_layout.addWidget(cb)
        
        self.weekdays_group.setLayout(weekdays_layout)
        self.weekdays_group.setVisible(False)
        right_panel.addWidget(self.weekdays_group)
        
        # Intervallo giornaliero
        self.daily_group = QGroupBox("Ripeti ogni")
        daily_layout = QHBoxLayout()
        
        self.daily_interval = QSpinBox()
        self.daily_interval.setMinimum(1)
        self.daily_interval.setMaximum(365)
        self.daily_interval.setValue(1)
        daily_layout.addWidget(self.daily_interval)
        
        daily_label = QLabel("giorno/i")
        daily_layout.addWidget(daily_label)
        daily_layout.addStretch()
        
        self.daily_group.setLayout(daily_layout)
        self.daily_group.setVisible(False)
        right_panel.addWidget(self.daily_group)
        
        right_panel.addStretch()
        h_layout.addLayout(right_panel, 2)
        
        main_layout.addLayout(h_layout)
        
        # Bottoni finali
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        buttons_layout.addWidget(cancel_btn)
        
        self.delete_all_btn = QPushButton("Elimina Tutto")
        self.delete_all_btn.clicked.connect(self.delete_all_triggers)
        self.delete_all_btn.setVisible(self.existing_config is not None)
        self.delete_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        buttons_layout.addWidget(self.delete_all_btn)
        
        save_btn = QPushButton("Salva")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        buttons_layout.addWidget(save_btn)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        
        # Carica trigger esistenti
        self.refresh_triggers_list()
        
        # Variabile per editing
        self.editing_trigger_index = None
    
    def refresh_triggers_list(self):
        """Aggiorna la lista dei trigger visualizzati"""
        self.triggers_list.clear()
        for trigger in self.triggers:
            summary = self.get_trigger_summary(trigger)
            self.triggers_list.addItem(summary)
    
    def get_trigger_summary(self, trigger):
        """Genera un riassunto testuale del trigger"""
        trigger_type = trigger['type']
        data = trigger['data']
        
        if trigger_type == 'once':
            return f"📅 Una volta: {data['datetime']}"
        elif trigger_type == 'daily':
            interval = data.get('interval', 1)
            if interval == 1:
                return f"🔄 Giornaliera: {data['time']}"
            else:
                return f"🔄 Ogni {interval} giorni: {data['time']}"
        elif trigger_type == 'weekly':
            days_short = {'Lunedì': 'Lun', 'Martedì': 'Mar', 'Mercoledì': 'Mer', 
                         'Giovedì': 'Gio', 'Venerdì': 'Ven', 'Sabato': 'Sab', 'Domenica': 'Dom'}
            days = ', '.join([days_short.get(d, d) for d in data['days']])
            return f"📆 Settimanale: {days} - {data['time']}"
        return "❓ Sconosciuto"
    
    def on_trigger_selected(self):
        """Gestisce la selezione di un trigger dalla lista"""
        selected_items = self.triggers_list.selectedItems()
        if selected_items:
            self.delete_trigger_btn.setEnabled(True)
            # Carica il trigger selezionato nel form
            selected_index = self.triggers_list.currentRow()
            if 0 <= selected_index < len(self.triggers):
                self.editing_trigger_index = selected_index
                self.load_trigger_into_form(self.triggers[selected_index])
                # Cambia testo bottone in modalità editing
                self.add_trigger_btn.setText("💾 Salva Modifiche")
        else:
            self.delete_trigger_btn.setEnabled(False)
            self.editing_trigger_index = None
            self.add_trigger_btn.setText("➕ Nuovo Trigger")
    
    def load_trigger_into_form(self, trigger):
        """Carica i dati di un trigger nel form"""
        from PyQt6.QtCore import QTime, QDateTime
        
        trigger_type = trigger['type']
        data = trigger['data']
        
        if trigger_type == 'once':
            self.once_radio.setChecked(True)
            datetime_str = data['datetime']
            dt = QDateTime.fromString(datetime_str, "dd/MM/yyyy HH:mm")
            self.date_edit.setDateTime(dt)
        elif trigger_type == 'daily':
            self.daily_radio.setChecked(True)
            time_str = data['time']
            time = QTime.fromString(time_str, "HH:mm")
            self.time_edit.setTime(time)
            self.daily_interval.setValue(data.get('interval', 1))
        elif trigger_type == 'weekly':
            self.weekly_radio.setChecked(True)
            time_str = data['time']
            time = QTime.fromString(time_str, "HH:mm")
            self.time_edit.setTime(time)
            # Reset weekdays
            for cb in self.weekday_checkboxes.values():
                cb.setChecked(False)
            # Set selected days
            for day in data['days']:
                if day in self.weekday_checkboxes:
                    self.weekday_checkboxes[day].setChecked(True)

    
    def add_trigger(self):
        """Aggiunge un nuovo trigger alla lista"""
        # Valida il form
        trigger = self.get_current_form_trigger()
        if trigger is None:
            return  # Validazione fallita
        
        if self.editing_trigger_index is not None:
            # Modalità editing: aggiorna il trigger esistente
            self.triggers[self.editing_trigger_index] = trigger
            self.editing_trigger_index = None
            self.add_trigger_btn.setText("➕ Nuovo Trigger")
        else:
            # Modalità inserimento: aggiungi nuovo trigger
            self.triggers.append(trigger)
        
        self.refresh_triggers_list()
        self.clear_form()
        self.triggers_list.clearSelection()
        self.delete_trigger_btn.setEnabled(False)
    
    def delete_trigger(self):
        """Elimina il trigger selezionato"""
        selected_index = self.triggers_list.currentRow()
        if 0 <= selected_index < len(self.triggers):
            from PyQt6.QtWidgets import QMessageBox
            
            # Ottieni il riepilogo del trigger prima di eliminarlo
            trigger_summary = self.get_trigger_summary(self.triggers[selected_index])
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Conferma")
            msg.setText(f"Eliminare questo trigger?\n\n{trigger_summary}")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            reply = msg.exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.triggers.pop(selected_index)
                self.refresh_triggers_list()
                self.clear_form()
                self.editing_trigger_index = None
                
                # Mostra messaggio nel parent se disponibile
                if self.parent() and hasattr(self.parent(), 'output_text'):
                    self.parent().output_text.append(f"🗑️ Trigger eliminato: {trigger_summary}")
    
    def delete_all_triggers(self):
        """Elimina tutti i trigger e la configurazione"""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Conferma")
        msg.setText("Eliminare TUTTA la schedulazione?\nQuesta azione è irreversibile.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QLabel {
                color: black;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self.triggers.clear()
            self.schedule_config = {'delete_all': True}
            super().accept()
    
    def clear_form(self):
        """Pulisce il form per un nuovo inserimento"""
        from PyQt6.QtCore import QTime, QDateTime
        
        self.once_radio.setChecked(True)
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        self.time_edit.setTime(QTime.currentTime())
        self.daily_interval.setValue(1)
        for cb in self.weekday_checkboxes.values():
            cb.setChecked(False)
        self.editing_trigger_index = None
        self.add_trigger_btn.setText("➕ Nuovo Trigger")
    
    def get_current_form_trigger(self):
        """Estrae il trigger dal form corrente con validazione"""
        from PyQt6.QtWidgets import QMessageBox
        
        if self.once_radio.isChecked():
            return {
                'type': 'once',
                'data': {
                    'datetime': self.date_edit.dateTime().toString("dd/MM/yyyy HH:mm")
                }
            }
        elif self.daily_radio.isChecked():
            return {
                'type': 'daily',
                'data': {
                    'time': self.time_edit.time().toString("HH:mm"),
                    'interval': self.daily_interval.value()
                }
            }
        elif self.weekly_radio.isChecked():
            selected_days = [day for day, cb in self.weekday_checkboxes.items() if cb.isChecked()]
            if not selected_days:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Attenzione")
                msg.setText("Seleziona almeno un giorno della settimana!")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: white;
                    }
                    QLabel {
                        color: black;
                        font-size: 10pt;
                    }
                    QPushButton {
                        background-color: #2196F3;
                        color: white;
                        padding: 6px 16px;
                        border: none;
                        border-radius: 4px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #1976D2;
                    }
                """)
                msg.exec()
                return None
            return {
                'type': 'weekly',
                'data': {
                    'time': self.time_edit.time().toString("HH:mm"),
                    'days': selected_days
                }
            }
        return None
    
    def on_schedule_type_changed(self):
        """Aggiorna la UI in base al tipo di schedulazione"""
        if self.once_radio.isChecked():
            self.date_label.setVisible(True)
            self.date_edit.setVisible(True)
            self.time_label.setVisible(False)
            self.time_edit.setVisible(False)
            self.weekdays_group.setVisible(False)
            self.daily_group.setVisible(False)
        elif self.daily_radio.isChecked():
            self.date_label.setVisible(False)
            self.date_edit.setVisible(False)
            self.time_label.setVisible(True)
            self.time_edit.setVisible(True)
            self.weekdays_group.setVisible(False)
            self.daily_group.setVisible(True)
        elif self.weekly_radio.isChecked():
            self.date_label.setVisible(False)
            self.date_edit.setVisible(False)
            self.time_label.setVisible(True)
            self.time_edit.setVisible(True)
            self.weekdays_group.setVisible(True)
            self.daily_group.setVisible(False)
    
    def accept(self):
        """Salva la configurazione di scheduling"""
        task_name = self.task_name_input.text().strip()
        
        if not task_name:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Attenzione")
            msg.setText("Inserisci un nome per l'attività!")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg.exec()
            return
        
        # Se non ci sono trigger, elimina la configurazione
        if not self.triggers:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Conferma")
            msg.setText("Non ci sono trigger configurati.\nVuoi eliminare la schedulazione per questo script?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                    font-size: 10pt;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            reply = msg.exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.schedule_config = {'delete_all': True}
                super().accept()
            return
        
        self.schedule_config = {
            'enabled': True,
            'task_name': task_name,
            'triggers': self.triggers
        }
        
        super().accept()
