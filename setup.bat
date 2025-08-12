@echo off
REM Quick setup script for Windows users
echo Bilbasen Fiat Panda Finder - Windows Setup
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+ first.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
echo [INFO] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements-dev.txt

REM Install Playwright browsers
echo [INFO] Installing Playwright browsers...
playwright install

REM Create runtime directories
echo [INFO] Creating runtime directories...
mkdir runtime\data 2>nul
mkdir runtime\fixtures 2>nul  
mkdir runtime\logs 2>nul
mkdir runtime\cache 2>nul
mkdir runtime\temp 2>nul

echo.
echo ========================================
echo ✅ Setup completed successfully!
echo.
echo Next steps:
echo 1. Run: venv\Scripts\activate.bat
echo 2. Run: python launch.py
echo 3. Visit: http://127.0.0.1:8001
echo.
pause