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
    QLineEdit, QComboBox
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

    def __init__(self, script_path, log_file_path=None):
        super().__init__()
        self.script_path = script_path
        self.log_file_path = log_file_path

    def run(self):
        try:
            # Opzioni per nascondere la finestra della console
            startupinfo = None
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            if self.script_path.endswith(".ps1"):
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", self.script_path],
                    capture_output=True, text=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            elif self.script_path.endswith(".bat") or self.script_path.endswith(".cmd"):
                result = subprocess.run(
                    self.script_path, 
                    capture_output=True, text=True, shell=True, 
                    startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            elif self.script_path.endswith(".py"):
                result = subprocess.run(
                    ["python", self.script_path], 
                    capture_output=True, text=True,
                    startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            else:
                self.error_signal.emit(f"Tipo di script non supportato: {self.script_path}")
                self.finished_signal.emit()
                return

            if result.stdout:
                self.output_signal.emit(result.stdout)
                if self.log_file_path:
                    self._write_to_log(result.stdout)
            if result.stderr:
                self.error_signal.emit(result.stderr)
                if self.log_file_path:
                    self._write_to_log(f"[ERRORE] {result.stderr}")

        except Exception as e:
            error_msg = f"Errore nell'esecuzione dello script: {str(e)}"
            self.error_signal.emit(error_msg)
            if self.log_file_path:
                self._write_to_log(f"[ERRORE] {error_msg}")
        finally:
            self.finished_signal.emit()
    
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
        self.setWindowTitle(f"Documentazione - {title}")
        self.setGeometry(100, 100, 700, 500)

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
    
    def _style_messagebox(self, msg_box):
        """Applica lo stile uniforme a tutti i QMessageBox"""
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
        self.add_module_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setMaximumWidth(80)
        self.refresh_button.setMaximumHeight(28)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        toolbar.addWidget(self.add_module_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # Progress bar (nascosta di default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setStyleSheet("QProgressBar { border: none; background-color: #f0f0f0; } QProgressBar::chunk { background-color: #2196F3; }")
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

        # Nome script
        self.script_name_label = QLabel("Seleziona uno script")
        self.script_name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.script_name_label.setStyleSheet("color: #2196F3;")
        right_layout.addWidget(self.script_name_label)

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
        self.view_code_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
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

        # Applica stili
        self.apply_styles()

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
                
                # Etichetta divisione (LED/LHD) con colori pastello
                division = script.get('division', 'LED')
                division_label = QLabel(division)
                if division == 'LED':
                    bg_color = '#B3E5FC'  # Azzurro pastello
                    text_color = '#01579B'  # Blu scuro
                else:  # LHD
                    bg_color = '#C8E6C9'  # Verde pastello
                    text_color = '#1B5E20'  # Verde scuro
                
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
            self.output_text.clear()

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
        self.executor_thread = ScriptExecutorThread(script_path, str(script_log_file) if script_log_file else None)
        self.executor_thread.output_signal.connect(self.append_output)
        self.executor_thread.error_signal.connect(self.append_error)
        self.executor_thread.finished_signal.connect(self.on_execution_finished)
        self.executor_thread.start()

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
        
        # Resetta selezione
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

        # Costruisci il percorso del file MD
        doc_filename = self.current_script['name'].replace(" ", "_").lower() + ".md"
        doc_path = self.config.docs_dir / self.current_category.lower() / doc_filename

        # Fallback se il percorso non esiste
        if not doc_path.exists():
            doc_path = self.config.docs_dir / f"{self.current_script['name']}.md"

        dialog = DocumentationViewer(self.current_script['name'], str(doc_path), self)
        dialog.exec()
    
    def show_script_code(self):
        """Mostra il contenuto del file di script selezionato"""
        if not self.current_script:
            return
        
        from pathlib import Path
        
        # Costruisci il percorso del file script
        script_path = self.current_script.get('path', '')
        script_file_path = Path(self.config.scripts_dir) / script_path
        
        if not script_file_path.exists():
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
        dialog.exec()
    
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
            
            old_script_path = scripts_dir / old_script['path']
            new_script_path = category_dir / new_script_info['filename']
            
            # Normalizza i path per il confronto
            old_script_path = old_script_path.resolve()
            new_script_path = new_script_path.resolve()
            
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
                                "params": s.get('params', []),
                                "division": new_script_info.get('division', 'LED')
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
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Aggiungi Nuovo Modulo")
        self.setGeometry(100, 100, 750, 220)
        
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
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Aggiungi Nuovo Script")
        self.setGeometry(100, 100, 750, 560)
        
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
        self.division_combo.addItems(["LED", "LHD"])
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
        self.code_input.setMinimumHeight(200)
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
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Modifica Script")
        self.setGeometry(100, 100, 750, 600)
        
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
        # Estrai il filename dal path
        script_path = self.script.get('path', '')
        filename = script_path.split('/')[-1] if '/' in script_path else script_path
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
        self.division_combo.addItems(["LED", "LHD"])
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
        
        # Codice script
        code_label = QLabel("Codice Script:")
        layout.addWidget(code_label)
        
        self.code_input = QTextEdit()
        # Carica il contenuto del file esistente
        try:
            from pathlib import Path
            script_file_path = Path(self.scripts_dir) / script_path
            if script_file_path.exists():
                self.code_input.setPlainText(script_file_path.read_text(encoding='utf-8'))
        except Exception:
            pass
        self.code_input.setMinimumHeight(250)
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


class ScriptCodeViewer(QDialog):
    """Dialog per visualizzare il codice di uno script"""
    def __init__(self, title, script_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Codice Script - {title}")
        self.setGeometry(100, 100, 900, 600)

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
