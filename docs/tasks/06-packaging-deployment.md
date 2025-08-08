# Packaging and Deployment Plan

## Overview

This document outlines the comprehensive packaging and deployment strategy for Ghostman, focusing on creating a single-file executable using PyInstaller that works without administrator permissions across different platforms.

## Packaging Strategy

### Core Requirements
- **Single executable file** (.exe for Windows)
- **No installer required** - direct execution
- **No admin permissions** needed
- **All dependencies bundled** including PyQt6, OpenAI libraries
- **Optimized file size** (target < 150MB)
- **Cross-platform support** (Windows primary, macOS/Linux secondary)
- **Logging system integration** - proper log file handling in packaged application
- **Debug information support** - enable troubleshooting in production

## PyInstaller Configuration

### 1. Main Spec File

**File**: `Ghostman.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Project paths
project_root = Path(SPECPATH)
src_path = project_root / 'ghostman' / 'src'
assets_path = project_root / 'assets'

# Analysis configuration
a = Analysis(
    # Main entry point
    [str(src_path / 'main.py')],
    
    # Additional paths to search for imports
    pathex=[
        str(project_root),
        str(src_path),
    ],
    
    # Binary files to include
    binaries=[],
    
    # Data files to include
    datas=[
        # Assets
        (str(assets_path / 'icons'), 'assets/icons'),
        (str(assets_path / 'sounds'), 'assets/sounds'),
        (str(assets_path / 'themes'), 'assets/themes'),
        
        # Configuration templates
        (str(project_root / 'config'), 'config'),
    ],
    
    # Hidden imports that PyInstaller might miss
    hiddenimports=[
        # PyQt6 modules
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.sip',
        
        # OpenAI and HTTP libraries
        'openai',
        'httpx',
        'httpcore',
        'anyio',
        'sniffio',
        'h11',
        'certifi',
        'charset_normalizer',
        
        # Async libraries
        'asyncio',
        'concurrent.futures',
        
        # Data processing
        'pydantic',
        'pydantic.v1',
        'pydantic_core',
        'typing_extensions',
        'annotated_types',
        
        # Token counting
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        'regex',
        
        # Encryption
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.backends',
        
        # Database
        'sqlite3',
        
        # JSON handling
        'json',
        'toml',
        
        # Toast notifications
        'tkinter',
        'tkinter.ttk',
        
        # Desktop notifications (optional)
        'desktop_notifier',
        'plyer',
        
        # Standard library modules that might be missed
        'uuid',
        'pathlib',
        'datetime',
        'logging',
        'logging.handlers',
        'configparser',
        'platform',
        'ctypes',
        'ctypes.wintypes',
    ],
    
    # Hooks for special handling
    hookspath=[],
    
    # Collect all submodules
    hooksconfig={
        "PyQt6": {
            "qt_plugins": True,
        },
    },
    
    # Runtime hooks
    runtime_hooks=[],
    
    # Exclude unnecessary modules
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
    ],
    
    # Don't follow imports to these modules
    noarchive=False,
    
    # Optimize bytecode
    optimize=2,
)

# Process collected data
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,  # Don't encrypt (causes issues with some systems)
)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    
    # Executable properties
    name='Ghostman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Don't use UPX (causes issues with PyQt6)
    upx_exclude=[],
    
    # Runtime options
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # Windows specific
    version='version_info.txt' if sys.platform == 'win32' else None,
    icon=str(assets_path / 'icons' / 'ghostman.ico') if sys.platform == 'win32' else None,
    
    # Manifest for Windows (no admin required)
    manifest='ghostman.exe.manifest' if sys.platform == 'win32' else None,
)

# For macOS, create app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Ghostman.app',
        icon=str(assets_path / 'icons' / 'ghostman.icns'),
        bundle_identifier='com.ghostman.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSUIElement': '1',  # Hide from dock initially
        },
    )
```

### 2. Windows Manifest (No Admin Required)

**File**: `ghostman.exe.manifest`

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="1.0.0.0"
    processorArchitecture="*"
    name="Ghostman.AI.Assistant"
    type="win32"
  />
  <description>Ghostman AI Desktop Assistant</description>
  
  <!-- Request user-level execution (no admin) -->
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  
  <!-- Windows 10/11 compatibility -->
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/> <!-- Windows 10/11 -->
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/> <!-- Windows 8.1 -->
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/> <!-- Windows 8 -->
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/> <!-- Windows 7 -->
    </application>
  </compatibility>
  
  <!-- DPI awareness -->
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
    </windowsSettings>
  </application>
  
  <!-- Visual styles -->
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.Windows.Common-Controls"
        version="6.0.0.0"
        processorArchitecture="*"
        publicKeyToken="6595b64144ccf1df"
        language="*"
      />
    </dependentAssembly>
  </dependency>
</assembly>
```

### 3. Version Information

**File**: `version_info.txt`

```
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'Ghostman Team'),
            StringStruct(u'FileDescription', u'Ghostman AI Desktop Assistant'),
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'InternalName', u'ghostman'),
            StringStruct(u'LegalCopyright', u'© 2025 Ghostman Team. All rights reserved.'),
            StringStruct(u'OriginalFilename', u'Ghostman.exe'),
            StringStruct(u'ProductName', u'Ghostman'),
            StringStruct(u'ProductVersion', u'1.0.0'),
            StringStruct(u'Comments', u'AI-powered desktop assistant overlay')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

## Build Scripts

### 1. Main Build Script

**File**: `scripts/build.py`

```python
#!/usr/bin/env python3
"""Build script for Ghostman application."""

import sys
import os
import shutil
import subprocess
import platform
import argparse
import json
import hashlib
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GhostmanBuilder:
    """Build manager for Ghostman application."""
    
    def __init__(self, project_root: Path, debug: bool = False):
        self.project_root = Path(project_root)
        self.debug = debug
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "Ghostman.spec"
        
        # Platform-specific settings
        self.platform = platform.system().lower()
        self.executable_name = self._get_executable_name()
        
        # Build metadata
        self.build_info = {
            'version': '1.0.0',
            'build_number': self._get_build_number(),
            'build_date': datetime.utcnow().isoformat(),
            'platform': self.platform,
            'python_version': sys.version,
        }
    
    def _get_executable_name(self) -> str:
        """Get platform-specific executable name."""
        if self.platform == 'windows':
            return 'Ghostman.exe'
        elif self.platform == 'darwin':
            return 'Ghostman.app'
        else:
            return 'Ghostman'
    
    def _get_build_number(self) -> int:
        """Get incremental build number."""
        build_file = self.project_root / '.build_number'
        
        if build_file.exists():
            with open(build_file, 'r') as f:
                build_number = int(f.read().strip())
        else:
            build_number = 0
        
        build_number += 1
        
        with open(build_file, 'w') as f:
            f.write(str(build_number))
        
        return build_number
    
    def check_requirements(self) -> bool:
        """Check build requirements."""
        logger.info("Checking build requirements...")
        
        # Check Python version
        if sys.version_info < (3, 10):
            logger.error("Python 3.10+ is required")
            return False
        
        # Check PyInstaller
        try:
            import PyInstaller
            logger.info(f"PyInstaller version: {PyInstaller.__version__}")
        except ImportError:
            logger.error("PyInstaller not installed. Run: pip install pyinstaller")
            return False
        
        # Check required packages
        required_packages = [
            'PyQt6',
            'openai',
            'pydantic',
            'tiktoken',
            'cryptography',
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"Missing packages: {', '.join(missing_packages)}")
            logger.info("Install with: pip install -r requirements.txt")
            return False
        
        # Check spec file exists
        if not self.spec_file.exists():
            logger.error(f"Spec file not found: {self.spec_file}")
            return False
        
        logger.info("All requirements satisfied")
        return True
    
    def clean_build_dirs(self):
        """Clean previous build artifacts."""
        logger.info("Cleaning build directories...")
        
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"Removed: {dir_path}")
        
        # Clean __pycache__ directories
        for pycache in self.project_root.rglob('__pycache__'):
            shutil.rmtree(pycache)
        
        logger.info("Build directories cleaned")
    
    def run_tests(self) -> bool:
        """Run tests before building."""
        logger.info("Running tests...")
        
        test_dir = self.project_root / 'tests'
        if not test_dir.exists():
            logger.warning("No tests directory found, skipping tests")
            return True
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', str(test_dir), '-v'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                logger.info("All tests passed")
                return True
            else:
                logger.error("Tests failed:")
                logger.error(result.stdout)
                logger.error(result.stderr)
                return False
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Test execution failed: {e}")
            return False
    
    def build_executable(self) -> bool:
        """Build the executable using PyInstaller."""
        logger.info(f"Building {self.executable_name}...")
        
        # Prepare PyInstaller command
        cmd = [
            sys.executable,
            '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
        ]
        
        if self.debug:
            cmd.extend(['--debug', 'all'])
            cmd.append('--log-level=DEBUG')
        else:
            cmd.append('--log-level=INFO')
        
        # Add spec file
        cmd.append(str(self.spec_file))
        
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONOPTIMIZE'] = '2' if not self.debug else '0'
        
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                env=env
            )
            
            if result.returncode == 0:
                logger.info("Build successful")
                
                # Log output for debugging
                if self.debug:
                    logger.debug(result.stdout)
                
                return True
            else:
                logger.error("Build failed:")
                logger.error(result.stdout)
                logger.error(result.stderr)
                return False
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Build execution failed: {e}")
            return False
    
    def optimize_executable(self):
        """Optimize the built executable."""
        logger.info("Optimizing executable...")
        
        executable_path = self.dist_dir / self.executable_name
        
        if not executable_path.exists():
            logger.error(f"Executable not found: {executable_path}")
            return
        
        # Get initial size
        initial_size = executable_path.stat().st_size / (1024 * 1024)
        logger.info(f"Initial size: {initial_size:.2f} MB")
        
        # Platform-specific optimizations
        if self.platform == 'windows':
            self._optimize_windows_exe(executable_path)
        elif self.platform == 'darwin':
            self._optimize_macos_app(executable_path)
        elif self.platform == 'linux':
            self._optimize_linux_binary(executable_path)
        
        # Get final size
        final_size = executable_path.stat().st_size / (1024 * 1024)
        logger.info(f"Final size: {final_size:.2f} MB")
        logger.info(f"Size reduction: {initial_size - final_size:.2f} MB")
    
    def _optimize_windows_exe(self, exe_path: Path):
        """Windows-specific optimizations."""
        # Strip debug symbols if not in debug mode
        if not self.debug:
            try:
                subprocess.run(['strip', str(exe_path)], check=True)
                logger.info("Stripped debug symbols")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("Could not strip executable (strip not available)")
    
    def _optimize_macos_app(self, app_path: Path):
        """macOS-specific optimizations."""
        # Code sign the app
        try:
            subprocess.run(
                ['codesign', '--force', '--deep', '--sign', '-', str(app_path)],
                check=True
            )
            logger.info("Code signed the app")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not code sign (codesign not available)")
    
    def _optimize_linux_binary(self, binary_path: Path):
        """Linux-specific optimizations."""
        # Strip symbols
        try:
            subprocess.run(['strip', str(binary_path)], check=True)
            logger.info("Stripped debug symbols")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not strip binary")
    
    def create_distribution_package(self):
        """Create distribution package with all necessary files."""
        logger.info("Creating distribution package...")
        
        # Create package directory
        package_name = f"Ghostman-{self.build_info['version']}-{self.platform}"
        package_dir = self.dist_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy executable
        executable_path = self.dist_dir / self.executable_name
        if executable_path.exists():
            if executable_path.is_dir():
                shutil.copytree(executable_path, package_dir / self.executable_name)
            else:
                shutil.copy2(executable_path, package_dir)
        
        # Create README
        readme_content = f"""# Ghostman AI Desktop Assistant

Version: {self.build_info['version']}
Build: {self.build_info['build_number']}
Date: {self.build_info['build_date']}
Platform: {self.platform}

## Installation

No installation required! Simply run the executable:
- Windows: Double-click Ghostman.exe
- macOS: Double-click Ghostman.app
- Linux: Run ./Ghostman

## First Run

1. The application will start minimized as an avatar
2. Click the avatar to open the main interface
3. Right-click for the context menu
4. Configure your AI settings in Settings

## Requirements

- No administrator permissions required
- Internet connection for AI features
- 100MB free disk space

## Support

For issues and updates, visit: https://github.com/ghostman/ghostman
"""
        
        with open(package_dir / 'README.txt', 'w') as f:
            f.write(readme_content)
        
        # Create build info file
        with open(package_dir / 'build_info.json', 'w') as f:
            json.dump(self.build_info, f, indent=2)
        
        # Create archive
        archive_name = f"{package_name}.zip"
        archive_path = self.dist_dir / archive_name
        
        logger.info(f"Creating archive: {archive_name}")
        shutil.make_archive(
            str(archive_path.with_suffix('')),
            'zip',
            package_dir.parent,
            package_dir.name
        )
        
        # Calculate hash
        sha256_hash = self._calculate_hash(archive_path)
        
        # Create hash file
        with open(archive_path.with_suffix('.zip.sha256'), 'w') as f:
            f.write(f"{sha256_hash}  {archive_name}\n")
        
        logger.info(f"Distribution package created: {archive_path}")
        logger.info(f"SHA256: {sha256_hash}")
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def run_post_build_tests(self) -> bool:
        """Run tests on the built executable."""
        logger.info("Running post-build tests...")
        
        executable_path = self.dist_dir / self.executable_name
        
        if not executable_path.exists():
            logger.error(f"Executable not found: {executable_path}")
            return False
        
        # Test 1: Check if executable runs
        try:
            if self.platform == 'windows':
                test_cmd = [str(executable_path), '--version']
            elif self.platform == 'darwin':
                test_cmd = ['open', '-a', str(executable_path), '--args', '--version']
            else:
                test_cmd = [str(executable_path), '--version']
            
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Executable runs successfully")
            else:
                logger.error(f"Executable failed to run: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.warning("Executable test timed out (might be normal for GUI app)")
        except Exception as e:
            logger.error(f"Failed to test executable: {e}")
            return False
        
        # Test 2: Check file size
        file_size_mb = executable_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 200:
            logger.warning(f"Executable size ({file_size_mb:.2f} MB) exceeds target (150 MB)")
        else:
            logger.info(f"Executable size: {file_size_mb:.2f} MB")
        
        return True
    
    def build(self) -> bool:
        """Run the complete build process."""
        logger.info("=" * 60)
        logger.info(f"Building Ghostman v{self.build_info['version']}")
        logger.info(f"Build #{self.build_info['build_number']}")
        logger.info("=" * 60)
        
        try:
            # Check requirements
            if not self.check_requirements():
                return False
            
            # Clean previous builds
            self.clean_build_dirs()
            
            # Run tests
            if not self.debug and not self.run_tests():
                logger.error("Tests failed, aborting build")
                return False
            
            # Build executable
            if not self.build_executable():
                return False
            
            # Optimize
            self.optimize_executable()
            
            # Create distribution package
            self.create_distribution_package()
            
            # Post-build tests
            if not self.run_post_build_tests():
                logger.warning("Post-build tests failed")
            
            logger.info("=" * 60)
            logger.info("Build completed successfully!")
            logger.info(f"Output: {self.dist_dir}")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"Build failed with error: {e}")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Build Ghostman application')
    parser.add_argument('--debug', action='store_true', help='Build in debug mode')
    parser.add_argument('--no-tests', action='store_true', help='Skip tests')
    parser.add_argument('--clean-only', action='store_true', help='Only clean build directories')
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create builder
    builder = GhostmanBuilder(project_root, debug=args.debug)
    
    # Run appropriate action
    if args.clean_only:
        builder.clean_build_dirs()
    else:
        success = builder.build()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

### 2. Simple Build Batch Script (Windows)

**File**: `scripts/build.bat`

```batch
@echo off
echo Building Ghostman...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+
    exit /b 1
)

REM Run build script
python scripts\build.py %*

REM Check result
if errorlevel 1 (
    echo Build failed!
    exit /b 1
) else (
    echo Build successful!
    echo Output in: dist\
)
```

## GitHub Actions CI/CD

**File**: `.github/workflows/build.yml`

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'
  pull_request:
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
        
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller pytest
    
    - name: Run tests
      run: pytest tests/
    
    - name: Build executable
      run: python scripts/build.py
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: ghostman-${{ matrix.os }}
        path: dist/Ghostman-*
```

This comprehensive packaging and deployment plan provides everything needed to create professional, single-file executables for Ghostman that work reliably without administrator permissions across different platforms.