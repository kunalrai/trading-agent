@echo off
echo.
echo  ===================================================
echo   SolSignals - Starting Application with Virtual Environment
echo  ===================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please create it first.
    echo Run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Verify Python is using virtual environment
echo [INFO] Using Python from:
where python

echo.
echo [START] Starting SolSignals Application...
echo.
echo  Available URLs:
echo  - Home/Index: http://localhost:5000/
echo  - Dashboard: http://localhost:5000/dashboard  
echo  - Coin Scanner: http://localhost:5000/scanner
echo  - Health Check: http://localhost:5000/health
echo.
echo  Press Ctrl+C to stop the server
echo.

REM Start the Flask application
python app.py

pause