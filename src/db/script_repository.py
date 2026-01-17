"""
============================================================
 File: script_repository.py
 Author: Internal Systems Automation Team
 Created: 2025-01-10
 Last Updated: 2026-01-13

 Description:
     Questo modulo gestisce il caricamento degli script
     disponibili tramite file index.json. Fornisce accesso
     strutturato a categorie e script, astrando completamente
     da filesystem e struttura fisica delle cartelle.
============================================================
"""

import json
from pathlib import Path
from utils.logger import logger


class ScriptRepository:
    def __init__(self, base_path="scripts", scan_folders=False):
        self.base_path = Path(base_path)
        logger.debug(f"ScriptRepository init: base_path={self.base_path}, scan_folders={scan_folders}")
        logger.debug(f"Base path exists: {self.base_path.exists()}")
        self.scan_folders = scan_folders
        self.index = self._load_index()
        logger.debug(f"Index loaded with {len(self.index)} categories")

    def _load_index(self):
        """Carica l'index da file JSON o scansiona le cartelle"""
        if self.scan_folders:
            logger.debug("Modalità scan_folders attiva")
            return self._scan_folders()
        
        index_file = self.base_path / "index.json"
        logger.debug(f"Cercando index.json in: {index_file}")
        logger.debug(f"Index.json exists: {index_file.exists()}")
        
        if index_file.exists():
            try:
                content = json.loads(index_file.read_text())
                logger.info(f"Index.json caricato: {len(content)} categorie trovate")
                
                # IMPORTANTE: Mappa le chiavi di index.json ai nomi effettivi delle cartelle
                # per garantire coerenza tra nome visualizzato e cartella fisica
                normalized_index = {}
                
                # Crea un mapping case-insensitive tra cartelle fisiche
                actual_folders = {}
                if self.base_path.exists():
                    for item in self.base_path.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            # Usa il nome della cartella fisica come chiave
                            actual_folders[item.name.lower()] = item.name
                
                # Per ogni categoria in index.json, trova la cartella corrispondente
                for category_key, scripts in content.items():
                    # Cerca la cartella fisica corrispondente (case-insensitive)
                    actual_folder_name = actual_folders.get(category_key.lower(), category_key)
                    
                    # Aggiorna i path negli script per usare il nome corretto della cartella
                    updated_scripts = []
                    for script in scripts:
                        script_copy = script.copy()
                        # Aggiorna il path se contiene il vecchio nome della categoria
                        if 'path' in script_copy:
                            old_path = script_copy['path']
                            # Sostituisci il primo segmento del path con il nome corretto della cartella
                            path_parts = old_path.split('/')
                            if len(path_parts) > 0:
                                path_parts[0] = actual_folder_name
                                script_copy['path'] = '/'.join(path_parts)
                        updated_scripts.append(script_copy)
                    
                    normalized_index[actual_folder_name] = updated_scripts
                    logger.debug(f"Mapped '{category_key}' -> '{actual_folder_name}'")
                
                return normalized_index
            except Exception as e:
                logger.error(f"Errore lettura index.json: {e}")
                return {}
        return {}

    def _scan_folders(self):
        """Scansiona le cartelle per trovare gli script"""
        logger.debug(f"Scanning folders in: {self.base_path}")
        index = {}
        if not self.base_path.exists():
            logger.warning(f"Base path non esiste: {self.base_path}")
            return index
        
        # Scansiona le sottocartelle
        try:
            for category_dir in self.base_path.iterdir():
                if not category_dir.is_dir() or category_dir.name.startswith('.'):
                    logger.debug(f"Saltando: {category_dir.name}")
                    continue
                
                category_name = category_dir.name
                scripts = []
                logger.debug(f"Scansionando categoria: {category_name}")
                
                # Cerca script nella cartella (.ps1, .bat, .py, etc)
                for script_file in category_dir.iterdir():
                    if script_file.is_file() and script_file.suffix in ['.ps1', '.bat', '.py', '.sh']:
                        logger.debug(f"  - Trovato script: {script_file.name}")
                        # IMPORTANTE: usa solo il nome file (con estensione), non il path completo
                        scripts.append({
                            "name": script_file.stem,
                            "description": f"Script: {script_file.name}",
                            "path": f"{category_name}/{script_file.name}",  # Senza estensione nel path
                            "params": []
                        })
                
                if scripts:
                    index[category_name] = scripts
                    logger.info(f"Categoria '{category_name}': {len(scripts)} script trovati")
        except Exception as e:
            logger.error(f"Errore scanning folders: {e}")
        
        logger.info(f"Scan completato: {len(index)} categorie totali")
        return index

    def get_categories(self):
        return list(self.index.keys())

    def get_scripts_by_category(self, category):
        return self.index.get(category, [])
    
    def get_all_scripts(self):
        """Restituisce tutti gli script di tutte le categorie"""
        all_scripts = []
        for scripts in self.index.values():
            all_scripts.extend(scripts)
        return all_scripts