#!/usr/bin/env python3
"""
Trading Signal Generator
Generates structured trading analysis with entry, stop loss, and take profit levels
"""

import ccxt
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import json
from dataclasses import dataclass, asdict
from enum import Enum

# Load environment variables
load_dotenv()


class TradeStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"


@dataclass
class Trade:
    """Represents a single trade"""
    id: str
    symbol: str
    trade_type: str  # LONG or SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    entry_time: str
    exit_time: str = None
    exit_price: float = None
    status: str = TradeStatus.OPEN.value
    pnl: float = 0.0
    reason: str = ""


@dataclass
class Portfolio:
    """Represents the trading portfolio"""
    initial_balance: float = 1000.0
    cash_balance: float = 1000.0
    total_value: float = 1000.0
    open_positions: list = None
    closed_trades: list = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 1000.0
    
    def __post_init__(self):
        if self.open_positions is None:
            self.open_positions = []
        if self.closed_trades is None:
            self.closed_trades = []


class PaperTradingEngine:
    """Paper trading engine for virtual trading"""
    
    def __init__(self, portfolio_file: str = "paper_trading_portfolio.json"):
        self.portfolio_file = portfolio_file
        self.portfolio = self.load_portfolio()
        self.position_size_pct = float(os.getenv('POSITION_SIZE_PCT', '10.0'))  # 10% per trade
        self.max_positions = int(os.getenv('MAX_POSITIONS', '3'))  # Max 3 open positions
    
    def load_portfolio(self) -> Portfolio:
        """Load portfolio from file or create new one"""
        try:
            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
                portfolio = Portfolio(**data)
                # Convert lists back to Trade objects
                portfolio.open_positions = [Trade(**trade) for trade in portfolio.open_positions]
                portfolio.closed_trades = [Trade(**trade) for trade in portfolio.closed_trades]
                return portfolio
        except FileNotFoundError:
            return Portfolio()
    
    def save_portfolio(self):
        """Save portfolio to file"""
        # Convert to dict for JSON serialization
        data = asdict(self.portfolio)
        with open(self.portfolio_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management"""
        # Risk per trade (default 2% of portfolio)
        risk_per_trade = self.portfolio.total_value * 0.02
        
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        # Calculate quantity based on risk
        quantity = risk_per_trade / risk_per_unit
        
        # Limit position size to available cash and max position size
        max_quantity_by_cash = (self.portfolio.cash_balance * self.position_size_pct / 100) / entry_price
        
        return min(quantity, max_quantity_by_cash)
    
    def can_open_position(self, symbol: str, trade_type: str) -> bool:
        """Check if we can open a new position"""
        # Check max positions limit
        if len(self.portfolio.open_positions) >= self.max_positions:
            return False
        
        # Check if we already have a position in this symbol
        for pos in self.portfolio.open_positions:
            if pos.symbol == symbol:
                return False
        
        # Check if we have enough cash
        if self.portfolio.cash_balance < 50:  # Minimum $50 to trade
            return False
        
        return True
    
    def open_position(self, symbol: str, trade_type: str, entry_price: float, 
                     stop_loss: float, take_profit: float, confidence: str, rationale: str) -> bool:
        """Open a new trading position"""
        
        if not self.can_open_position(symbol, trade_type):
            return False
        
        quantity = self.calculate_position_size(entry_price, stop_loss)
        
        if quantity <= 0:
            return False
        
        # Create new trade
        trade_id = f"{symbol}_{len(self.portfolio.closed_trades) + len(self.portfolio.open_positions) + 1}"
        trade = Trade(
            id=trade_id,
            symbol=symbol,
            trade_type=trade_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            entry_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            reason=f"Confidence: {confidence} | {rationale}"
        )
        
        # Update portfolio
        position_value = quantity * entry_price
        self.portfolio.cash_balance -= position_value
        self.portfolio.open_positions.append(trade)
        
        self.save_portfolio()
        return True
    
    def update_positions(self, current_price: float, symbol: str):
        """Update open positions with current market price"""
        positions_to_close = []
        
        for position in self.portfolio.open_positions:
            if position.symbol != symbol:
                continue
            
            # Calculate unrealized P&L
            if position.trade_type == "LONG":
                unrealized_pnl = (current_price - position.entry_price) * position.quantity
                
                # Check stop loss or take profit
                if current_price <= position.stop_loss:
                    positions_to_close.append((position, current_price, "Stop Loss Hit"))
                elif current_price >= position.take_profit:
                    positions_to_close.append((position, current_price, "Take Profit Hit"))
                    
            else:  # SHORT
                unrealized_pnl = (position.entry_price - current_price) * position.quantity
                
                # Check stop loss or take profit
                if current_price >= position.stop_loss:
                    positions_to_close.append((position, current_price, "Stop Loss Hit"))
                elif current_price <= position.take_profit:
                    positions_to_close.append((position, current_price, "Take Profit Hit"))
        
        # Close positions that hit SL or TP
        for position, exit_price, reason in positions_to_close:
            self.close_position(position, exit_price, reason)
    
    def close_position(self, position: Trade, exit_price: float, reason: str = "Manual Close"):
        """Close an open position"""
        
        # Calculate P&L
        if position.trade_type == "LONG":
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Update trade
        position.exit_price = exit_price
        position.exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        position.pnl = pnl
        position.status = TradeStatus.CLOSED.value
        
        # Update portfolio
        position_value = position.quantity * exit_price
        self.portfolio.cash_balance += position_value
        self.portfolio.total_pnl += pnl
        
        if pnl > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
        
        self.portfolio.total_trades += 1
        
        # Move to closed trades
        self.portfolio.closed_trades.append(position)
        self.portfolio.open_positions.remove(position)
        
        # Update portfolio value and drawdown
        self.update_portfolio_metrics()
        
        self.save_portfolio()
        
        return pnl
    
    def update_portfolio_metrics(self):
        """Update portfolio metrics like total value and drawdown"""
        # Calculate total portfolio value
        unrealized_pnl = 0
        for position in self.portfolio.open_positions:
            # This would need current price, simplified for now
            pass
        
        self.portfolio.total_value = self.portfolio.cash_balance + unrealized_pnl
        
        # Update peak value and drawdown
        if self.portfolio.total_value > self.portfolio.peak_value:
            self.portfolio.peak_value = self.portfolio.total_value
        
        current_drawdown = (self.portfolio.peak_value - self.portfolio.total_value) / self.portfolio.peak_value * 100
        if current_drawdown > self.portfolio.max_drawdown:
            self.portfolio.max_drawdown = current_drawdown
    
    def get_portfolio_summary(self) -> str:
        """Get portfolio performance summary"""
        win_rate = (self.portfolio.winning_trades / max(1, self.portfolio.total_trades)) * 100
        
        return f"""
📊 PAPER TRADING PORTFOLIO
Initial Balance: ${self.portfolio.initial_balance:,.2f}
Cash Balance: ${self.portfolio.cash_balance:,.2f}
Total Value: ${self.portfolio.total_value:,.2f}
Total P&L: ${self.portfolio.total_pnl:,.2f} ({(self.portfolio.total_pnl/self.portfolio.initial_balance)*100:+.1f}%)
Open Positions: {len(self.portfolio.open_positions)}
Total Trades: {self.portfolio.total_trades}
Win Rate: {win_rate:.1f}% ({self.portfolio.winning_trades}W/{self.portfolio.losing_trades}L)
Max Drawdown: {self.portfolio.max_drawdown:.1f}%
"""
    
    def get_open_positions_summary(self) -> str:
        """Get summary of open positions"""
        if not self.portfolio.open_positions:
            return "No open positions"
        
        summary = "\n🔄 OPEN POSITIONS:\n"
        for pos in self.portfolio.open_positions:
            entry_time = pos.entry_time.split()[1][:5]  # Get HH:MM
            summary += f"  {pos.trade_type} {pos.symbol} | Entry: ${pos.entry_price:.3f} | Qty: {pos.quantity:.3f} | SL: ${pos.stop_loss:.3f} | TP: ${pos.take_profit:.3f} | Time: {entry_time}\n"
        
        return summary


class TechnicalAnalyzer:
    """Technical analysis calculations for trading signals"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])  # Start with SMA
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
        """Calculate MACD indicator"""
        if len(prices) < slow_period:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        fast_ema = TechnicalAnalyzer.calculate_ema(prices, fast_period)
        slow_ema = TechnicalAnalyzer.calculate_ema(prices, slow_period)
        macd_line = fast_ema - slow_ema
        
        # For signal line, we'd need historical MACD values
        # Simplified: use MACD line as approximation
        signal_line = macd_line * 0.8  # Approximation
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_atr(high_prices: List[float], low_prices: List[float], close_prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(close_prices) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(close_prices)):
            high_low = high_prices[i] - low_prices[i]
            high_close = abs(high_prices[i] - close_prices[i-1])
            low_close = abs(low_prices[i] - close_prices[i-1])
            
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        return np.mean(true_ranges[-period:]) if true_ranges else 0.0


class SupportResistanceAnalyzer:
    """Identify key support and resistance levels"""
    
    @staticmethod
    def find_support_resistance(high_prices: List[float], low_prices: List[float], close_prices: List[float]) -> Dict:
        """Find key support and resistance levels"""
        current_price = close_prices[-1]
        
        # Recent highs and lows for S/R levels
        recent_highs = high_prices[-20:]
        recent_lows = low_prices[-20:]
        
        # Find resistance (recent high above current price)
        resistance_candidates = [h for h in recent_highs if h > current_price]
        resistance = min(resistance_candidates) if resistance_candidates else current_price * 1.02
        
        # Find support (recent low below current price)  
        support_candidates = [l for l in recent_lows if l < current_price]
        support = max(support_candidates) if support_candidates else current_price * 0.98
        
        return {
            'support': support,
            'resistance': resistance
        }


class TrendAnalyzer:
    """Analyze market trends for different timeframes"""
    
    @staticmethod
    def analyze_intraday_trend(current_price: float, ema20: float, macd: Dict, rsi: float) -> str:
        """Determine intraday trend based on technical indicators"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Price vs EMA
        if current_price > ema20:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # MACD
        if macd['macd'] > macd['signal']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # RSI
        if rsi > 50:
            bullish_signals += 1
        elif rsi < 50:
            bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return "bullish"
        elif bearish_signals > bullish_signals:
            return "bearish"
        else:
            return "neutral"
    
    @staticmethod
    def analyze_4h_trend(prices_4h: List[float], ema20_4h: float, ema50_4h: float) -> str:
        """Determine 4H trend based on longer timeframe indicators"""
        current_price = prices_4h[-1]
        
        # EMA alignment
        if current_price > ema20_4h > ema50_4h:
            return "bullish"
        elif current_price < ema20_4h < ema50_4h:
            return "bearish"
        else:
            return "neutral"


class TradeSignalGenerator:
    """Generate complete trading signals with entry, SL, and TP levels"""
    
    def __init__(self, symbol: str = None, enable_paper_trading: bool = False):
        # Load configuration from environment
        self.symbol = symbol or os.getenv('TRADING_SYMBOL', 'SOL/USDT')
        self.exchange_name = os.getenv('EXCHANGE', 'binance').lower()
        self.timeframe = os.getenv('TIMEFRAME', '15m')
        self.ema_period = int(os.getenv('EMA_PERIOD', '20'))
        self.rsi_period = int(os.getenv('RSI_PERIOD', '14'))
        
        # Store previous analysis for comparison
        self.previous_analysis = None
        
        # Paper trading engine
        self.enable_paper_trading = enable_paper_trading
        if self.enable_paper_trading:
            self.paper_trader = PaperTradingEngine()
        else:
            self.paper_trader = None
        
        # Initialize exchange based on configuration
        if self.exchange_name == 'binance':
            self.exchange = ccxt.binance({
                'apiKey': os.getenv('BINANCE_API_KEY', ''),
                'secret': os.getenv('BINANCE_SECRET_KEY', ''),
                'sandbox': os.getenv('BINANCE_SANDBOX', 'false').lower() == 'true',
                'enableRateLimit': True,
            })
        elif self.exchange_name == 'coindcx':
            # Use custom CoinDCX exchange implementation
            from exchanges.coindcx_exchange import CoinDCXExchange
            self.coindcx_exchange = CoinDCXExchange(
                api_key=os.getenv('COINDCX_API_KEY', ''),
                api_secret=os.getenv('COINDCX_SECRET_KEY', '')
            )
            self.exchange = None  # We'll use coindcx_exchange directly
            print(f"Using CoinDCX exchange with custom implementation")
        else:
            # Default to Binance
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
            })
    
    def get_market_data(self, timeframe: str = None, limit: int = 100) -> Dict:
        """Fetch market data from exchange"""
        if timeframe is None:
            timeframe = self.timeframe
        
        try:
            if self.exchange_name == 'coindcx' and hasattr(self, 'coindcx_exchange'):
                # Use CoinDCX custom implementation
                ohlcv_data = self.coindcx_exchange.get_historical_data(self.symbol, timeframe, limit)
                
                # Convert to DataFrame format
                df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                return {
                    'open': df['open'].tolist(),
                    'high': df['high'].tolist(), 
                    'low': df['low'].tolist(),
                    'close': df['close'].tolist(),
                    'volume': df['volume'].tolist(),
                    'current_price': df['close'].iloc[-1]
                }
            else:
                # Use ccxt for other exchanges (Binance)
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                return {
                    'open': df['open'].tolist(),
                    'high': df['high'].tolist(), 
                    'low': df['low'].tolist(),
                    'close': df['close'].tolist(),
                    'volume': df['volume'].tolist(),
                    'current_price': df['close'].iloc[-1]
                }
        except Exception as e:
            print(f"Error fetching data from {self.exchange_name}: {e}")
            # Fallback mock data for testing
            return self.get_mock_data()
    
    def get_mock_data(self) -> Dict:
        """Generate mock data for testing"""
        base_price = 180.0
        prices = []
        
        for i in range(100):
            price = base_price + np.random.normal(0, 2) + np.sin(i/10) * 5
            prices.append(max(price, 170))  # Keep above 170
        
        return {
            'open': prices,
            'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
            'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
            'close': prices,
            'volume': [np.random.uniform(1000, 5000) for _ in prices],
            'current_price': prices[-1]
        }
    
    def calculate_trade_levels(self, current_price: float, trend: str, atr: float, support: float, resistance: float) -> Dict:
        """Calculate entry, stop loss, and take profit levels"""
        
        if trend == "bullish":
            trade_type = "LONG"
            entry = current_price
            stop_loss = max(support, current_price - (2 * atr))
            take_profit = min(resistance, current_price + (3 * atr))
            
        elif trend == "bearish":
            trade_type = "SHORT"
            entry = current_price
            stop_loss = min(resistance, current_price + (2 * atr))
            take_profit = max(support, current_price - (3 * atr))
            
        else:  # neutral
            trade_type = "FLAT"
            entry = current_price
            stop_loss = current_price
            take_profit = current_price
        
        return {
            'trade_type': trade_type,
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
    
    def calculate_confidence(self, trend_intraday: str, trend_4h: str, rsi: float, macd: Dict) -> Tuple[str, int]:
        """Calculate trade confidence level"""
        confidence_score = 0
        
        # Trend alignment
        if trend_intraday == trend_4h and trend_intraday != "neutral":
            confidence_score += 30
        elif trend_intraday != "neutral":
            confidence_score += 15
        
        # RSI conditions
        if (trend_intraday == "bullish" and 30 < rsi < 70) or (trend_intraday == "bearish" and 30 < rsi < 70):
            confidence_score += 20
        elif (trend_intraday == "bullish" and rsi > 70) or (trend_intraday == "bearish" and rsi < 30):
            confidence_score -= 10  # Overbought/oversold
        
        # MACD momentum
        if abs(macd['histogram']) > abs(macd['macd']) * 0.1:
            confidence_score += 15
        
        # Volume confirmation (simplified)
        confidence_score += 10  # Assume average volume
        
        if confidence_score >= 60:
            return "high", min(confidence_score, 85)
        elif confidence_score >= 35:
            return "medium", confidence_score
        else:
            return "low", max(confidence_score, 15)
    
    def generate_rationale(self, trend_intraday: str, trend_4h: str, current_price: float, ema20: float, 
                          rsi: float, macd: Dict, confidence_level: str) -> str:
        """Generate brief rationale for the trade decision"""
        
        if trend_intraday == "bullish":
            price_position = "above EMA20" if current_price > ema20 else "below EMA20"
            macd_status = "bullish MACD" if macd['macd'] > macd['signal'] else "bearish MACD"
            rsi_status = "strong RSI" if 40 < rsi < 70 else "extreme RSI"
            
            rationale = f"Long bias with price {price_position}, {macd_status}, {rsi_status}"
            
        elif trend_intraday == "bearish":
            price_position = "below EMA20" if current_price < ema20 else "above EMA20"  
            macd_status = "bearish MACD" if macd['macd'] < macd['signal'] else "bullish MACD"
            rsi_status = "weak RSI" if 30 < rsi < 60 else "extreme RSI"
            
            rationale = f"Short bias with price {price_position}, {macd_status}, {rsi_status}"
            
        else:
            rationale = "Sideways market, mixed signals, waiting for clearer direction"
        
        if trend_4h != trend_intraday and trend_4h != "neutral":
            rationale += f", 4H trend {trend_4h}"
        
        return rationale
    
    def generate_analysis(self) -> str:
        """Generate complete trading analysis in the specified format"""
        
        # Get market data
        data_15m = self.get_market_data('15m', 100)
        data_4h = self.get_market_data('4h', 50)
        
        current_price = data_15m['current_price']
        
        # Calculate technical indicators
        ema20 = TechnicalAnalyzer.calculate_ema(data_15m['close'], self.ema_period)
        macd = TechnicalAnalyzer.calculate_macd(data_15m['close'])
        rsi = TechnicalAnalyzer.calculate_rsi(data_15m['close'], self.rsi_period)
        atr = TechnicalAnalyzer.calculate_atr(data_15m['high'], data_15m['low'], data_15m['close'])
        
        # 4H indicators
        ema20_4h = TechnicalAnalyzer.calculate_ema(data_4h['close'], 20)
        ema50_4h = TechnicalAnalyzer.calculate_ema(data_4h['close'], 50)
        
        # Analyze trends
        trend_intraday = TrendAnalyzer.analyze_intraday_trend(current_price, ema20, macd, rsi)
        trend_4h = TrendAnalyzer.analyze_4h_trend(data_4h['close'], ema20_4h, ema50_4h)
        
        # Find support/resistance
        sr_levels = SupportResistanceAnalyzer.find_support_resistance(
            data_15m['high'], data_15m['low'], data_15m['close']
        )
        
        # Calculate trade levels
        trade_levels = self.calculate_trade_levels(
            current_price, trend_intraday, atr, sr_levels['support'], sr_levels['resistance']
        )
        
        # Calculate confidence
        confidence_level, confidence_score = self.calculate_confidence(
            trend_intraday, trend_4h, rsi, macd
        )
        
        # Generate rationale
        rationale = self.generate_rationale(
            trend_intraday, trend_4h, current_price, ema20, rsi, macd, confidence_level
        )
        
        # Format output
        analysis = f"""Analyze {self.symbol}: current_price = {current_price:.3f}, EMA{self.ema_period} = {ema20:.3f}, MACD = {macd['macd']:.3f}, RSI = {rsi:.1f}
Intraday trend: {trend_intraday}
4H context: {trend_4h}
Key levels: Support {sr_levels['support']:.3f}, Resistance {sr_levels['resistance']:.3f}
Trade: {trade_levels['trade_type']}
Entry: {trade_levels['entry']:.3f}
SL: {trade_levels['stop_loss']:.3f}
TP: {trade_levels['take_profit']:.3f}
Confidence: {confidence_level} ({confidence_score}%)
Rationale: {rationale}"""

        # Store current analysis for next comparison
        current_analysis_data = {
            'trade_type': trade_levels['trade_type'],
            'trend_intraday': trend_intraday,
            'trend_4h': trend_4h,
            'confidence_level': confidence_level,
            'current_price': current_price,
            'rsi': rsi
        }
        
        # Paper trading logic
        paper_trading_info = ""
        if self.paper_trader:
            # Update existing positions
            self.paper_trader.update_positions(current_price, self.symbol)
            
            # Check for new trade opportunities
            trade_decision = self.evaluate_trade_decision(
                trade_levels, confidence_level, current_analysis_data
            )
            
            if trade_decision:
                opened = self.paper_trader.open_position(
                    self.symbol,
                    trade_levels['trade_type'],
                    trade_levels['entry'],
                    trade_levels['stop_loss'],
                    trade_levels['take_profit'],
                    confidence_level,
                    rationale
                )
                if opened:
                    paper_trading_info += f"\n✅ NEW POSITION OPENED: {trade_levels['trade_type']} {self.symbol}"
                else:
                    paper_trading_info += f"\n❌ Position not opened (risk management/limits)"
            
            # Add portfolio summary
            paper_trading_info += self.paper_trader.get_portfolio_summary()
            paper_trading_info += self.paper_trader.get_open_positions_summary()
        
        # Check for significant changes
        alert_message = self.check_for_alerts(current_analysis_data)
        if alert_message:
            analysis += f"\n🚨 ALERT: {alert_message}"
        
        if paper_trading_info:
            analysis += paper_trading_info
        
        self.previous_analysis = current_analysis_data
        return analysis
    
    def evaluate_trade_decision(self, trade_levels: Dict, confidence_level: str, analysis_data: Dict) -> bool:
        """Evaluate whether to execute a trade based on conditions"""
        # Don't trade if signal is FLAT
        if trade_levels['trade_type'] == 'FLAT':
            return False
        
        # Only trade on high or medium confidence
        if confidence_level == 'low':
            return False
        
        # Don't trade in extreme RSI conditions
        rsi = analysis_data['rsi']
        if rsi > 80 or rsi < 20:
            return False
        
        # Require trend alignment for high confidence trades
        if confidence_level == 'high':
            intraday = analysis_data['trend_intraday']
            trend_4h = analysis_data['trend_4h']
            
            # For LONG: both trends should be bullish or at least intraday bullish
            if trade_levels['trade_type'] == 'LONG':
                if intraday != 'bullish':
                    return False
            
            # For SHORT: both trends should be bearish or at least intraday bearish  
            if trade_levels['trade_type'] == 'SHORT':
                if intraday != 'bearish':
                    return False
        
        return True
    
    def check_for_alerts(self, current_data: Dict) -> str:
        """Check for significant changes and generate alerts"""
        if not self.previous_analysis:
            return ""
        
        alerts = []
        prev = self.previous_analysis
        curr = current_data
        
        # Trade direction change
        if prev['trade_type'] != curr['trade_type']:
            alerts.append(f"Trade signal changed from {prev['trade_type']} to {curr['trade_type']}")
        
        # Trend reversal
        if prev['trend_intraday'] != curr['trend_intraday'] and curr['trend_intraday'] != 'neutral':
            alerts.append(f"Intraday trend reversed to {curr['trend_intraday']}")
        
        # 4H trend change
        if prev['trend_4h'] != curr['trend_4h'] and curr['trend_4h'] != 'neutral':
            alerts.append(f"4H trend changed to {curr['trend_4h']}")
        
        # Confidence level change
        if prev['confidence_level'] != curr['confidence_level']:
            if curr['confidence_level'] == 'high':
                alerts.append(f"Confidence increased to HIGH")
            elif prev['confidence_level'] == 'high' and curr['confidence_level'] != 'high':
                alerts.append(f"Confidence decreased from HIGH to {curr['confidence_level']}")
        
        # RSI extreme levels
        if curr['rsi'] > 80 and prev['rsi'] <= 80:
            alerts.append(f"RSI entered overbought zone ({curr['rsi']:.1f})")
        elif curr['rsi'] < 20 and prev['rsi'] >= 20:
            alerts.append(f"RSI entered oversold zone ({curr['rsi']:.1f})")
        
        # Price movement alerts (>2% change)
        price_change = ((curr['current_price'] - prev['current_price']) / prev['current_price']) * 100
        if abs(price_change) > 2:
            direction = "📈 UP" if price_change > 0 else "📉 DOWN"
            alerts.append(f"Price moved {direction} {abs(price_change):.1f}%")
        
        return " | ".join(alerts) if alerts else ""


def continuous_monitor(enable_paper_trading: bool = False):
    """Continuously monitor and generate trading signals"""
    signal_generator = TradeSignalGenerator(enable_paper_trading=enable_paper_trading)
    check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '1')) * 60  # Convert to seconds
    verbose_logging = os.getenv('VERBOSE_LOGGING', 'true').lower() == 'true'
    
    print("=" * 70)
    print("CONTINUOUS TRADING SIGNAL MONITOR")
    if enable_paper_trading:
        print("📈 PAPER TRADING ENABLED - Starting with $1000 USDT")
    print(f"Symbol: {signal_generator.symbol} | Exchange: {signal_generator.exchange_name.upper()}")
    print(f"Timeframe: {signal_generator.timeframe} | EMA Period: {signal_generator.ema_period}")
    print(f"Check Interval: {check_interval//60} minute(s)")
    print("=" * 70)
    print("Press Ctrl+C to stop monitoring...")
    print()
    
    try:
        while True:
            try:
                if verbose_logging:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {signal_generator.symbol}...")
                
                analysis = signal_generator.generate_analysis()
                
                # Always show the full analysis
                print("\n" + "=" * 70)
                print(analysis)
                print("=" * 70)
                
                if verbose_logging:
                    print(f"Next check in {check_interval//60} minute(s)...")
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"Error during analysis: {e}")
                if verbose_logging:
                    print(f"Retrying in {check_interval//60} minute(s)...")
                time.sleep(check_interval)
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")


def single_analysis():
    """Generate a single trading analysis"""
    signal_generator = TradeSignalGenerator()
    
    print("=" * 60)
    print("TRADING SIGNAL ANALYSIS")
    print(f"Symbol: {signal_generator.symbol} | Exchange: {signal_generator.exchange_name.upper()}")
    print(f"Timeframe: {signal_generator.timeframe} | EMA Period: {signal_generator.ema_period}")
    print("=" * 60)
    
    analysis = signal_generator.generate_analysis()
    
    print(analysis)
    print("\n" + "=" * 60)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def portfolio_status():
    """Show current paper trading portfolio status"""
    paper_trader = PaperTradingEngine()
    print("=" * 60)
    print(paper_trader.get_portfolio_summary())
    print(paper_trader.get_open_positions_summary())
    
    if paper_trader.portfolio.closed_trades:
        print("\n📈 RECENT CLOSED TRADES:")
        for trade in paper_trader.portfolio.closed_trades[-5:]:  # Last 5 trades
            pnl_color = "📗" if trade.pnl > 0 else "📕"
            print(f"  {pnl_color} {trade.trade_type} {trade.symbol} | Entry: ${trade.entry_price:.3f} | Exit: ${trade.exit_price:.3f} | P&L: ${trade.pnl:+.2f}")
    print("=" * 60)


def main():
    """Main execution function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        continuous_monitor()
    elif len(sys.argv) > 1 and sys.argv[1] == '--monitor':
        continuous_monitor()
    elif len(sys.argv) > 1 and sys.argv[1] == '--paper-trade':
        continuous_monitor(enable_paper_trading=True)
    elif len(sys.argv) > 1 and sys.argv[1] == '--portfolio':
        portfolio_status()
    elif len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Trading Signal Generator")
        print("Usage:")
        print("  python trade.py                - Single analysis")
        print("  python trade.py --continuous   - Continuous monitoring")
        print("  python trade.py --monitor      - Continuous monitoring")
        print("  python trade.py --paper-trade  - Paper trading with $1000 USDT")
        print("  python trade.py --portfolio    - Show paper trading portfolio")
        print("  python trade.py --help         - Show this help")
        print("\nConfiguration is read from .env file:")
        print("  TRADING_SYMBOL - Trading pair (e.g., BTC/USDT)")
        print("  CHECK_INTERVAL_MINUTES - Check interval in minutes")
        print("  TIMEFRAME - Candle timeframe (5m, 15m, 1h, etc.)")
        print("  EMA_PERIOD - EMA period for analysis")
        print("  POSITION_SIZE_PCT - Position size as % of portfolio (default: 10)")
        print("  MAX_POSITIONS - Maximum open positions (default: 3)")
    else:
        single_analysis()


if __name__ == "__main__":
    main()
