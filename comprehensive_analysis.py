#!/usr/bin/env python3
"""
Complete Trading Analysis with Automated Signals
Provides comprehensive technical analysis data and automated trading signals with TP/SL
"""

from ema9_api import EMA9API
import json
from datetime import datetime


class ComprehensiveTradingAnalyzer:
    """Complete trading analysis with signals and TP/SL levels"""
    
    def __init__(self):
        self.api = EMA9API()
    
    def get_complete_analysis(self) -> dict:
        """Get complete analysis with formatted output and trading signal"""
        
        # Get comprehensive data
        data = self.api.get_ema9_data()
        if 'error' in data:
            return {'error': data['error']}
        
        # Get trading signal
        signal = self.api.get_trading_signal()
        
        # Format the output
        formatted_data = self.api.get_formatted_output()
        formatted_signal = self.api.get_formatted_trading_signal()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': data['symbol'],
            'formatted_analysis': formatted_data,
            'trading_signal': signal,
            'formatted_signal': formatted_signal,
            'raw_data': data
        }
    
    def analyze_and_trade(self) -> str:
        """Get complete analysis with trading recommendation"""
        
        print("🔍 COMPREHENSIVE TRADING ANALYSIS")
        print("=" * 70)
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            # Test connection
            test = self.api.test_connection()
            if test['status'] != 'SUCCESS':
                return f"❌ Connection Error: {test.get('error', 'Unknown')}"
            
            print(f"✅ Connected to {test['exchange_name']}")
            print()
            
            # Get formatted technical analysis
            print("📊 TECHNICAL ANALYSIS DATA")
            print("=" * 50)
            formatted_data = self.api.get_formatted_output()
            print(formatted_data)
            
            print("\n" + "=" * 70)
            print("🎯 AUTOMATED TRADING SIGNAL")
            print("=" * 70)
            
            # Get trading signal
            signal_data = self.api.get_trading_signal()
            
            if 'error' in signal_data:
                return f"❌ Signal Error: {signal_data['error']}"
            
            # Generate trading recommendation
            trade_recommendation = self._generate_trade_recommendation(signal_data)
            print(trade_recommendation)
            
            # Add risk management notes
            print("\n" + "=" * 70)
            print("⚠️  RISK MANAGEMENT NOTES")
            print("=" * 70)
            risk_notes = self._generate_risk_notes(signal_data)
            print(risk_notes)
            
            return "Analysis completed successfully"
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _generate_trade_recommendation(self, signal_data: dict) -> str:
        """Generate detailed trading recommendation"""
        
        direction = signal_data['signal_direction']
        price = signal_data['current_price']
        confidence = signal_data['confidence']
        
        if direction == "HOLD":
            return f"""
🔄 RECOMMENDATION: HOLD/WAIT
Current Price: ${price}
Confidence: {confidence}%

⏳ No clear trading opportunity detected. 
Wait for better technical setup or market conditions.

Current Market State:
• RSI(7): {signal_data['current_rsi7']:.1f} | RSI(14): {signal_data['current_rsi14']:.1f}
• MACD: {signal_data['current_macd']:.3f}
• Price vs EMA20: {signal_data['price_vs_ema20_pct']:+.2f}%
• Volatility (ATR): {signal_data['volatility_factor']:.3f}
"""
        
        emoji = "📈" if direction == "LONG" else "📉"
        color = "GREEN" if direction == "LONG" else "RED"
        
        # Calculate percentages
        sl_pct = abs((signal_data['stop_loss'] - price) / price * 100)
        tp1_pct = abs((signal_data['take_profit_1'] - price) / price * 100)
        tp2_pct = abs((signal_data['take_profit_2'] - price) / price * 100)
        tp3_pct = abs((signal_data['take_profit_3'] - price) / price * 100)
        
        return f"""
{emoji} TRADE SIGNAL: {direction} POSITION ({color})
═══════════════════════════════════════════════════════════════

💰 TRADE SETUP:
├─ Entry Price:     ${signal_data['entry_price']}
├─ Stop Loss:       ${signal_data['stop_loss']} (-{sl_pct:.2f}%)
├─ Take Profit 1:   ${signal_data['take_profit_1']} (+{tp1_pct:.2f}%) [R/R: 1:{signal_data['risk_reward_1']}]
├─ Take Profit 2:   ${signal_data['take_profit_2']} (+{tp2_pct:.2f}%) [R/R: 1:{signal_data['risk_reward_2']}]
└─ Take Profit 3:   ${signal_data['take_profit_3']} (+{tp3_pct:.2f}%) [R/R: 1:{signal_data['risk_reward_3']}]

📊 POSITION MANAGEMENT:
├─ Position Size:   {signal_data['position_size_pct']}% of total capital
├─ Risk Amount:     ${signal_data['risk_amount']}
├─ Confidence:      {confidence}% | Strength: {signal_data['signal_strength']}/100
├─ Time Validity:   {signal_data['validity_hours']} hours
└─ Volatility:      {signal_data['volatility_factor']:.4f} (ATR-based)

📈 TECHNICAL ANALYSIS:
├─ Current Price:   ${signal_data['current_price']}
├─ EMA20 (1m):      ${signal_data['current_ema20']} ({signal_data['price_vs_ema20_pct']:+.2f}%)
├─ MACD:            {signal_data['current_macd']:.3f}
├─ RSI(7):          {signal_data['current_rsi7']:.1f}
├─ RSI(14):         {signal_data['current_rsi14']:.1f}
├─ 4H EMA20:        ${signal_data['ema20_4h']:.3f}
├─ 4H EMA50:        ${signal_data['ema50_4h']:.3f}
├─ ATR(3):          {signal_data['atr_3']:.4f}
└─ ATR(14):         {signal_data['atr_14']:.4f}

🎯 SIGNAL FACTORS:"""
        
        recommendation = f"\n"
        for i, factor in enumerate(signal_data['signal_factors'], 1):
            recommendation += f"├─ {i}. {factor}\n"
        
        return recommendation
    
    def _generate_risk_notes(self, signal_data: dict) -> str:
        """Generate risk management notes"""
        
        direction = signal_data['signal_direction']
        confidence = signal_data['confidence']
        
        if direction == "HOLD":
            return """
• Monitor for clearer technical signals
• Wait for RSI to reach extreme levels (>70 or <30)
• Watch for MACD crossover or divergence
• Consider market volatility and news events
"""
        
        notes = f"""
🚨 RISK MANAGEMENT CHECKLIST:

✅ Position Sizing:
├─ Use only {signal_data['position_size_pct']}% of capital (based on {confidence}% confidence)
├─ Never risk more than 2% of total capital on single trade
└─ Scale position size based on market conditions

✅ Stop Loss Management:
├─ Place stop loss at ${signal_data['stop_loss']} immediately after entry
├─ Do NOT move stop loss against your position
├─ Consider trailing stop after reaching TP1
└─ Exit immediately if stop loss is hit

✅ Take Profit Strategy:
├─ Take 30% profit at TP1 (${signal_data['take_profit_1']})
├─ Take 40% profit at TP2 (${signal_data['take_profit_2']})  
├─ Let 30% run to TP3 or trail stop (${signal_data['take_profit_3']})
└─ Move stop to breakeven after TP1 is hit

✅ Time Management:
├─ Signal valid for {signal_data['validity_hours']} hours maximum
├─ Re-evaluate if no movement within 2 hours
├─ Exit if market conditions change significantly
└─ Avoid holding overnight unless confident

✅ Market Conditions:
├─ Current volatility: {signal_data['volatility_factor']:.4f} (ATR-based)
├─ {"Higher than average volatility - reduce position size" if signal_data['volatility_factor'] > 0.1 else "Normal volatility conditions"}
├─ Monitor major support/resistance levels
└─ Watch for news events that could affect price

⚠️  IMPORTANT DISCLAIMERS:
• This is an automated signal based on technical analysis only
• Past performance does not guarantee future results  
• Always do your own research and risk assessment
• Never invest more than you can afford to lose
• Consider market sentiment and fundamental factors
"""
        
        return notes


def main():
    """Main execution function"""
    analyzer = ComprehensiveTradingAnalyzer()
    result = analyzer.analyze_and_trade()
    
    if "Error" in result:
        print(result)
    else:
        print(f"\n✅ {result}")
        print("\n" + "=" * 70)
        print("📱 QUICK ACCESS COMMANDS")
        print("=" * 70)
        print("""
# Get just the formatted data:
python ema9_api.py formatted

# Get just the trading signal:  
python ema9_api.py trade-formatted

# Get JSON data for algorithms:
python ema9_api.py trade

# Run this complete analysis:
python comprehensive_analysis.py
""")


if __name__ == "__main__":
    main()