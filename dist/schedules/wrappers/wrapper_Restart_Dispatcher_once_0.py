"""
Wrapper script per esecuzione schedulata
Script: Restart_Dispatcher_once_0
Generato automaticamente da SYS-Toolset
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

def main():
    # Path dello script da eseguire
    script_path = Path(r"C:\Users\alex.sorrentino\OneDrive - DGS SpA\Desktop\TC\SYS-Toolset\dist\scripts\dispatcher\restart_dispatcher.ps1")
    working_dir = Path(r"C:\Users\alex.sorrentino\OneDrive - DGS SpA\Desktop\TC\SYS-Toolset\dist")
    
    # Directory logs
    logs_dir = working_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Crea file di log con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"scheduled_Restart_Dispatcher_once_0_{timestamp}.log"
    
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
            f.write(f"=== Esecuzione Schedulata: Restart_Dispatcher_once_0 ===\n")
            f.write(f"Data/Ora: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n")
            f.write(f"Script: " + str(script_path) + "\n")
            f.write(f"Comando: " + ' '.join(cmd) + "\n")
            f.write("=" * 60 + "\n\n")
        
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
                f.write("Output:\n")
                f.write(result.stdout + "\n")
            
            if result.stderr:
                f.write("\nErrori:\n")
                f.write(result.stderr + "\n")
            
            f.write("\n" + "=" * 60 + "\n")
            if result.returncode == 0:
                f.write("✅ Completato con successo (exit code: 0)\n")
            else:
                f.write(f"❌ Errore (exit code: " + str(result.returncode) + ")\n")
            
            f.write(f"Log salvato: " + str(log_file) + "\n")
        
        sys.exit(result.returncode)
        
    except subprocess.TimeoutExpired:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write("\n❌ ERRORE: Timeout (1 ora)\n")
        sys.exit(1)
        
    except Exception as e:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n❌ ERRORE: " + str(e) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
