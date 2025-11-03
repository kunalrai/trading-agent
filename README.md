# CoinDCX Futures Trading Agent 🚀

A sophisticated Python-based trading analysis system that fetches real-time data from CoinDCX futures API, calculates technical indicators, and provides high-confidence trading signals with automated entry, take profit, and stop loss levels.

## Features ✨

- **Real-time CoinDCX Futures Data**: Fetches live market data using CoinDCX API endpoints
- **Advanced Technical Analysis**: 
  - EMA (20, 50 periods)
  - MACD (12, 26, 9 periods)
  - RSI (7, 14 periods)
  - ATR (3, 14 periods)
  - Volume analysis
- **Multi-timeframe Analysis**: 
  - 5-minute intraday analysis
  - 4-hour longer-term context
- **Intelligent Signal Generation**: Only provides trade signals when confidence ≥ 80%
- **Automated Risk Management**: Calculates entry, TP, SL based on ATR and risk-reward ratios
- **Continuous Monitoring**: Monitor trades every 5 minutes with updated analysis

## Quick Start 🏃‍♂️

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd trading-agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Analysis

#### Single Analysis
```bash
python app.py
```

#### Continuous Monitoring (every 5 minutes)
```bash
python app.py --monitor
```

#### Demo with Sample Data
```bash
# Basic demo
python demo.py

# High confidence signals demo
python high_confidence_demo.py
```

## API Usage 📊

The system uses CoinDCX's public futures API endpoints:

### Active Futures Instruments
```
GET https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments?margin_currency_short_name[]=USDT
```

### Real-time Futures Prices
```
GET https://public.coindcx.com/market_data/v3/current_prices/futures/rt
```

### Candlestick Data
```
GET https://public.coindcx.com/market_data/candlesticks?pair=B-BTC_USDT&resolution=5&pcode=f
```

## Configuration ⚙️

### Monitored Coins
Default top 5 coins (can be modified in `app.py`):
- BTC/USDT
- ETH/USDT 
- SOL/USDT
- BNB/USDT
- ADA/USDT

### Trading Parameters
```python
self.confidence_threshold = 80  # Minimum confidence for trade signals
self.risk_reward_ratio = 2.0    # Risk:Reward ratio (1:2)
```

## Example Output 📈

When the system detects a high-confidence trading opportunity:

```
🔥 HIGH CONFIDENCE TRADE SIGNALS (≥80%)
================================================================================

1. 📈 LONG SOL/USDT - 95% Confidence
   📍 Entry: $195.50
   🎯 TP: $209.90 (+$14.40)
   🛡️ SL: $188.30 (-$7.20)
   ⚖️ Risk:Reward = 1:2.0

   📋 EXECUTION INSTRUCTIONS:
      • Enter LONG position at $195.50
      • Set Take Profit at $209.90
      • Set Stop Loss at $188.30
```

## Technical Indicator Logic 🧮

### Signal Generation
The system generates LONG/SHORT/FLAT signals based on:

1. **Price vs EMA Analysis** (30 points max)
   - Price > EMA20 > EMA50 = Strong LONG signal
   - Price < EMA20 < EMA50 = Strong SHORT signal

2. **MACD Momentum** (25 points max)
   - MACD > 30 = Strong bullish momentum
   - MACD < -30 = Strong bearish momentum

3. **RSI Levels** (40 points max)
   - RSI7 < 25 = Severely oversold (LONG)
   - RSI7 > 75 = Severely overbought (SHORT)
   - RSI14 confirmation adds extra confidence

4. **Volume Confirmation** (15 points max)
   - Volume > 1.5x average = Strong confirmation
   - Volume < 0.5x average = Warning signal

5. **Price Momentum** (15 points max)
   - Recent trend analysis over multiple periods

### Confidence Calculation
- Base score from individual indicators
- Bonus for signal alignment (multiple indicators agreeing)
- Only signals with ≥80% confidence are actionable

### Risk Management
- **Entry**: Current market price
- **Stop Loss**: Entry ± (1.5 × ATR14)
- **Take Profit**: Entry ± (3.0 × ATR14) for 1:2 risk-reward
- **Position Size**: Calculated based on risk per trade

## File Structure 📁

```
trading-agent/
├── app.py                     # Main trading analysis system
├── demo.py                    # Demo with sample data
├── high_confidence_demo.py    # High confidence signals demo
├── exchanges/
│   ├── __init__.py
│   ├── base_exchange.py      # Base exchange interface
│   ├── coindcx_exchange.py   # CoinDCX API implementation
│   └── factory.py            # Exchange factory
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Market Context Display 📊

### Intraday Series (5-minute timeframe)
```
Mid prices: [110188.0, 110187.0, 110226.0, 110209.0, 110236.5]
EMA20: [110149.948, 110153.001, 110161.096, 110165.468, 110187.564]
MACD: [46.83, 43.344, 44.586, 42.579, 33.907]
RSI(7): [52.012, 64.533, 55.227, 50.312, 60.921]
RSI(14): [57.968, 63.458, 58.874, 56.329, 53.06]
```

### Longer-term Context (4-hour timeframe)
```
20-Period EMA: 110,389.719 vs. 50-Period EMA: 111,034.958
3-Period ATR: 444.048 vs. 14-Period ATR: 721.016
Current Volume: 53.457 vs. Average Volume: 4329.191
MACD: -657.601
RSI(14): 46.748
```

## Important Notes ⚠️

1. **Paper Trading First**: Always test strategies with paper trading before live trading
2. **Risk Management**: Never risk more than you can afford to lose
3. **Market Volatility**: Crypto markets are highly volatile - use appropriate position sizes
4. **API Limits**: CoinDCX has rate limits - the system includes delays to respect them
5. **Internet Connection**: Requires stable internet for real-time data
6. **No Financial Advice**: This tool is for educational purposes - not financial advice

## Monitoring Workflow 🔄

1. **Every 5 minutes**: System fetches fresh market data
2. **Calculate Indicators**: Technical analysis on latest price data
3. **Generate Signals**: Confidence-based signal generation
4. **Risk Assessment**: Automatic TP/SL calculation
5. **Display Results**: Formatted output with trade instructions
6. **Continuous Loop**: Repeat process for ongoing monitoring

## Customization Options 🛠️

### Add New Coins
```python
self.top_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'YOUR_COIN/USDT']
```

### Adjust Confidence Threshold
```python
self.confidence_threshold = 85  # Require 85% confidence
```

### Modify Risk-Reward Ratio
```python
self.risk_reward_ratio = 3.0  # 1:3 risk-reward ratio
```

### Change Monitoring Interval
```python
trader.run_continuous_monitoring(interval_minutes=3)  # Every 3 minutes
```

## Troubleshooting 🔧

### Common Issues
1. **No data available**: Check internet connection and CoinDCX API status
2. **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
3. **Rate limiting**: System includes delays, but reduce monitoring frequency if needed
4. **Low confidence signals**: Market may be ranging - wait for clear trends

### Debug Mode
Add more verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer ⚠️

**This software is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always conduct your own research and consider consulting with a qualified financial advisor before making investment decisions.**

---

*Happy Trading! 🚀📈*