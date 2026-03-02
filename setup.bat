@echo off
setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════╗
echo ║   ScholArx - Environment Setup         ║
echo ╚═══════════════════════════════════════╝
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ✘ Python not found. Please install Python 3.9+ 
    pause
    exit /b 1
)

:: Create .venv
if not exist .venv (
    echo [1/3] Creating virtual environment (.venv)...
    python -m venv .venv
    echo ✓ Environment created.
) else (
    echo ✓ Virtual environment already exists.
)

:: Install Dependencies
echo [2/3] Installing dependencies from requirements.txt...
echo (This may take a few minutes for ML libraries like torch)
echo.

:: Use the venv's pip specifically to avoid global conflicts
call .venv\Scripts\activate.bat && (
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

if %errorlevel% neq 0 (
    echo.
    echo ✘ FAILED: Installation encountered an error.
    pause
    exit /b 1
)

echo.
echo [3/3] Finalizing...
echo ✓ All dependencies installed successfully.
echo.
echo ========================================================
echo SUCCESS: ScholArx is ready.
echo To start: run start.bat
echo ========================================================
echo.
pause
