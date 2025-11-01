#!/usr/bin/env python3
"""
Example Usage of EMA9 Backend for CoinDCX
Demonstrates how to use the backend.py to get EMA9 data
"""

import json
import time
from datetime import datetime
from ema9_api import EMA9API, get_ema9_data, get_current_signal, is_bullish, is_bearish


def example_basic_usage():
    """Example: Basic usage of EMA9 API"""
    print("=" * 60)
    print("Example 1: Basic EMA9 Data Retrieval")
    print("=" * 60)
    
    # Method 1: Using convenience functions
    print("Method 1: Using convenience functions")
    print("-" * 40)
    
    # Get complete EMA9 data
    data = get_ema9_data()
    if 'error' not in data:
        print(f"Symbol: {data['symbol']}")
        print(f"Current Price: ${data['current_price']:.6f}")
        print(f"EMA9: ${data['ema9']:.6f}")
        print(f"Gap: {data['price_to_ema_percentage']:+.3f}%")
        print(f"Position: {data['position']} EMA9")
        print(f"Signal: {data['signal']['type']} (Strength: {data['signal']['strength']}%)")
    else:
        print(f"Error: {data['error']}")
    
    print("\nMethod 2: Using quick checks")
    print("-" * 40)
    
    # Quick boolean checks
    print(f"Is Bullish: {is_bullish()}")
    print(f"Is Bearish: {is_bearish()}")
    
    # Get current signal
    signal = get_current_signal()
    if 'error' not in signal:
        print(f"Signal Type: {signal['signal_type']}")
        print(f"Confidence: {signal['confidence']:.1%}")
        print(f"Recommendation: {signal['recommendation']}")


def example_api_class():
    """Example: Using EMA9API class for advanced features"""
    print("\n" + "=" * 60)
    print("Example 2: Advanced Usage with EMA9API Class")
    print("=" * 60)
    
    # Initialize API
    api = EMA9API()
    
    # Test connection first
    print("Testing connection...")
    test_result = api.test_connection()
    if test_result['status'] != 'SUCCESS':
        print(f"Connection failed: {test_result.get('error', 'Unknown error')}")
        return
    
    print(f"✅ Connected to {test_result['exchange_name']}")
    
    # Get price vs EMA9 data
    print("\nPrice vs EMA9 Analysis:")
    print("-" * 40)
    price_data = api.get_price_vs_ema9()
    if 'error' not in price_data:
        print(f"Current Price: ${price_data['current_price']:.6f}")
        print(f"EMA9: ${price_data['ema9']:.6f}")
        print(f"Gap Amount: ${price_data['gap_amount']:.6f}")
        print(f"Gap Percentage: {price_data['gap_percentage']:+.3f}%")
        print(f"Position: Price is {price_data['position']} EMA9")
        print(f"EMA9 Trend: {price_data['ema_trend']}")
    
    # Get historical data
    print("\nHistorical EMA9 Data (Last 5 periods):")
    print("-" * 40)
    history = api.get_history(periods=5)
    if history:
        print("Period | Price      | EMA9       | Gap%    | Position")
        print("-" * 55)
        for point in history:
            print(f"{point['period']:6d} | ${point['price']:9.4f} | ${point['ema9']:9.4f} | {point['gap_percent']:+6.2f}% | {point['position']:>8s}")
    else:
        print("No historical data available")


def example_monitoring_loop():
    """Example: Continuous monitoring with EMA9 backend"""
    print("\n" + "=" * 60)
    print("Example 3: Continuous Monitoring (5 iterations)")
    print("=" * 60)
    
    api = EMA9API()
    
    for i in range(5):
        print(f"\n--- Update {i+1}/5 at {datetime.now().strftime('%H:%M:%S')} ---")
        
        # Get quick summary
        summary = api.get_quick_summary()
        if 'error' not in summary:
            print(f"{summary['symbol']}: ${summary['price']:.4f} | EMA9: ${summary['ema9']:.4f} | Gap: {summary['gap_percent']:+.2f}% | Signal: {summary['signal']}")
        else:
            print(f"Error: {summary['error']}")
        
        # Wait 10 seconds before next update (except for last iteration)
        if i < 4:
            print("Waiting 10 seconds...")
            time.sleep(10)


def example_signal_analysis():
    """Example: Detailed signal analysis"""
    print("\n" + "=" * 60)
    print("Example 4: Detailed Signal Analysis")
    print("=" * 60)
    
    api = EMA9API()
    
    # Get complete signal data
    signal_data = api.get_current_signal()
    if 'error' in signal_data:
        print(f"Error getting signal: {signal_data['error']}")
        return
    
    print(f"Trading Signal Analysis for {signal_data['symbol']}")
    print("-" * 50)
    print(f"Signal Type: {signal_data['signal_type']}")
    print(f"Strength: {signal_data['signal_strength']}/100")
    print(f"Confidence: {signal_data['confidence']:.1%}")
    print(f"Timestamp: {signal_data['timestamp']}")
    
    print(f"\nRecommendation:")
    print(f"{signal_data['recommendation']}")
    
    if signal_data['reasons']:
        print(f"\nAnalysis Reasons:")
        for i, reason in enumerate(signal_data['reasons'], 1):
            print(f"  {i}. {reason}")
    
    # Additional context
    price_data = api.get_price_vs_ema9()
    if 'error' not in price_data:
        print(f"\nPrice Context:")
        print(f"• Current price is {price_data['gap_percentage']:+.2f}% {price_data['position']} EMA9")
        print(f"• EMA9 is currently {price_data['ema_trend']}")
        print(f"• Gap amount: ${abs(price_data['gap_amount']):.6f}")


def example_json_output():
    """Example: Getting data in JSON format for integration"""
    print("\n" + "=" * 60)
    print("Example 5: JSON Output for Integration")
    print("=" * 60)
    
    api = EMA9API()
    
    # Get all data as JSON
    data = api.get_ema9_data()
    
    print("Complete EMA9 data as JSON:")
    print("-" * 40)
    print(json.dumps(data, indent=2, default=str))
    
    # Save to file example
    filename = f"ema9_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nData saved to: {filename}")
    except Exception as e:
        print(f"Could not save to file: {e}")


def main():
    """Run all examples"""
    print("EMA9 Backend Examples")
    print("Trading Symbol from .env file will be used")
    
    try:
        # Run all examples
        example_basic_usage()
        example_api_class()
        example_signal_analysis()
        example_json_output()
        
        # Ask if user wants to run monitoring
        print(f"\n{'='*60}")
        print("Would you like to run the monitoring example?")
        print("This will check EMA9 data 5 times with 10-second intervals.")
        
        user_input = input("Run monitoring? (y/N): ").lower()
        if user_input == 'y' or user_input == 'yes':
            example_monitoring_loop()
        
        print(f"\n{'='*60}")
        print("Examples completed!")
        print("\nTo use the backend in your own code:")
        print("1. Import: from ema9_api import EMA9API")
        print("2. Initialize: api = EMA9API()")
        print("3. Get data: data = api.get_ema9_data()")
        
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()