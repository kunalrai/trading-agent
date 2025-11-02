@echo off
echo Starting Continuous Trading Signal Monitor...
echo.
echo Configuration from .env:
echo - Symbol: ZEC/USDT
echo - Check Interval: 1 minute
echo - Timeframe: 5m
echo - EMA Period: 50
echo.
echo Press Ctrl+C to stop monitoring
echo.
cd /d "c:\apps\repo\trading-agent"
C:/apps/repo/trading-agent/venv/Scripts/python.exe trade.py --continuous
pause