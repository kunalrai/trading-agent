@echo off
echo Starting Paper Trading Monitor...
echo.
echo 📈 PAPER TRADING CONFIGURATION:
echo - Initial Balance: $1000 USDT
echo - Symbol: ZEC/USDT
echo - Position Size: 10%% per trade
echo - Max Positions: 3
echo - Risk per Trade: 2%% of portfolio
echo - Check Interval: 1 minute
echo.
echo Features:
echo - Automatic entry/exit based on signals
echo - Stop loss and take profit management
echo - Portfolio tracking and P&L monitoring
echo - Risk management and position sizing
echo.
echo Press Ctrl+C to stop paper trading
echo.
cd /d "c:\apps\repo\trading-agent"
C:/apps/repo/trading-agent/venv/Scripts/python.exe trade.py --paper-trade
pause