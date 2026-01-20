"""
============================================================
File: windows_scheduler.py
Author: Internal Systems Automation Team
Created: 2026-01-19

Description:
Gestisce la creazione, modifica ed eliminazione di task schedulati
nel Windows Task Scheduler. Permette di eseguire script anche quando
l'applicazione è chiusa.
============================================================
"""

import subprocess
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys


class WindowsTaskScheduler:
    """Gestisce i task schedulati nel Task Scheduler di Windows"""
    
    TASK_PREFIX = "SYS_Toolset_"
    
    def __init__(self):
        """Inizializza il gestore del Task Scheduler"""
        self.task_folder = "\\SYS-Toolset\\"
        
    def create_task(self, script_name: str, script_path: Path, trigger_config: Dict, 
                   working_dir: Path, python_exe: Path = None) -> tuple[bool, str]:
        """
        Crea un task nel Task Scheduler di Windows
        
        Args:
            script_name: Nome identificativo dello script
            script_path: Path completo allo script da eseguire
            trigger_config: Configurazione del trigger (type, datetime, time, days, etc.)
            working_dir: Directory di lavoro per l'esecuzione
            python_exe: Path all'eseguibile Python (se None, usa sys.executable)
            
        Returns:
            Tuple (success: bool, error_message: str)
        """
        if python_exe is None:
            # Se l'app è frozen (exe), cerca Python nel sistema
            if getattr(sys, 'frozen', False):
                # Prova a trovare pythonw.exe (senza finestra console) nel PATH
                import shutil
                pythonw_path = shutil.which('pythonw')
                if pythonw_path:
                    python_exe = Path(pythonw_path)
                else:
                    # Fallback: prova path comuni di pythonw.exe
                    common_paths = [
                        Path(r"C:\Python312\pythonw.exe"),
                        Path(r"C:\Python311\pythonw.exe"),
                        Path(r"C:\Python310\pythonw.exe"),
                        Path(r"C:\Python39\pythonw.exe"),
                        Path(r"C:\Program Files\Python312\pythonw.exe"),
                        Path(r"C:\Program Files\Python311\pythonw.exe"),
                        Path(r"C:\Program Files\Python310\pythonw.exe"),
                    ]
                    for path in common_paths:
                        if path.exists():
                            python_exe = path
                            break
                    else:
                        # Ultimo fallback: usa pyw launcher
                        python_exe = Path("pythonw")
            else:
                python_exe = Path(sys.executable)
            
        task_name = f"{self.TASK_PREFIX}{script_name.replace(' ', '_')}"
        
        try:
            # Verifica che lo script esista
            if not script_path.exists():
                return False, f"Script non trovato: {script_path}"
            
            # Normalizza trigger_config: se ha 'data', estrai i valori
            normalized_trigger = trigger_config.copy()
            if 'data' in normalized_trigger:
                trigger_type = normalized_trigger['type']
                data = normalized_trigger.pop('data')
                normalized_trigger.update(data)
            
            # Crea il wrapper script che eseguirà lo script target
            wrapper_script = self._create_wrapper_script(script_name, script_path, working_dir)
            
            # Crea il file XML per il task
            xml_file = self._create_task_xml(
                task_name=task_name,
                script_name=script_name,
                wrapper_script=wrapper_script,
                trigger_config=normalized_trigger,
                python_exe=python_exe,
                working_dir=working_dir
            )
            
            # Registra il task usando schtasks (senza mostrare finestre)
            CREATE_NO_WINDOW = 0x08000000
            cmd = [
                'schtasks',
                '/Create',
                '/TN', f"{self.task_folder}{task_name}",
                '/XML', str(xml_file),
                '/F'  # Force overwrite se esiste già
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            # Rimuovi il file XML temporaneo
            xml_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                print(f"✅ Task Windows creato: {task_name}")
                return True, ""
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                print(f"❌ Errore creazione task: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"❌ Errore nella creazione del task: {error_msg}")
            return False, str(e)
    
    def delete_task(self, script_name: str) -> bool:
        """
        Elimina un task dal Task Scheduler
        
        Args:
            script_name: Nome identificativo dello script
            
        Returns:
            True se il task è stato eliminato con successo, False altrimenti
        """
        task_name = f"{self.TASK_PREFIX}{script_name.replace(' ', '_')}"
        
        try:
            CREATE_NO_WINDOW = 0x08000000
            cmd = [
                'schtasks',
                '/Delete',
                '/TN', f"{self.task_folder}{task_name}",
                '/F'  # Force senza conferma
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print(f"✅ Task Windows eliminato: {task_name}")
                
                # Elimina anche il wrapper script
                self._delete_wrapper_script(script_name)
                return True
            else:
                # Se il task non esiste, non è un errore
                if "cannot find the file" in result.stderr.lower() or "impossibile trovare" in result.stderr.lower():
                    print(f"ℹ️ Task non esistente: {task_name}")
                    return True
                print(f"❌ Errore eliminazione task: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Errore nell'eliminazione del task: {e}")
            return False
    
    def task_exists(self, script_name: str) -> bool:
        """
        Verifica se un task esiste nel Task Scheduler
        
        Args:
            script_name: Nome identificativo dello script
            
        Returns:
            True se il task esiste, False altrimenti
        """
        task_name = f"{self.TASK_PREFIX}{script_name.replace(' ', '_')}"
        
        try:
            CREATE_NO_WINDOW = 0x08000000
            cmd = [
                'schtasks',
                '/Query',
                '/TN', f"{self.task_folder}{task_name}",
                '/FO', 'LIST'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _create_wrapper_script(self, script_name: str, script_path: Path, working_dir: Path) -> Path:
        """
        Crea uno script Python wrapper che eseguirà lo script target con logging
        
        Args:
            script_name: Nome identificativo dello script
            script_path: Path completo allo script da eseguire
            working_dir: Directory di lavoro
            
        Returns:
            Path al wrapper script creato
        """
        # Directory per i wrapper scripts
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent
            
        wrappers_dir = base_dir / "schedules" / "wrappers"
        wrappers_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = script_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        wrapper_path = wrappers_dir / f"wrapper_{safe_name}.py"
        
        # Crea il contenuto del wrapper - usa triple quote e escape corretto
        wrapper_content = f"""\"\"\"
Wrapper script per esecuzione schedulata
Script: {script_name}
Generato automaticamente da SYS-Toolset
\"\"\"

import subprocess
import sys
from datetime import datetime
from pathlib import Path

def main():
    # Path dello script da eseguire
    script_path = Path(r"{script_path}")
    working_dir = Path(r"{working_dir}")
    
    # Directory logs
    logs_dir = working_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Crea file di log con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"scheduled_{safe_name}_{{timestamp}}.log"
    
    try:
        # Determina il comando
        if script_path.suffix.lower() == '.ps1':
            cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)]
        elif script_path.suffix.lower() == '.py':
            cmd = [sys.executable, str(script_path)]
        elif script_path.suffix.lower() in ['.bat', '.cmd']:
            cmd = ['cmd', '/c', str(script_path)]
        else:
            cmd = [str(script_path)]
        
        # Scrivi header nel log
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Esecuzione Schedulata: {script_name} ===\\n")
            f.write(f"Data/Ora: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\\n")
            f.write(f"Script: " + str(script_path) + "\\n")
            f.write(f"Comando: " + ' '.join(cmd) + "\\n")
            f.write("=" * 60 + "\\n\\n")
        
        # Esegui lo script in modo silente (senza finestre)
        import subprocess
        CREATE_NO_WINDOW = 0x08000000  # Flag per Windows
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 ora timeout
            cwd=str(working_dir),
            creationflags=CREATE_NO_WINDOW  # Nascondi la finestra
        )
        
        # Scrivi output nel log
        with open(log_file, 'a', encoding='utf-8') as f:
            if result.stdout:
                f.write("Output:\\n")
                f.write(result.stdout + "\\n")
            
            if result.stderr:
                f.write("\\nErrori:\\n")
                f.write(result.stderr + "\\n")
            
            f.write("\\n" + "=" * 60 + "\\n")
            if result.returncode == 0:
                f.write("✅ Completato con successo (exit code: 0)\\n")
            else:
                f.write(f"❌ Errore (exit code: " + str(result.returncode) + ")\\n")
            
            f.write(f"Log salvato: " + str(log_file) + "\\n")
        
        sys.exit(result.returncode)
        
    except subprocess.TimeoutExpired:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write("\\n❌ ERRORE: Timeout (1 ora)\\n")
        sys.exit(1)
        
    except Exception as e:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\\n❌ ERRORE: " + str(e) + "\\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
        
        # Scrivi il wrapper su file
        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)
        
        return wrapper_path
    
    def _delete_wrapper_script(self, script_name: str):
        """Elimina il wrapper script"""
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent
            
        wrappers_dir = base_dir / "schedules" / "wrappers"
        safe_name = script_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        wrapper_path = wrappers_dir / f"wrapper_{safe_name}.py"
        
        wrapper_path.unlink(missing_ok=True)
    
    def _create_task_xml(self, task_name: str, script_name: str, wrapper_script: Path,
                        trigger_config: Dict, python_exe: Path, working_dir: Path) -> Path:
        """
        Crea un file XML per la definizione del task
        
        Args:
            task_name: Nome del task
            script_name: Nome dello script
            wrapper_script: Path al wrapper script
            trigger_config: Configurazione del trigger
            python_exe: Path all'eseguibile Python
            working_dir: Directory di lavoro
            
        Returns:
            Path al file XML creato
        """
        # Template base XML per Task Scheduler
        xml_template = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Esecuzione automatica di {script_name}</Description>
    <Author>SYS-Toolset</Author>
  </RegistrationInfo>
  <Triggers>
{self._generate_trigger_xml(trigger_config)}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{wrapper_script}"</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        
        # Salva il file XML temporaneo
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent
            
        temp_dir = base_dir / "schedules" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        xml_file = temp_dir / f"{task_name}.xml"
        with open(xml_file, 'w', encoding='utf-16') as f:
            f.write(xml_template)
        
        return xml_file
    
    def _generate_trigger_xml(self, trigger_config: Dict) -> str:
        """
        Genera la sezione XML per il trigger
        
        Args:
            trigger_config: Configurazione del trigger
            
        Returns:
            Stringa XML del trigger
        """
        trigger_type = trigger_config.get('type')
        
        if trigger_type == 'once':
            # Esecuzione una tantum
            datetime_str = trigger_config.get('datetime', '')
            
            # Gestisci vari formati di data
            try:
                # Prova formato "dd/MM/yyyy HH:mm"
                if '/' in datetime_str:
                    exec_time = datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
                # Prova formato ISO
                else:
                    exec_time = datetime.fromisoformat(datetime_str)
            except Exception as e:
                print(f"⚠️ Errore parsing data '{datetime_str}': {e}")
                exec_time = datetime.now() + timedelta(minutes=5)
            
            return f'''    <TimeTrigger>
      <StartBoundary>{exec_time.strftime('%Y-%m-%dT%H:%M:%S')}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>'''
            
        elif trigger_type == 'daily':
            # Esecuzione giornaliera
            time_str = trigger_config['time']
            hour, minute = time_str.split(':')
            start_date = datetime.now().strftime('%Y-%m-%d')
            return f'''    <CalendarTrigger>
      <StartBoundary>{start_date}T{hour}:{minute}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>'''
            
        elif trigger_type == 'weekly':
            # Esecuzione settimanale
            days = trigger_config['days']
            time_str = trigger_config['time']
            hour, minute = time_str.split(':')
            start_date = datetime.now().strftime('%Y-%m-%d')
            
            # Converti i giorni nel formato Windows Task Scheduler
            days_xml = []
            day_mapping = {
                'mon': 'Monday',
                'tue': 'Tuesday',
                'wed': 'Wednesday',
                'thu': 'Thursday',
                'fri': 'Friday',
                'sat': 'Saturday',
                'sun': 'Sunday'
            }
            
            for day in days:
                if day.lower() in day_mapping:
                    days_xml.append(f'        <{day_mapping[day.lower()]} />')
            
            days_xml_str = '\n'.join(days_xml)
            
            return f'''    <CalendarTrigger>
      <StartBoundary>{start_date}T{hour}:{minute}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
{days_xml_str}
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>'''
            
        elif trigger_type == 'interval':
            # Esecuzione a intervalli
            interval_type = trigger_config['interval_type']
            interval_value = trigger_config['interval_value']
            start_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            
            # Converti in formato ISO 8601 duration
            if interval_type == 'minutes':
                repetition = f'PT{interval_value}M'
            elif interval_type == 'hours':
                repetition = f'PT{interval_value}H'
            elif interval_type == 'days':
                repetition = f'P{interval_value}D'
            else:
                repetition = 'PT1H'
            
            return f'''    <TimeTrigger>
      <Repetition>
        <Interval>{repetition}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>{start_date}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>'''
        
        return ''
    
    def list_all_tasks(self) -> List[str]:
        """
        Elenca tutti i task SYS-Toolset nel Task Scheduler
        
        Returns:
            Lista dei nomi dei task
        """
        try:
            CREATE_NO_WINDOW = 0x08000000
            cmd = [
                'schtasks',
                '/Query',
                '/FO', 'LIST',
                '/V'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode != 0:
                return []
            
            tasks = []
            for line in result.stdout.split('\n'):
                if 'TaskName:' in line or 'Nome attività:' in line:
                    task_name = line.split(':', 1)[1].strip()
                    if self.TASK_PREFIX in task_name:
                        tasks.append(task_name)
            
            return tasks
            
        except Exception as e:
            print(f"❌ Errore nel listing dei task: {e}")
            return []
