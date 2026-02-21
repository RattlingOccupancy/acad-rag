@echo off
REM Quick start script for RAG system (Windows)

echo.
echo ╔═══════════════════════════════════════╗
echo ║   RAG System - Quick Start             ║
echo ╚═══════════════════════════════════════╝
echo.

REM Check if we have required tools
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ✘ Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ✘ npm not found. Please install Node.js
    pause
    exit /b 1
)

echo ✓ Python and npm found
echo.
echo Starting services...
echo.

REM Start backend in a new window
echo [1/2] Starting Backend (FastAPI on port 8000)...
start cmd /k "cd backend && python -m pip install fastapi uvicorn python-multipart -q && python -m uvicorn api:app --reload --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start frontend in a new window
echo [2/2] Starting Frontend (Vite on port 5173)...
start cmd /k "cd frontend && npm install -q && npm run dev"

echo.
echo ✓ Services starting...
echo.
echo Frontend:  http://localhost:5173
echo Backend:   http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo.
echo Close the terminal windows to stop services
echo.
pause
