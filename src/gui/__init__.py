"""
============================================================
File: __init__.py
Author: Internal Systems Automation Team
Created: 2026-01-12

Description:
Package per l'interfaccia grafica PyQt6.
============================================================
"""

# Import dinamico per compatibilità PyInstaller
import sys
import os

# Assicurati che la directory src sia nel path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import usando __import__ che è più robusto con PyInstaller
main_window_module = __import__('gui.main_window', fromlist=['MainWindow'])
MainWindow = main_window_module.MainWindow

splash_screen_module = __import__('gui.splash_screen', fromlist=['SplashScreen'])
SplashScreen = splash_screen_module.SplashScreen

__all__ = ['MainWindow', 'SplashScreen']
