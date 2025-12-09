"""
============================================================
File: tool_menu.py
Author: Internal Systems Automation Team
Created: 2025-01-10
Last Updated: 2025-12-09

Description:
Modulo responsabile della gestione del menu principale
dell'applicazione usando la libreria Rich.
Funziona su Windows, Linux e macOS senza curses.
============================================================
"""

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
import subprocess
import os

class ToolMenu:
    def __init__(self, repository):
        self.repository = repository
        self.categories = repository.get_categories()
        self.console = Console()

    def start(self):
        while True:
            self.console.print("\n[bold cyan]SYSTEM TOOLSET - Select a Category[/bold cyan]\n")
            for idx, cat in enumerate(self.categories, start=1):
                self.console.print(f"{idx}. {cat}")
            self.console.print("0. Exit")

            choice = Prompt.ask("\nSelect a category", choices=[str(i) for i in range(len(self.categories)+1)])
            if choice == "0":
                self.console.print("[bold green]Exiting...[/bold green]")
                break

            category = self.categories[int(choice)-1]
            self._show_script_list(category)

    def _show_script_list(self, category):
        scripts = self.repository.get_scripts_by_category(category)
        if not scripts:
            self.console.print(f"[yellow]No scripts found in {category}[/yellow]")
            return

        while True:
            self.console.print(f"\n[bold magenta]Category: {category}[/bold magenta]")
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("No.", justify="right")
            table.add_column("Script Name")
            table.add_column("Description")

            for idx, s in enumerate(scripts, start=1):
                table.add_row(str(idx), s['name'], s['description'])

            table.add_row("0", "Back", "Return to category selection")
            self.console.print(table)

            choice = Prompt.ask("\nSelect a script to execute", choices=[str(i) for i in range(len(scripts)+1)])
            if choice == "0":
                return  # torna al menu categorie

            script = scripts[int(choice)-1]
            self._execute_script(script)

    def _execute_script(self, script):
        self.console.print(f"[bold green]Executing {script['name']}...[/bold green]")
        script_path = os.path.join("scripts", script["path"])

        # Esegui lo script a seconda dell'estensione
        try:
            if script_path.endswith(".ps1"):
                # PowerShell
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    capture_output=True, text=True
                )
            elif script_path.endswith(".bat") or script_path.endswith(".cmd"):
                # Batch
                result = subprocess.run([script_path], capture_output=True, text=True, shell=True)
            elif script_path.endswith(".py"):
                # Python
                result = subprocess.run(["python", script_path], capture_output=True, text=True)
            else:
                self.console.print(f"[red]Unsupported script type: {script_path}[/red]")
                return

            # Stampa output
            if result.stdout:
                self.console.print(f"[white]{result.stdout}[/white]")
            if result.stderr:
                self.console.print(f"[red]{result.stderr}[/red]")

        except Exception as e:
            self.console.print(f"[bold red]Error executing script: {e}[/bold red]")

        input("Press Enter to return to scripts list")