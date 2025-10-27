@echo off
echo.
echo  ===================================================
echo   SolSignals - Crypto Trading Dashboard Launcher
echo  ===================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [SETUP] Installing/updating dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed to install
)

REM Copy environment file if it doesn't exist
if not exist ".env" (
    echo [CONFIG] Creating .env file from example...
    copy .env.example .env >nul
    echo [INFO] Please edit .env file to configure your settings
    echo.
)

REM Run quick test
echo [TEST] Running quick environment test...
python test_dashboard.py
if errorlevel 1 (
    echo [ERROR] Environment test failed
    pause
    exit /b 1
)

echo.
echo [START] Starting SolSignals Dashboard...
echo.
echo  Dashboard URLs (Consistent Design):
echo  - Home/Index: http://localhost:5000/
echo  - Dashboard: http://localhost:5000/dashboard  
echo  - Scanner: http://localhost:5000/scanner
echo  - Health: http://localhost:5000/health
echo.
echo  All pages now follow the same layout and navigation!
echo  Press Ctrl+C to stop the server
echo.

python web_dashboard.py

pause