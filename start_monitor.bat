@echo off
echo ===============================================
echo SOL/USDT Trading Monitor - Quick Start Menu
echo ===============================================
echo.
echo Select monitoring option:
echo.
echo 1. Single Check (one-time signal check)
echo 2. Continuous Monitor (every 15 minutes)
echo 3. Fast Monitor (every 5 minutes)
echo 4. Web Dashboard (browser-based)
echo 5. Desktop Alerts (notifications)
echo 6. View Current Signal
echo 7. View Formatted Analysis
echo 8. Exit
echo.
set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" (
    echo Running single check...
    python monitor.py once
    pause
    goto menu
)

if "%choice%"=="2" (
    echo Starting continuous monitoring (15 min intervals)...
    python monitor.py
    pause
    goto menu
)

if "%choice%"=="3" (
    echo Starting fast monitoring (5 min intervals)...
    python monitor.py fast
    pause
    goto menu
)

if "%choice%"=="4" (
    echo Starting web dashboard...
    echo Dashboard will be available at: http://localhost:5000
    echo Press Ctrl+C to stop the dashboard
    python dashboard.py
    pause
    goto menu
)

if "%choice%"=="5" (
    echo Starting desktop alert system...
    python alerts.py desktop
    pause
    goto menu
)

if "%choice%"=="6" (
    echo Getting current trading signal...
    python ema9_api.py trade-formatted
    pause
    goto menu
)

if "%choice%"=="7" (
    echo Getting formatted analysis...
    python ema9_api.py formatted
    pause
    goto menu
)

if "%choice%"=="8" (
    echo Goodbye!
    exit
)

echo Invalid choice. Please try again.
pause

:menu
cls
goto start

:start
goto menu