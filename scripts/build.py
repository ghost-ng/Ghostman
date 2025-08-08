#!/usr/bin/env python3
"""
Advanced build script for Ghostman AI Overlay Application
Supports PyInstaller with comprehensive error handling and validation
"""

import os
import sys
import subprocess
import shutil
import argparse
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime

class GhostmanBuilder:
    """Advanced builder for Ghostman application."""
    
    def __init__(self, debug=False, clean=True):
        self.debug = debug
        self.clean = clean
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.spec_file = self.project_root / "Ghostman.spec"
        self.build_log = []
        
    def log(self, message, level="INFO"):
        """Log build messages."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.build_log.append(log_entry)
        
    def run_command(self, command, check=True, timeout=None):
        """Run command with logging and error handling."""
        self.log(f"Running: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout,
                cwd=self.project_root
            )
            
            if result.stdout:
                self.log(f"STDOUT: {result.stdout.strip()}")
            if result.stderr:
                self.log(f"STDERR: {result.stderr.strip()}", "WARN")
                
            return result
            
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed with return code {e.returncode}", "ERROR")
            self.log(f"STDERR: {e.stderr}", "ERROR")
            raise
        except subprocess.TimeoutExpired as e:
            self.log(f"Command timed out after {timeout} seconds", "ERROR")
            raise
            
    def check_dependencies(self):
        """Check if all required tools and dependencies are available."""
        self.log("Checking dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 10):
            raise RuntimeError("Python 3.10+ is required")
        self.log(f"Python version: {sys.version}")
        
        # Check PyInstaller
        try:
            result = self.run_command([sys.executable, "-m", "pyinstaller", "--version"])
            self.log(f"PyInstaller version: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.log("PyInstaller not found, installing...", "WARN")
            self.run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
            
        # Check required files
        required_files = [
            self.spec_file,
            self.project_root / "ghostman" / "src" / "main.py",
            self.project_root / "requirements.txt"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Required file not found: {file_path}")
        self.log("All required files found")
        
        # Check if icon exists
        icon_path = self.project_root / "ghostman" / "assets" / "ghostman_icon.ico"
        if not icon_path.exists():
            self.log(f"Icon not found: {icon_path}", "WARN")
            self.log("Creating placeholder icon...")
            self.create_placeholder_icon(icon_path)
            
    def create_placeholder_icon(self, icon_path):
        """Create a simple placeholder icon if none exists."""
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a minimal ICO file (this is a base64 encoded 16x16 icon)
        ico_data = (
            "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAA"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//"
            "/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///"
            "/wD///8A////AAAAAAAAAAAA"
        )
        
        import base64
        with open(icon_path, 'wb') as f:
            f.write(base64.b64decode(ico_data))
        
        self.log(f"Created placeholder icon: {icon_path}")
        
    def clean_build_dirs(self):
        """Clean previous build artifacts."""
        if not self.clean:
            return
            
        self.log("Cleaning build directories...")
        
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                self.log(f"Removed {directory}")
                
    def install_dependencies(self):
        """Install project dependencies."""
        self.log("Installing dependencies...")
        
        requirements_file = self.project_root / "requirements.txt"
        self.run_command([
            sys.executable, "-m", "pip", "install", 
            "-r", str(requirements_file)
        ])
        
    def build_executable(self):
        """Build the executable using PyInstaller."""
        self.log("Building executable with PyInstaller...")
        
        build_start = time.time()
        
        command = [
            sys.executable, "-m", "pyinstaller",
            "--clean",
            "--noconfirm"
        ]
        
        if self.debug:
            command.extend(["--debug", "all"])
            
        command.append(str(self.spec_file))
        
        # Run PyInstaller with extended timeout
        self.run_command(command, timeout=1800)  # 30 minutes max
        
        build_time = time.time() - build_start
        self.log(f"Build completed in {build_time:.2f} seconds")
        
    def validate_build(self):
        """Validate the built executable."""
        self.log("Validating build...")
        
        exe_path = self.dist_dir / "Ghostman.exe"
        
        if not exe_path.exists():
            raise FileNotFoundError(f"Executable not found: {exe_path}")
            
        # Get file size
        size_mb = exe_path.stat().st_size / 1024 / 1024
        self.log(f"Executable size: {size_mb:.2f} MB")
        
        # Calculate SHA256
        sha256 = self.calculate_sha256(exe_path)
        self.log(f"SHA256: {sha256}")
        
        # Save hash to file
        hash_file = exe_path.with_suffix('.exe.sha256')
        with open(hash_file, 'w') as f:
            f.write(f"{sha256}  {exe_path.name}\n")
        self.log(f"SHA256 saved to: {hash_file}")
        
        # Test basic execution (quick test)
        try:
            result = subprocess.run([str(exe_path), "--version"], 
                                  timeout=10, capture_output=True, text=True)
            if result.returncode == 0:
                self.log("Basic execution test passed")
            else:
                self.log(f"Execution test warning: {result.stderr}", "WARN")
        except subprocess.TimeoutExpired:
            self.log("Execution test timeout (may be normal for GUI apps)", "WARN")
        except Exception as e:
            self.log(f"Execution test error: {e}", "WARN")
            
        return {
            "executable_path": str(exe_path),
            "size_mb": size_mb,
            "sha256": sha256,
            "hash_file": str(hash_file)
        }
        
    def calculate_sha256(self, file_path):
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
        
    def save_build_report(self, validation_results):
        """Save detailed build report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "project_root": str(self.project_root),
            "build_log": self.build_log,
            "validation": validation_results
        }
        
        report_file = self.dist_dir / "build_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Build report saved: {report_file}")
        
    def build(self):
        """Main build process."""
        try:
            self.log("Starting Ghostman build process...")
            
            # Pre-build steps
            self.check_dependencies()
            self.clean_build_dirs()
            self.install_dependencies()
            
            # Build
            self.build_executable()
            
            # Post-build validation
            validation_results = self.validate_build()
            self.save_build_report(validation_results)
            
            self.log("Build completed successfully!")
            return True
            
        except Exception as e:
            self.log(f"Build failed: {e}", "ERROR")
            if self.debug:
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build Ghostman AI Overlay Application")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-clean", action="store_true", help="Don't clean build directories")
    
    args = parser.parse_args()
    
    builder = GhostmanBuilder(debug=args.debug, clean=not args.no_clean)
    success = builder.build()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()