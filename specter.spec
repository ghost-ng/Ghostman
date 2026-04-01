# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Specter AI Assistant
"""

import os
import sys
from pathlib import Path

# Get the base path
base_path = Path.cwd()

# Define data files to include
datas = [
    (str(base_path / 'specter' / 'assets'), 'specter/assets'),
    (str(base_path / 'specter' / '__version__.py'), 'specter'),
]

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'alembic',
    'alembic.config',
    'sqlite3',
    'requests',
    'urllib3',
    'ssl',
    'certifi',
    'openai',
    'markdown',
    'bleach',
    'html2text',
    'cryptography',
    'cryptography.fernet',
    'asyncio',
    'json',
    'pathlib',
    'logging.handlers',
    'faiss',
    'numpy',
    'tiktoken',
    'ddgs',
]

binaries = []

a = Analysis(
    [str(base_path / 'specter' / '__main__.py')],
    pathex=[str(base_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI frameworks we don't use
        'tkinter', 'tk', 'tcl',
        # Test frameworks
        'pytest', 'pytest_qt', 'pytest_asyncio', '_pytest', 'pluggy',
        # Heavy unused packages
        'matplotlib', 'jupyter', 'IPython', 'notebook',
        'sphinx', 'docutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='specter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_path / 'specter' / 'assets' / 'app_icon.png') if (base_path / 'specter' / 'assets' / 'app_icon.png').exists() else None,
)
