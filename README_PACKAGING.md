# Ghostman Packaging Guide

This guide provides step-by-step instructions for packaging the Ghostman AI Overlay application into a standalone executable using PyInstaller.

## Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- All dependencies installed: `pip install -r requirements.txt`
- PyInstaller: `pip install pyinstaller`

### 2. Simple Build
```bash
# Windows
scripts\build.bat

# Or using Python directly
python scripts\build.py
```

### 3. Output
- Executable: `dist\Ghostman.exe`
- SHA256 hash: `dist\Ghostman.exe.sha256`
- Build report: `dist\build_report.json`

## Advanced Building

### Debug Build
```bash
# Windows
scripts\build.bat --debug

# Python
python scripts\build.py --debug
```

### Custom Build Options
```bash
# Don't clean previous builds
python scripts\build.py --no-clean

# Debug mode with no clean
python scripts\build.py --debug --no-clean
```

## Files Overview

### Core Build Files
- `Ghostman.spec` - Main PyInstaller specification file
- `version_info.txt` - Windows version information
- `ghostman.exe.manifest` - Windows manifest (no admin rights)

### Build Scripts
- `scripts\build.py` - Advanced Python build script
- `scripts\build.bat` - Simple Windows batch script
- `scripts\detect_hidden_imports.py` - Import analysis tool
- `scripts\test_build.py` - Build testing and validation

### Configuration Features
- **Single File Executable** - Everything bundled into one `.exe`
- **No Admin Rights Required** - Uses `asInvoker` execution level
- **High DPI Support** - Proper scaling on high-DPI displays
- **Complete Dependency Bundling** - All Python libraries included
- **Hidden Import Detection** - Automatically handles PyQt6, OpenAI, requests

## Build Process Details

### 1. Dependency Analysis
The build process automatically detects and includes:
- PyQt6 and all required Qt modules
- OpenAI library with HTTP clients (httpx, requests)
- SSL certificates for HTTPS requests
- Pydantic for data validation
- TOML configuration support

### 2. Size Optimization
- Excludes unused Qt bindings (PySide2/6, PyQt5)
- Removes development tools (pytest, unittest, etc.)
- Excludes large scientific libraries if not used
- UPX compression disabled for PyQt6 compatibility

### 3. Windows Compatibility
- Supports Windows 7 through Windows 11
- No UAC prompts required
- Proper DPI awareness
- Windows Defender friendly configuration

## Testing Your Build

### Automated Testing
```bash
# Test the built executable
python scripts\test_build.py

# Test with verbose output
python scripts\test_build.py --verbose

# Custom executable path
python scripts\test_build.py path\to\your\app.exe
```

### Manual Testing
1. **Basic Launch**: Double-click `dist\Ghostman.exe`
2. **Command Line**: Run `dist\Ghostman.exe --help`
3. **Antivirus**: Check that Windows Defender doesn't flag it
4. **Performance**: Monitor startup time and memory usage

## Troubleshooting

### Common Issues

#### "Failed to execute script"
**Cause**: Missing hidden imports
**Solution**: 
```bash
# Analyze your project for missing imports
python scripts\detect_hidden_imports.py --spec-snippet
```

#### Large executable size (>200MB)
**Cause**: Unnecessary dependencies included
**Solution**: 
1. Review `excludes` list in `Ghostman.spec`
2. Use virtual environment with only required packages

#### SSL/HTTPS errors
**Cause**: Missing certificates
**Solution**: Already handled in `Ghostman.spec` - certificates are bundled

#### Slow startup time
**Cause**: Large number of dependencies
**Solutions**:
1. Use lazy imports in your code
2. Consider Nuitka for better performance
3. Profile your application startup

### Debug Mode
Enable debug mode for detailed error information:
```bash
python scripts\build.py --debug
```

This creates a console version that shows detailed error messages.

## Alternative Packaging Tools

### Nuitka (Performance Option)
```bash
pip install nuitka
nuitka --onefile --enable-plugin=pyqt6 --windows-disable-console ghostman/src/main.py
```
- **Pros**: 2-3x faster startup, better performance
- **Cons**: Very long compile times (30+ minutes), larger size

### cx_Freeze (Cross-platform)
See `packaging_research.md` for detailed cx_Freeze configuration.

## Distribution

### Code Signing (Optional but Recommended)
```bash
# Sign your executable to reduce Windows SmartScreen warnings
signtool sign /f certificate.pfx /p password /t http://timestamp.comodoca.com /v dist\Ghostman.exe
```

### Release Preparation
1. Test on clean Windows systems
2. Create installation instructions
3. Provide SHA256 checksums
4. Consider using GitHub Releases or similar

## CI/CD Integration

The project includes GitHub Actions workflow in `packaging_research.md` for:
- Automated builds on multiple platforms
- Code signing integration
- Release asset creation
- Build validation

## Performance Benchmarks

Typical results for Ghostman-like applications:
- **Executable Size**: 80-120 MB
- **Startup Time**: 2-3 seconds
- **Build Time**: 30 seconds - 2 minutes
- **Memory Usage**: 50-100 MB at startup

## Support

For packaging issues:
1. Check this guide and `packaging_research.md`
2. Run the import analyzer: `python scripts\detect_hidden_imports.py`
3. Test with debug mode: `python scripts\build.py --debug`
4. Review PyInstaller documentation: https://pyinstaller.org/

## Advanced Configuration

### Custom Spec File Modifications
Edit `Ghostman.spec` to:
- Add more hidden imports
- Include additional data files
- Modify exclusions list
- Change executable options

### Environment Variables
Set these before building:
```bash
set PYTHONOPTIMIZE=2          # Remove docstrings and assertions
set PYTHONDONTWRITEBYTECODE=1 # Don't create .pyc files
```

### Build Validation
The build process includes automatic validation:
- File existence and size checks
- SHA256 hash generation
- Basic execution testing
- Performance metrics

This ensures your executable is properly built and ready for distribution.