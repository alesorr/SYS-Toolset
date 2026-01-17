"""
PyInstaller hook for gui package
Forces inclusion of all gui modules
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules from gui package
hiddenimports = collect_submodules('gui')

# Also collect any data files
datas = collect_data_files('gui', include_py_files=True)
