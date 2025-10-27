# SolSignals - Cryptocurrency Trading Signal Monitor

A comprehensive cryptocurrency trading signal monitoring system that tracks price movements against EMA indicators across multiple exchanges with a modern web dashboard interface.

## 🚀 Features

### Real-Time Monitoring
- **Multi-Exchange Support**: Binance and CoinDCX integration
- **EMA-Based Signals**: 50-period exponential moving average analysis
- **Breakout Detection**: Customizable price distance thresholds
- **Live Data Streaming**: Real-time price updates every 15 minutes

### Web Dashboard
- **Modern UI**: Responsive design with dark theme and SolSignals branding
- **Interactive Charts**: Real-time price and EMA visualization
- **Signal History**: Complete trading signal timeline with detailed metrics
- **Coin Details**: Individual cryptocurrency analysis pages
- **Settings Management**: Customizable scanning parameters and notifications

### Technical Analysis
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic Oscillator
- **Custom Alerts**: Price threshold and volume spike notifications
- **Multiple Timeframes**: 1h, 4h, 1d analysis periods
- **Signal Strength**: Confidence scoring for trading signals

### Data Management
- **SQLite Database**: Persistent storage for all trading data
- **Settings Persistence**: User preferences saved across sessions
- **Historical Data**: Price history and signal tracking
- **Data Cleanup**: Automated old data removal

## 📁 Project Structure

```
solsignals/
├── app.py                 # Core trading signal monitor
├── web_dashboard.py       # Flask web application
├── database.py           # SQLite database management
├── requirements.txt      # Python dependencies
├── start_dashboard.bat   # Windows batch starter
├── .env.example         # Environment variables template
├── exchanges/           # Exchange connectors
│   ├── __init__.py
│   ├── base_exchange.py
│   ├── binance_exchange.py
│   ├── coindcx_exchange.py
│   └── factory.py
├── static/             # Web assets
│   ├── css/
│   │   ├── dashboard.css
│   │   └── base.css
│   └── js/
│       ├── dashboard.js
│       ├── base.js
│       └── tailwind.config.js
└── templates/          # HTML templates
    ├── base.html
    ├── sidebar_layout.html
    ├── index.html
    ├── coindetail.html
    ├── scan_settings.html
    └── dashboard.html
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Git (for cloning the repository)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd solsignals
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   copy .env.example .env
   # Edit .env file with your API keys
   ```

5. **Required API Keys**
   - **Binance**: Get from [Binance API](https://www.binance.com/en/support/faq/360002502072)
   - **CoinDCX**: Get from [CoinDCX API](https://coindcx.com/api-docs)

   Add to `.env` file:
   ```
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_SECRET_KEY=your_binance_secret_key
   COINDCX_API_KEY=your_coindcx_api_key
   COINDCX_SECRET_KEY=your_coindcx_secret_key
   ```

## 🚀 Usage

### Running the Web Dashboard

**Option 1: Using batch file (Windows)**
```bash
start_dashboard.bat
```

**Option 2: Manual start**
```bash
python web_dashboard.py
```

The web dashboard will be available at: `http://localhost:5000`

### Running Core Signal Monitor
```bash
python app.py
```

### Web Interface Features

#### Main Scanner (`/`)
- Real-time breakout signal detection
- Live price monitoring for multiple cryptocurrencies
- Signal strength indicators and trend analysis

#### Settings Page (`/settings`)
- **Scanning Parameters**: Breakout threshold, volume thresholds, timeframes
- **Technical Indicators**: Enable/disable RSI, MACD, Bollinger Bands, Stochastic
- **Notifications**: Email, desktop, and mobile push notifications
- **Watchlist Management**: Add/remove cryptocurrencies to monitor

#### Coin Details (`/coin/<symbol>`)
- Individual cryptocurrency analysis
- Price charts with EMA overlays
- Historical signal timeline
- Technical indicator values

#### Dashboard (`/dashboard`)
- System overview and statistics
- Database metrics and performance
- Real-time data status

## ⚙️ Configuration

### Scanning Parameters
- **Breakout Threshold**: 1-20% price distance from EMA
- **Volume Threshold**: 50-500% volume increase detection
- **Timeframe**: 1h, 4h, or 1d analysis periods

### Technical Indicators
- **RSI**: Relative Strength Index (14-period)
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Price volatility bands
- **Stochastic Oscillator**: Momentum indicator

### Notification Settings
- **Email Notifications**: SMTP-based email alerts
- **Desktop Notifications**: Browser push notifications
- **Mobile Notifications**: Mobile device alerts

## 🗄️ Database Schema

### Tables
- **price_data**: Real-time price and EMA data
- **trading_signals**: Generated buy/sell signals
- **alerts**: User-defined alert conditions
- **settings**: User preferences and configuration

### Data Retention
- Automatic cleanup of data older than 30 days
- Configurable retention periods
- VACUUM operations for database optimization

## 🔧 API Endpoints

### Settings Management
- `GET /api/settings` - Retrieve all settings
- `POST /api/settings` - Save settings to database

### Real-Time Data
- `GET /api/scanner-data` - Live scanner data
- `GET /api/coin-data/<symbol>` - Individual coin data
- `GET /api/dashboard-data` - Dashboard metrics

### Signal Data
- `GET /api/signals` - Recent trading signals
- `GET /api/chart-data/<symbol>` - Chart data for visualization

## 🎨 Frontend Technology

### Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Custom Theme**: SolSignals branding with primary color #13a4ec
- **Responsive Design**: Mobile-first approach
- **Dark Theme**: Professional dark interface

### JavaScript
- **Vanilla JS**: No heavy frameworks, optimized performance
- **Modular Architecture**: Organized in SolSignals namespace
- **Real-Time Updates**: WebSocket-like functionality for live data
- **Template Inheritance**: Jinja2-based template system

## 🔍 Monitoring & Alerts

### Signal Detection
1. Fetch latest OHLCV data from exchange
2. Calculate 50-period EMA
3. Check price position relative to EMA
4. Validate volume increase thresholds
5. Generate signal if conditions met

### Alert System
- Price crosses EMA alerts
- Volume spike notifications
- Custom threshold alerts
- Multi-channel notification delivery

## 📊 Performance & Scaling

### Data Management
- SQLite for development/small scale
- Indexed queries for fast data retrieval
- Automatic data archival and cleanup
- Connection pooling for concurrent access

### Monitoring Intervals
- **Price Updates**: Every 15 minutes
- **Signal Generation**: Real-time on price updates
- **Database Cleanup**: Daily at midnight
- **Health Checks**: Continuous monitoring

## 🛡️ Security Considerations

### API Key Security
- Environment variables for sensitive data
- No hardcoded credentials in source code
- API key rotation recommendations

### Data Protection
- Input validation on all endpoints
- SQL injection prevention
- XSS protection in templates

## 🚦 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check if database file exists and permissions
ls -la trading_data.db
```

**API Connection Issues**
```bash
# Verify API keys in .env file
# Check network connectivity
# Validate exchange API status
```

**Web Dashboard Not Loading**
```bash
# Check if port 5000 is available
# Verify Flask installation
# Check console for JavaScript errors
```

### Debug Mode
Set `DEBUG=True` in environment variables for detailed error logging.

### Log Files
Application logs are written to console. Redirect to file for production:
```bash
python web_dashboard.py > solsignals.log 2>&1
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the API documentation

## 🏗️ Architecture

### Core Components

1. **Signal Monitor (`app.py`)**
   - Continuous price monitoring
   - EMA calculation engine
   - Signal generation logic

2. **Web Dashboard (`web_dashboard.py`)**
   - Flask-based web server
   - RESTful API endpoints
   - Template rendering engine

3. **Database Layer (`database.py`)**
   - SQLite ORM wrapper
   - Data persistence management
   - Query optimization

4. **Exchange Connectors (`exchanges/`)**
   - Unified API interface
   - Multi-exchange support
   - Error handling and retry logic

### Data Flow
```
Exchange APIs → Data Normalization → Signal Analysis → Database Storage → Web Interface
```

## 📈 Future Roadmap

- [ ] Additional exchange integrations
- [ ] Advanced technical indicators
- [ ] Machine learning signal enhancement
- [ ] Mobile application
- [ ] Portfolio tracking features
- [ ] Social trading features
- [ ] WebSocket real-time updates
- [ ] Advanced charting capabilities

---

**SolSignals** - Your gateway to intelligent cryptocurrency trading signals.