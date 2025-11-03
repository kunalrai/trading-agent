# CoinDCX Market Scanner Dashboard

A modern web dashboard for scanning and analyzing CoinDCX futures markets with real-time confidence scoring.

## Features

- **Real-time Market Scanning**: Scan all active CoinDCX futures instruments
- **Multi-timeframe Analysis**: 5-minute short-term and 4-hour long-term signals
- **Confidence Scoring**: Combined confidence scores with alignment bonuses
- **Interactive Dashboard**: Modern web interface with live progress updates
- **Export Capabilities**: Export results to HTML files
- **Volume Filtering**: Focus on truly tradable symbols based on volume

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Dashboard**:
   ```bash
   python scanner_dashboard.py
   ```

3. **Access the Dashboard**:
   Open your browser and go to: http://localhost:5000

## Dashboard Features

### Scan Controls
- **Quick Scan**: Analyze top 15 high-volume symbols
- **Medium Scan**: Analyze top 30 high-volume symbols
- **Full Scan**: Analyze all available symbols (may take longer)
- **Volume Filter**: Set minimum volume threshold for tradable symbols

### Real-time Status
- Live progress updates during scanning
- Current symbol being analyzed
- Scan completion status

### Results Display
- Comprehensive table with all analysis results
- Signal indicators (LONG/SHORT/FLAT)
- Confidence scores with color coding
- Price and volume information
- Error handling for failed analyses

### Export Options
- Export current results to HTML file
- Professional formatting with charts and statistics

## API Endpoints

- `GET /` - Main dashboard
- `POST /scan` - Start a market scan
- `GET /scan_status` - Get current scan status
- `GET /results` - Get scan results as JSON
- `GET /export_html` - Export results to HTML file
- `GET /api/symbols/<symbol>` - Get detailed analysis for specific symbol

## Technical Details

- **Backend**: Flask web framework
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Modern gradient design with Font Awesome icons
- **Real-time Updates**: AJAX polling for live status updates
- **Responsive**: Mobile-friendly design

## Configuration

The dashboard uses the same configuration as the main trading system. Make sure your CoinDCX API credentials are properly configured in the main application.

## Usage Examples

### Start a Quick Scan
1. Select "Quick Scan" from the dropdown
2. Set minimum volume (default: $50,000)
3. Click "Start Market Scan"
4. Watch real-time progress updates
5. View results in the table

### Export Results
1. After a scan completes, click "Export to HTML"
2. The system will generate `market_scan_results.html`
3. Open the file in your browser for a detailed report

### Monitor High Confidence Signals
- Look for signals with ≥80% confidence
- These are highlighted in the results table
- Consider these for trading opportunities

## Troubleshooting

- **No symbols found**: Check your CoinDCX API connection
- **Scan fails**: Verify API credentials and network connection
- **Slow performance**: Reduce scan size or increase volume filter
- **Browser issues**: Ensure JavaScript is enabled for real-time updates

## Security Note

This dashboard is intended for local development and testing. For production use, implement proper authentication and security measures.