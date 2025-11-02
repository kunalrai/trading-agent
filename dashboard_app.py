#!/usr/bin/env python3
"""
Trading Dashboard Flask Application
Provides web interface for paper trading system with PostgreSQL database
"""

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
from trade import TradeSignalGenerator, PaperTradingEngine, TechnicalAnalyzer
import threading
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trading.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)

# Database Models
class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_value = db.Column(db.Float, default=1000.0)
    cash_balance = db.Column(db.Float, default=1000.0)
    unrealized_pnl = db.Column(db.Float, default=0.0)
    realized_pnl = db.Column(db.Float, default=0.0)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    max_drawdown = db.Column(db.Float, default=0.0)
    peak_value = db.Column(db.Float, default=1000.0)


class Trade(db.Model):
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(100), unique=True, nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    trade_type = db.Column(db.String(10), nullable=False)  # LONG or SHORT
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float)
    quantity = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)
    take_profit = db.Column(db.Float, nullable=False)
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    exit_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='OPEN')  # OPEN, CLOSED, STOPPED
    pnl = db.Column(db.Float, default=0.0)
    reason = db.Column(db.Text)
    confidence = db.Column(db.String(10))
    rationale = db.Column(db.Text)


class MarketAnalysis(db.Model):
    __tablename__ = 'market_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(20), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    ema = db.Column(db.Float, nullable=False)
    macd = db.Column(db.Float, nullable=False)
    rsi = db.Column(db.Float, nullable=False)
    trend_intraday = db.Column(db.String(10))
    trend_4h = db.Column(db.String(10))
    support = db.Column(db.Float)
    resistance = db.Column(db.Float)
    trade_type = db.Column(db.String(10))
    confidence = db.Column(db.String(10))
    rationale = db.Column(db.Text)


class PortfolioHistory(db.Model):
    __tablename__ = 'portfolio_history'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_value = db.Column(db.Float, nullable=False)
    pnl = db.Column(db.Float, default=0.0)
    pnl_percentage = db.Column(db.Float, default=0.0)


# Global variables for trading system
trading_engine = None
signal_generator = None
trading_thread = None
is_trading = False


class TradingDashboardBackend:
    """Backend service for trading dashboard"""
    
    def __init__(self):
        self.paper_trader = PaperTradingEngine()
        self.signal_generator = TradeSignalGenerator(enable_paper_trading=True)
        self.db_available = True
    
    def test_database_connection(self):
        """Test if database is available"""
        try:
            with app.app_context():
                db.engine.connect()
                return True
        except Exception as e:
            print(f"Database unavailable: {e}")
            self.db_available = False
            return False
    
    def sync_database_with_paper_trader(self):
        """Sync paper trading data with database"""
        # Skip database sync if not available
        if not self.db_available and not self.test_database_connection():
            print("⚠️  Skipping database sync - database unavailable")
            return
        
        try:
            portfolio = self.paper_trader.portfolio
            
            # Update portfolio record
            portfolio_record = Portfolio(
                total_value=portfolio.total_value,
                cash_balance=portfolio.cash_balance,
                unrealized_pnl=self.calculate_unrealized_pnl(),
                realized_pnl=portfolio.total_pnl,
                total_trades=portfolio.total_trades,
                winning_trades=portfolio.winning_trades,
                losing_trades=portfolio.losing_trades,
                max_drawdown=portfolio.max_drawdown,
                peak_value=portfolio.peak_value
            )
            db.session.add(portfolio_record)
            
            # Add to portfolio history
            portfolio_history = PortfolioHistory(
                total_value=portfolio.total_value,
                pnl=portfolio.total_pnl,
                pnl_percentage=((portfolio.total_value - portfolio.initial_balance) / portfolio.initial_balance) * 100
            )
            db.session.add(portfolio_history)
            
            # Sync trades
            for trade in portfolio.open_positions + portfolio.closed_trades:
                existing_trade = Trade.query.filter_by(trade_id=trade.id).first()
                if not existing_trade:
                    try:
                        entry_time = datetime.strptime(trade.entry_time, '%Y-%m-%d %H:%M:%S') if isinstance(trade.entry_time, str) else trade.entry_time
                        exit_time = None
                        if trade.exit_time:
                            exit_time = datetime.strptime(trade.exit_time, '%Y-%m-%d %H:%M:%S') if isinstance(trade.exit_time, str) else trade.exit_time
                        
                        db_trade = Trade(
                            trade_id=trade.id,
                            symbol=trade.symbol,
                            trade_type=trade.trade_type,
                            entry_price=trade.entry_price,
                            exit_price=trade.exit_price,
                            quantity=trade.quantity,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            entry_time=entry_time,
                            exit_time=exit_time,
                            status=trade.status,
                            pnl=trade.pnl,
                            reason=getattr(trade, 'reason', ''),
                            confidence=getattr(trade, 'confidence', ''),
                            rationale=getattr(trade, 'rationale', '')
                        )
                        db.session.add(db_trade)
                    except (ValueError, AttributeError) as e:
                        print(f"Error parsing trade data for {trade.id}: {e}")
                        continue
                else:
                    # Update existing trade
                    try:
                        existing_trade.exit_price = trade.exit_price
                        if trade.exit_time:
                            existing_trade.exit_time = datetime.strptime(trade.exit_time, '%Y-%m-%d %H:%M:%S') if isinstance(trade.exit_time, str) else trade.exit_time
                        existing_trade.status = trade.status
                        existing_trade.pnl = trade.pnl
                    except (ValueError, AttributeError) as e:
                        print(f"Error updating trade {trade.id}: {e}")
                        continue
            
            db.session.commit()
            print(f"Successfully synced database at {datetime.utcnow()}")
            
        except Exception as e:
            print(f"Error syncing database: {e}")
            db.session.rollback()
    
    def calculate_unrealized_pnl(self):
        """Calculate unrealized P&L for open positions"""
        # This would require current market prices
        # For now, return 0 as placeholder
        return 0.0
    
    def save_market_analysis(self, analysis_data):
        """Save market analysis to database"""
        try:
            analysis = MarketAnalysis(
                symbol=analysis_data.get('symbol', 'ZECUSDT'),
                current_price=float(analysis_data.get('current_price', 0)),
                ema=float(analysis_data.get('ema', 0)),
                macd=float(analysis_data.get('macd', 0)),
                rsi=float(analysis_data.get('rsi', 0)),
                trend_intraday=analysis_data.get('trend_intraday', 'neutral'),
                trend_4h=analysis_data.get('trend_4h', 'neutral'),
                support=float(analysis_data.get('support', 0)),
                resistance=float(analysis_data.get('resistance', 0)),
                trade_type=analysis_data.get('trade_type', 'FLAT'),
                confidence=analysis_data.get('confidence', 'low'),
                rationale=analysis_data.get('rationale', '')[:500]  # Limit length
            )
            db.session.add(analysis)
            db.session.commit()
            print(f"Market analysis saved at {datetime.utcnow()}")
        except Exception as e:
            print(f"Error saving market analysis: {e}")
            db.session.rollback()


# Initialize backend
backend = TradingDashboardBackend()


# Routes
@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('tradedashboard.html')


@app.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio data"""
    try:
        portfolio = backend.paper_trader.portfolio
        
        return jsonify({
            'total_value': portfolio.total_value,
            'cash_balance': portfolio.cash_balance,
            'initial_balance': portfolio.initial_balance,
            'unrealized_pnl': backend.calculate_unrealized_pnl(),
            'total_pnl': portfolio.total_pnl,
            'max_drawdown': portfolio.max_drawdown,
            'open_positions': len(portfolio.open_positions),
            'total_trades': portfolio.total_trades,
            'winning_trades': portfolio.winning_trades,
            'losing_trades': portfolio.losing_trades,
            'win_rate': (portfolio.winning_trades / max(1, portfolio.total_trades)) * 100
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    try:
        positions = []
        for pos in backend.paper_trader.portfolio.open_positions:
            # Get current market price
            try:
                if hasattr(backend, 'signal_generator'):
                    current_price = backend.signal_generator.get_market_data()['current_price']
                else:
                    current_price = pos.entry_price
                    
                # Calculate unrealized P&L
                if pos.trade_type == "LONG":
                    unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
                else:  # SHORT
                    unrealized_pnl = (pos.entry_price - current_price) * pos.quantity
                    
            except Exception:
                current_price = pos.entry_price
                unrealized_pnl = 0
            
            positions.append({
                'id': pos.id,
                'symbol': pos.symbol,
                'trade_type': pos.trade_type,
                'entry_price': pos.entry_price,
                'current_price': current_price,
                'quantity': pos.quantity,
                'stop_loss': pos.stop_loss,
                'take_profit': pos.take_profit,
                'entry_time': pos.entry_time,
                'unrealized_pnl': unrealized_pnl
            })
        
        print(f"DEBUG: Returning {len(positions)} positions with IDs: {[p['id'] for p in positions]}")
        return jsonify(positions)
    except Exception as e:
        print(f"DEBUG: Error in get_positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
def get_trades():
    """Get trade history"""
    try:
        trades = []
        for trade in reversed(backend.paper_trader.portfolio.closed_trades):
            trades.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'trade_type': trade.trade_type,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'status': trade.status,
                'pnl': trade.pnl
            })
        
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analysis')
def get_analysis():
    """Get latest market analysis"""
    try:
        # Get latest analysis from database or generate new one
        latest_analysis = MarketAnalysis.query.order_by(MarketAnalysis.timestamp.desc()).first()
        
        if not latest_analysis or (datetime.utcnow() - latest_analysis.timestamp) > timedelta(minutes=5):
            # Generate new analysis
            analysis_text = backend.signal_generator.generate_analysis()
            
            # Try to get real-time data from CoinDCX if configured
            try:
                if backend.signal_generator.exchange_name == 'coindcx' and hasattr(backend.signal_generator, 'coindcx_exchange'):
                    ticker = backend.signal_generator.coindcx_exchange.get_ticker(backend.signal_generator.symbol)
                    current_price = ticker['last_price']
                    
                    # Get recent data for indicators
                    recent_data = backend.signal_generator.get_market_data('5m', 50)
                    ema_value = TechnicalAnalyzer.calculate_ema(recent_data['close'], 50)
                    rsi_value = TechnicalAnalyzer.calculate_rsi(recent_data['close'])
                    macd_data = TechnicalAnalyzer.calculate_macd(recent_data['close'])
                    
                    # Parse the analysis text for other values (simplified)
                    return jsonify({
                        'symbol': backend.signal_generator.symbol,
                        'current_price': current_price,
                        'ema': ema_value,
                        'macd': macd_data['macd'],
                        'rsi': rsi_value,
                        'trend_intraday': 'bearish' if current_price < ema_value else 'bullish',
                        'trend_4h': 'bullish',
                        'support': current_price * 0.995,
                        'resistance': current_price * 1.005,
                        'trade_type': 'SHORT' if current_price < ema_value else 'LONG',
                        'confidence': 'medium (65%)',
                        'rationale': f'Live CoinDCX data: Price {current_price:.2f} vs EMA {ema_value:.2f}, RSI {rsi_value:.1f}',
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except Exception as e:
                print(f"Error getting live CoinDCX data: {e}")
            
            # Fallback to sample data
            return jsonify({
                'symbol': backend.signal_generator.symbol,
                'current_price': 412.23,
                'ema': 417.24,
                'macd': -0.051,
                'rsi': 53.4,
                'trend_intraday': 'bearish',
                'trend_4h': 'bullish',
                'support': 412.16,
                'resistance': 412.41,
                'trade_type': 'SHORT',
                'confidence': 'high (60%)',
                'rationale': 'Short bias with price below EMA50, bearish MACD, weak RSI, 4H trend bullish',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'symbol': latest_analysis.symbol,
            'current_price': latest_analysis.current_price,
            'ema': latest_analysis.ema,
            'macd': latest_analysis.macd,
            'rsi': latest_analysis.rsi,
            'trend_intraday': latest_analysis.trend_intraday,
            'trend_4h': latest_analysis.trend_4h,
            'support': latest_analysis.support,
            'resistance': latest_analysis.resistance,
            'trade_type': latest_analysis.trade_type,
            'confidence': latest_analysis.confidence,
            'rationale': latest_analysis.rationale,
            'timestamp': latest_analysis.timestamp.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart-data')
def get_chart_data():
    """Get portfolio chart data"""
    try:
        period = request.args.get('period', '24h')
        
        # Calculate time range
        if period == '24h':
            start_time = datetime.utcnow() - timedelta(hours=24)
        elif period == '7d':
            start_time = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_time = datetime.utcnow() - timedelta(days=30)
        else:  # ALL
            start_time = datetime.utcnow() - timedelta(days=365)
        
        # Get portfolio history
        history = PortfolioHistory.query.filter(
            PortfolioHistory.timestamp >= start_time
        ).order_by(PortfolioHistory.timestamp).all()
        
        if not history:
            # Generate sample data if no history exists
            timestamps = []
            values = []
            base_time = datetime.utcnow() - timedelta(hours=24)
            
            for i in range(24):
                timestamps.append((base_time + timedelta(hours=i)).isoformat())
                values.append(1000 + (i * 2))  # Sample growth
            
            return jsonify({
                'timestamps': timestamps,
                'values': values
            })
        
        timestamps = [h.timestamp.isoformat() for h in history]
        values = [h.total_value for h in history]
        
        return jsonify({
            'timestamps': timestamps,
            'values': values
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start-trading', methods=['POST'])
def start_trading():
    """Start automated trading"""
    global is_trading, trading_thread
    
    try:
        if not is_trading:
            is_trading = True
            trading_thread = threading.Thread(target=trading_loop, daemon=True)
            trading_thread.start()
            print(f"Trading started at {datetime.utcnow()}")
            return jsonify({'status': 'started'})
        
        return jsonify({'status': 'already running'})
    except Exception as e:
        print(f"Error starting trading: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop-trading', methods=['POST'])
def stop_trading():
    """Stop automated trading"""
    global is_trading
    
    is_trading = False
    return jsonify({'status': 'stopped'})


@app.route('/api/close-position/<trade_id>', methods=['POST'])
def close_position(trade_id):
    """Close a specific position"""
    try:
        print(f"DEBUG: Attempting to close position with trade_id: {trade_id}")
        print(f"DEBUG: Available positions: {[p.id for p in backend.paper_trader.portfolio.open_positions]}")
        
        # Find the position in paper trader
        for position in backend.paper_trader.portfolio.open_positions:
            if position.id == trade_id:
                # Get current market price from exchange
                try:
                    if hasattr(backend, 'signal_generator'):
                        current_price = backend.signal_generator.get_market_data()['current_price']
                    else:
                        current_price = position.entry_price  # Fallback
                except Exception:
                    current_price = position.entry_price  # Fallback
                
                backend.paper_trader.close_position(position, current_price, "Manual Close")
                backend.sync_database_with_paper_trader()
                return jsonify({'status': 'closed', 'exit_price': current_price})
        
        return jsonify({'error': f'Position not found. Available positions: {[p.id for p in backend.paper_trader.portfolio.open_positions]}'}), 404
    except Exception as e:
        print(f"DEBUG: Error in close_position: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset-portfolio', methods=['POST'])
def reset_portfolio():
    """Reset portfolio to initial state"""
    try:
        # Clear paper trading data
        backend.paper_trader.portfolio = backend.paper_trader.load_portfolio()
        backend.paper_trader.portfolio.cash_balance = 1000.0
        backend.paper_trader.portfolio.total_value = 1000.0
        backend.paper_trader.portfolio.total_pnl = 0.0
        backend.paper_trader.portfolio.open_positions = []
        backend.paper_trader.portfolio.closed_trades = []
        backend.paper_trader.portfolio.total_trades = 0
        backend.paper_trader.portfolio.winning_trades = 0
        backend.paper_trader.portfolio.losing_trades = 0
        backend.paper_trader.portfolio.max_drawdown = 0.0
        backend.paper_trader.portfolio.peak_value = 1000.0
        
        backend.paper_trader.save_portfolio()
        
        # Clear database records
        db.session.query(Trade).delete()
        db.session.query(Portfolio).delete()
        db.session.query(PortfolioHistory).delete()
        db.session.commit()
        
        return jsonify({'status': 'reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-trades')
def export_trades():
    """Export trades to CSV"""
    try:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Symbol', 'Type', 'Entry Price', 'Exit Price', 'Quantity', 'P&L', 'Status'])
        
        # Write trades
        for trade in backend.paper_trader.portfolio.closed_trades:
            writer.writerow([
                trade.entry_time,
                trade.symbol,
                trade.trade_type,
                trade.entry_price,
                trade.exit_price,
                trade.quantity,
                trade.pnl,
                trade.status
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=trades.csv'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def trading_loop():
    """Main trading loop for automated trading"""
    global is_trading
    
    with app.app_context():
        while is_trading:
            try:
                # Run one iteration of trading analysis
                analysis = backend.signal_generator.generate_analysis()
                
                # Sync with database
                backend.sync_database_with_paper_trader()
                
                # Wait for next iteration
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in trading loop: {e}")
                time.sleep(60)


def init_db():
    """Initialize database tables"""
    with app.app_context():
        try:
            # Test database connection
            db.engine.connect()
            print("✅ Database connection successful")
            
            # Create all tables
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Create initial portfolio history entry if none exists
            if not PortfolioHistory.query.first():
                initial_history = PortfolioHistory(
                    total_value=1000.0,
                    pnl=0.0,
                    pnl_percentage=0.0
                )
                db.session.add(initial_history)
                db.session.commit()
                print("✅ Initial portfolio history created")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            print("⚠️  Dashboard will run with limited functionality")
            # Continue without database if connection fails


if __name__ == '__main__':
    print("=" * 60)
    print("TRADING DASHBOARD STARTING")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Test backend connection
    backend.test_database_connection()
    
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"🚀 Dashboard URL: http://localhost:{port}")
    print(f"📊 Database: {os.getenv('DATABASE_URL', 'sqlite:///trading.db')}")
    print(f"💱 Trading Symbol: {os.getenv('TRADING_SYMBOL', 'ZECUSDT')}")
    print(f"⏱️  Check Interval: {os.getenv('CHECK_INTERVAL_MINUTES', 1)} minute(s)")
    print(f"📈 Paper Trading: $1000 USDT initial balance")
    print("=" * 60)
    print("✨ Features: Portfolio Chart | Live Trading | P&L Tracking")
    print("🎯 Ready! Navigate to the dashboard URL above")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        print("💡 Check if PostgreSQL is running and DATABASE_URL is correct")