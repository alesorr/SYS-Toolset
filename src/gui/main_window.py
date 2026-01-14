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
    QLineEdit
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

    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path

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
            if result.stderr:
                self.error_signal.emit(result.stderr)

        except Exception as e:
            self.error_signal.emit(f"Errore nell'esecuzione dello script: {str(e)}")
        finally:
            self.finished_signal.emit()


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
            self.update_scripts_list()

    def update_scripts_list(self):
        """Aggiorna la lista degli script in base alla categoria selezionata"""
        self.scripts_list.clear()
        self.output_text.clear()
        self.script_name_label.setText("Seleziona uno script")
        self.description_label.setText("")
        self.exec_button.setEnabled(False)
        self.doc_button.setEnabled(False)
        self.current_script = None

        if self.current_category:
            scripts = self.repository.get_scripts_by_category(self.current_category)
            for script in scripts:
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
                layout.addStretch()
                
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
            self.script_name_label.setText(f"🔧 {self.current_script['name']}")
            self.description_label.setText(self.current_script['description'])
            self.exec_button.setEnabled(True)
            self.doc_button.setEnabled(True)
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
        
        # Log esecuzione script in logs/script_executions.log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_dir = self.config.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        execution_log_file = log_dir / "script_executions.log"
        try:
            with open(execution_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] MODULO: {module_name} | SCRIPT: {script_name} | PATH: {script_path}\n")
            logger.info(f"Execution logged to {execution_log_file}: Module='{module_name}', Script='{script_name}'")
        except Exception as e:
            logger.error(f"Failed to write execution log: {e}")

        self.output_text.clear()
        self.output_text.setText(f"⏳ Esecuzione in corso: {self.current_script['name']}...\n")
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
        self.executor_thread = ScriptExecutorThread(script_path)
        self.executor_thread.output_signal.connect(self.append_output)
        self.executor_thread.error_signal.connect(self.append_error)
        self.executor_thread.finished_signal.connect(self.on_execution_finished)
        self.executor_thread.start()

    def append_output(self, text):
        """Aggiunge output al text area"""
        self.output_text.append(text)

    def append_error(self, text):
        """Aggiunge errore al text area con styling"""
        self.output_text.append(f"[ERRORE] {text}")

    def on_execution_finished(self):
        """Gestisce la fine dell'esecuzione dello script"""
        self.output_text.append("\n[OK] Esecuzione completata")
        self.exec_button.setEnabled(True)

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
            QMessageBox.warning(self, "Avviso", "Seleziona prima una categoria!")
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
        
        # Applica stile professionale: sfondo bianco, testi neri
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: black;
                background-color: white;
            }
            QPushButton {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_script(script)

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
                QMessageBox.warning(self, "Errore", f"Il file '{script_info['filename']}' esiste già!")
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
                "params": []
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
            QMessageBox.critical(self, "Errore", error_msg)

    def delete_script(self, script):
        """Cancella un file di script e aggiorna index.json"""
        from utils.logger import logger
        
        try:
            scripts_dir = Path(self.config.scripts_dir).resolve()
            
            # Trova e cancella il file
            script_path = scripts_dir / script['path']
            if script_path.exists():
                script_path.unlink()
                logger.info(f"Script file deleted: {script_path}")
            
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
            QMessageBox.critical(self, "Errore", error_msg)

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
            QMessageBox.critical(self, "Errore", error_msg)


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
            QMessageBox.warning(self, "Avviso", "Inserisci un nome per il modulo!")
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
            'code': self.code_input.toPlainText().strip()
        }

    def accept(self):
        """Valida e accetta il dialog"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Avviso", "Inserisci un nome per lo script!")
            return
        if not self.filename_input.text().strip():
            QMessageBox.warning(self, "Avviso", "Inserisci il nome del file con estensione!")
            return
        
        # Valida che il filename abbia un'estensione
        filename = self.filename_input.text().strip()
        if '.' not in filename:
            QMessageBox.warning(self, "Avviso", "Il nome file deve includere un'estensione (es: .ps1, .py, .bat)")
            return
        
        super().accept()