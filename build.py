#!/usr/bin/env python3
"""
Build script for Specter
Creates production packages and executables
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e.stderr}")
        return False
    return True

def clean_build():
    """Clean previous build artifacts."""
    dirs_to_clean = ['build', 'dist', '*.egg-info']
    for dir_pattern in dirs_to_clean:
        for path in Path('.').glob(dir_pattern):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"🧹 Removed directory: {path}")
                else:
                    path.unlink()
                    print(f"🧹 Removed file: {path}")

def build_wheel():
    """Build Python wheel package."""
    return run_command("python setup.py bdist_wheel", "Building wheel package")

def build_source():
    """Build source distribution."""
    return run_command("python setup.py sdist", "Building source distribution")

def build_executable():
    """Build standalone executable with PyInstaller."""
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=specter",
        "--onefile",
        "--windowed",
        "--icon=specter/assets/avatar.ico" if Path('specter/assets/avatar.ico').exists() else "",
        "--add-data=specter/assets:specter/assets",
        "--add-data=specter/__version__.py:specter",
        "--hidden-import=PyQt6",
        "--hidden-import=markdown",
        "--hidden-import=aiohttp",
        "--hidden-import=sqlalchemy",
        "specter/__main__.py"
    ]

    # Filter out empty strings
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]

    return run_command(' '.join(pyinstaller_cmd), "Building standalone executable")

def main():
    """Main build process."""
    print("🚀 Starting Specter build process...")

    # Check if we're in the right directory
    if not Path('specter').exists():
        print("❌ Error: Run this script from the Specter root directory")
        sys.exit(1)

    # Clean previous builds
    print("\n🧹 Cleaning previous builds...")
    clean_build()

    # Build packages
    success = True
    success &= build_source()
    success &= build_wheel()

    # Check if PyInstaller is available for executable build
    try:
        subprocess.run("pyinstaller --version", shell=True, check=True, capture_output=True)
        success &= build_executable()
    except subprocess.CalledProcessError:
        print("⚠️  PyInstaller not found, skipping executable build")
        print("   Install with: pip install pyinstaller")

    if success:
        print("\n🎉 Build completed successfully!")
        print("\nArtifacts created:")
        print("📦 Source: dist/*.tar.gz")
        print("🎯 Wheel: dist/*.whl")
        if Path('dist/specter').exists() or Path('dist/specter.exe').exists():
            print("💾 Executable: dist/specter or dist/specter.exe")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
