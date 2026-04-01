# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Specter AI Assistant
Optimised for size — excludes unused Qt modules, test frameworks, and heavy
scientific subpackages that aren't needed at runtime.
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
    # PyQt6 modules (only the ones we actually use)
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',

    # Database and ORM
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'alembic',
    'alembic.config',
    'sqlite3',

    # HTTP and networking
    'requests',
    'urllib3',
    'ssl',
    'certifi',

    # AI and API clients
    'openai',

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

    # RAG pipeline
    'faiss',
    'numpy',
    'tiktoken',

    # Skills
    'ddgs',
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
        # ── GUI frameworks we don't use ──
        'tkinter', 'tk', 'tcl',

        # ── Unused PyQt6 modules (saves ~70 MB of DLLs) ──
        'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtQuick', 'PyQt6.QtQuick3D', 'PyQt6.QtQuickWidgets',
        'PyQt6.QtQml', 'PyQt6.QtQmlModels',
        'PyQt6.QtDesigner', 'PyQt6.QtHelp',
        'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
        'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
        'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets',
        'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
        'PyQt6.QtPositioning', 'PyQt6.QtSensors',
        'PyQt6.QtSerialPort', 'PyQt6.QtRemoteObjects',
        'PyQt6.QtTest', 'PyQt6.QtDBus',
        'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.Qt3DInput',
        'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
        'PyQt6.QtShaderTools',

        # ── Heavy scientific libs (only small parts used) ──
        'scipy.spatial.ckdtree',
        'scipy.integrate', 'scipy.interpolate', 'scipy.optimize',
        'scipy.signal', 'scipy.fft', 'scipy.io',
        'scipy.ndimage', 'scipy.odr', 'scipy.misc',
        'scipy.cluster', 'scipy.constants',

        # ── Pandas internals we don't need ──
        'pandas.plotting', 'pandas.io.formats.style',
        'pandas.io.stata', 'pandas.io.sas', 'pandas.io.spss',

        # ── Test frameworks (not needed at runtime) ──
        'pytest', 'pytest_qt', 'pytest_asyncio',
        '_pytest', 'pluggy',

        # ── Other unused heavy packages ──
        'matplotlib', 'jupyter', 'IPython', 'notebook',
        'sphinx', 'docutils',
        'pytesseract',  # optional OCR, rarely installed
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ── Strip unused Qt DLLs and data from the bundle ──
# These are pulled in by PyQt6 but never loaded by Specter.
_qt_dll_excludes = {
    # Software OpenGL renderer (~20 MB)
    'opengl32sw.dll',
    # Multimedia codecs (~16 MB)
    'avcodec-61.dll', 'avformat-61.dll', 'avutil-59.dll',
    'swresample-5.dll', 'swscale-8.dll',
    # Qt modules we excluded above
    'Qt6Quick.dll', 'Qt6Quick3D.dll', 'Qt6Quick3DRuntimeRender.dll',
    'Qt6Quick3DPhysics.dll', 'Qt6Quick3DUtils.dll',
    'Qt6Qml.dll', 'Qt6QmlModels.dll', 'Qt6QmlWorkerScript.dll',
    'Qt6Designer.dll', 'Qt6Pdf.dll',
    'Qt6ShaderTools.dll',
    'Qt6Multimedia.dll', 'Qt6MultimediaWidgets.dll',
    'Qt6WebEngineCore.dll', 'Qt6WebChannel.dll',
    'Qt6QuickControls2.dll', 'Qt6QuickControls2Imagine.dll',
    'Qt6QuickDialogs2.dll', 'Qt6QuickDialogs2QuickImpl.dll',
    'Qt6QuickLayouts.dll', 'Qt6QuickTemplates2.dll',
    'Qt6QuickTimeline.dll', 'Qt6QuickParticles.dll',
    'Qt6Svg.dll', 'Qt6SvgWidgets.dll',
    'Qt6Charts.dll', 'Qt6DataVisualization.dll',
    'Qt6OpenGL.dll',
    'd3dcompiler_47.dll',
}

a.binaries = [b for b in a.binaries if b[0].split('/')[-1].split('\\')[-1] not in _qt_dll_excludes]

# Also strip Qt translations and qml directories
a.datas = [d for d in a.datas if not d[0].startswith(('PyQt6/Qt6/translations/',
                                                       'PyQt6/Qt6/qml/',
                                                       'PyQt6/Qt6/qsci/'))]

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
    icon=str(base_path / 'specter' / 'assets' / 'app_icon.png') if (base_path / 'specter' / 'assets' / 'app_icon.png').exists() else None,
)
