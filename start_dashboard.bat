@echo off
echo ================================================
echo 🚀 Trading Dashboard with Paper Trading
echo ================================================
echo.
echo Dashboard Features:
echo • Portfolio Performance Chart (like your screenshot)
echo • Real-time Paper Trading with $1000 USDT
echo • Automated Position Management
echo • Live P&L Tracking and Analytics
echo • Trade History and Export
echo • PostgreSQL Database Integration
echo.
echo Dashboard will be available at:
echo 🌐 http://localhost:5000
echo.
echo Instructions:
echo 1. Wait for "Running on http://0.0.0.0:5000" message
echo 2. Dashboard will open automatically in browser
echo 3. Click "Start Trading" to begin automated paper trading
echo 4. Press Ctrl+C here to stop the dashboard
echo.
echo Opening dashboard in browser...
timeout /t 3 /nobreak >nul
start http://localhost:5000
echo.
echo Starting Trading Dashboard...
echo.

C:/apps/repo/trading-agent/venv/Scripts/python.exe dashboard_app.py

pause