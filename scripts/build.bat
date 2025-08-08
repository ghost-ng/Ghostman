@echo off
REM Ghostman Build Script for Windows
REM This script provides a simple interface to build the Ghostman executable

setlocal EnableDelayedExpansion

echo ==========================================
echo    Ghostman AI Overlay - Build Script
echo ==========================================

REM Change to project root directory
cd /d "%~dp0\.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ and add it to your PATH
    pause
    exit /b 1
)

REM Parse command line arguments
set DEBUG_MODE=0
set CLEAN_BUILD=1

:parse_args
if "%~1"=="--debug" (
    set DEBUG_MODE=1
    shift
    goto parse_args
)
if "%~1"=="--no-clean" (
    set CLEAN_BUILD=0
    shift
    goto parse_args
)
if "%~1"=="--help" (
    goto show_help
)
if "%~1"=="/?" (
    goto show_help
)
if not "%~1"=="" (
    echo Unknown argument: %~1
    goto show_help
)

REM Display build configuration
echo Build Configuration:
if %DEBUG_MODE%==1 (
    echo   - Debug Mode: ENABLED
) else (
    echo   - Debug Mode: DISABLED
)
if %CLEAN_BUILD%==1 (
    echo   - Clean Build: ENABLED
) else (
    echo   - Clean Build: DISABLED
)
echo.

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    if errorlevel 1 (
        echo WARNING: Failed to activate virtual environment
    ) else (
        echo Virtual environment activated
    )
) else (
    echo No virtual environment found, using system Python
)

REM Run the Python build script
set BUILD_ARGS=
if %DEBUG_MODE%==1 set BUILD_ARGS=%BUILD_ARGS% --debug
if %CLEAN_BUILD%==0 set BUILD_ARGS=%BUILD_ARGS% --no-clean

echo Starting build process...
python scripts\build.py%BUILD_ARGS%

set BUILD_RESULT=%errorlevel%

REM Display results
echo.
echo ==========================================
if %BUILD_RESULT%==0 (
    echo           BUILD SUCCESSFUL!
    echo ==========================================
    echo.
    echo Executable location: dist\Ghostman.exe
    
    if exist "dist\Ghostman.exe" (
        for %%F in (dist\Ghostman.exe) do (
            set /a SIZE_MB=%%~zF/1024/1024
            echo Executable size: !SIZE_MB! MB
        )
    )
    
    if exist "dist\Ghostman.exe.sha256" (
        echo SHA256 hash file: dist\Ghostman.exe.sha256
    )
    
    if exist "dist\build_report.json" (
        echo Build report: dist\build_report.json
    )
    
    echo.
    echo You can now run: dist\Ghostman.exe
    
) else (
    echo            BUILD FAILED!
    echo ==========================================
    echo.
    echo Check the output above for error details.
    echo For more verbose output, try: %~nx0 --debug
)

echo.
echo Press any key to continue...
pause >nul
exit /b %BUILD_RESULT%

:show_help
echo.
echo Usage: %~nx0 [OPTIONS]
echo.
echo OPTIONS:
echo   --debug      Enable debug mode for detailed output
echo   --no-clean   Don't clean build directories before building
echo   --help       Show this help message
echo.
echo Examples:
echo   %~nx0                 # Standard build
echo   %~nx0 --debug         # Debug build with verbose output
echo   %~nx0 --no-clean      # Build without cleaning previous artifacts
echo.
pause
exit /b 0