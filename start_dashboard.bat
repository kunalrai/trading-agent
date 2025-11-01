@echo off
echo ================================================
echo 🚀 SOL/USDT Trading Monitor Dashboard Launcher
echo ================================================
echo.
echo Dashboard Features:
echo • Real-time price monitoring every 15 minutes
echo • RSI indicators with visual gauges  
echo • Live trading signal detection and alerts
echo • Signal history and monitoring log
echo • Automatic notifications when signals detected
echo.
echo Dashboard will be available at:
echo 🌐 http://localhost:5001
echo.
echo Instructions:
echo 1. Wait for "Running on http://0.0.0.0:5001" message
echo 2. Open your browser to http://localhost:5001
echo 3. Click "Start Monitoring" to begin real-time monitoring
echo 4. Press Ctrl+C here to stop the dashboard
echo.
echo Starting enhanced monitor dashboard...
echo.

python monitor_dashboard.py

pause