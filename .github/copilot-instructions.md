# SolSignals - Copilot Instructions

## Project Overview
This is a cryptocurrency trading signal monitoring system that tracks SOL/USDT price movements against EMA indicators on Binance. The application runs as a continuous monitoring service that checks conditions every 15 minutes.

## Architecture
- **Single-file application**: `app.py` contains the entire trading logic
- **Real-time monitoring**: Continuous loop with 15-minute intervals
- **Technical analysis**: Custom EMA calculation and price-distance conditions
- **Exchange integration**: Uses ccxt library for Binance API connectivity

## Key Dependencies
- `ccxt`: Cryptocurrency exchange connector (likely needs installation via `pip install ccxt`)
- `time`: Standard library for sleep intervals

## Core Components

### Data Flow
1. Fetch latest OHLCV candle data from Binance
2. Retrieve 50 historical candles for EMA calculation  
3. Calculate 50-period EMA using custom algorithm
4. Check if price > EMA and distance ≤ threshold (5 USDT)
5. Print alert if conditions met, then sleep 15 minutes

### Key Functions
- `get_latest_ohlcv()`: Fetches most recent candle data
- `calculate_ema()`: Custom exponential moving average implementation
- `check_conditions()`: Validates price position relative to EMA with distance threshold

## Project Patterns

### Configuration Approach
- Hardcoded symbol (`SOL/USDT`) and parameters (50-period EMA, 5 USDT threshold)
- 15-minute timeframe and check intervals
- Direct variable assignment rather than config files

### Error Handling
- No explicit error handling currently implemented
- API failures or network issues will crash the application

### Development Workflow
- Run directly with: `python app.py`
- No build process or test suite
- Manual monitoring via console output

## Technical Considerations
- EMA calculation starts with SMA for initial period, then applies exponential smoothing
- Uses index 4 from OHLCV arrays (close price)
- Sleep duration (900 seconds) matches 15-minute candle timeframe
- Exchange initialization happens once at startup

## Extension Points
- Alert mechanism placeholder: "You can add an email alert or notification here"
- Threshold parameter is configurable in `check_conditions()`
- Symbol can be changed but requires code modification
- Additional technical indicators could follow similar pattern

## Common Tasks
- **Add new trading pairs**: Modify `symbol` variable
- **Adjust sensitivity**: Change `threshold` parameter in condition check
- **Add notifications**: Implement alert system in condition block
- **Error handling**: Wrap exchange calls in try-catch blocks
- **Configuration**: Extract hardcoded values to config file or environment variables