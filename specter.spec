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
    # Assets directory (icons, images, etc.)
    (str(base_path / 'specter' / 'assets'), 'specter/assets'),
    # Version file
    (str(base_path / 'specter' / '__version__.py'), 'specter'),
    # Help documentation
    (str(base_path / 'specter' / 'assets' / 'help'), 'specter/assets/help'),
]

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtMultimedia',

    # Database and ORM
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'alembic',
    'alembic.config',
    'sqlite3',

    # HTTP and networking
    'httpx',
    'aiohttp',
    'ssl',
    'certifi',

    # AI and API clients
    'openai',
    'anthropic',

    # Text processing
    'markdown',
    'bleach',
    'html2text',

    # Cryptography
    'cryptography',
    'cryptography.fernet',

    # Standard library modules that might be missed
    'asyncio',
    'json',
    'pathlib',
    'tempfile',
    'webbrowser',
    'subprocess',
    'threading',
    'queue',
    'logging.handlers',
    'pkg_resources',

    # Testing modules (if needed for runtime)
    'pytest',
    'pytest_qt',
    'pytest_asyncio',
]

# Binaries - additional binary files
binaries = []

# Analysis configuration
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
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'tk',
        'tcl',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
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
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_path / 'specter' / 'assets' / 'avatar.png') if (base_path / 'specter' / 'assets' / 'avatar.png').exists() else None,
)
