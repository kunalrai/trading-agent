#!/usr/bin/env python3
"""
Flask Dashboard for CoinDCX Market Scanner
"""

import sys
import os
from flask import Flask, render_template, request, jsonify, Response
import threading
import time
from datetime import datetime
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import CoinDCXFuturesTrader
from coindcx_trading import CoinDCXTrading

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Initialize trading client
trading_client = CoinDCXTrading()

# Global variables for scan results and status
scan_results = []
scan_status = {"is_scanning": False, "progress": 0, "current_symbol": "", "message": "Ready"}
last_scan_time = None
scan_stop_flag = False

def perform_scan(scan_type="quick", min_volume=50000):
    """Perform market scan in background thread"""
    global scan_results, scan_status, last_scan_time, scan_stop_flag

    try:
        scan_status["is_scanning"] = True
        scan_status["progress"] = 0
        scan_status["message"] = f"Starting {scan_type} market scan..."
        scan_stop_flag = False  # Reset stop flag at start

        # Clear previous results at the start of a new scan
        scan_results.clear()

        # Create trader instance
        trader = CoinDCXFuturesTrader()
        trader.enable_full_market_scan(min_volume=min_volume)

        # Get tradable symbols with appropriate limits based on scan type
        scan_status["message"] = "Fetching tradable symbols..."
        
        # Set symbol limits based on scan type
        if scan_type == "quick":
            max_symbols = 15
        elif scan_type == "medium":
            max_symbols = 30
        elif scan_type == "full":
            max_symbols = None  # No limit for full scan
        else:
            max_symbols = 15  # Default to quick scan limit
        
        tradable_symbols = trader.get_all_tradable_symbols(max_symbols=max_symbols)

        if not tradable_symbols:
            scan_status["message"] = "No tradable symbols found!"
            scan_status["is_scanning"] = False
            return

        total_symbols = len(tradable_symbols)
        scan_status["message"] = f"Analyzing {total_symbols} symbols..."

        for i, symbol in enumerate(tradable_symbols, 1):
            # Check if scan should be stopped
            if scan_stop_flag:
                scan_status["message"] = f"Scan stopped by user. Analyzed {len(scan_results)} symbols."
                scan_status["is_scanning"] = False
                scan_status["current_symbol"] = ""
                app.logger.info(f"🛑 Scan stopped by user at symbol {symbol}")
                return

            scan_status["current_symbol"] = symbol
            scan_status["progress"] = int((i-1) / total_symbols * 100)
            scan_status["message"] = f"Analyzing {symbol} ({i}/{total_symbols})..."

            try:
                analysis = trader.analyze_single_coin(symbol)
                # Add result immediately to global results (real-time streaming)
                scan_results.append(analysis)
                app.logger.info(f"✅ Added result for {symbol} - Total results: {len(scan_results)}")
            except Exception as e:
                error_result = {
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                # Add error result immediately too
                scan_results.append(error_result)
                app.logger.warning(f"❌ Added error result for {symbol}: {e}")

            # Small delay to avoid rate limiting
            time.sleep(0.3)

        # Update final status
        last_scan_time = datetime.now()
        scan_status["progress"] = 100
        scan_status["message"] = f"Scan completed! Analyzed {len(scan_results)} symbols."
        scan_status["is_scanning"] = False
        scan_status["current_symbol"] = ""

    except Exception as e:
        scan_status["message"] = f"Scan failed: {str(e)}"
        scan_status["is_scanning"] = False
        scan_status["progress"] = 0

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html',
                         scan_results=scan_results,
                         scan_status=scan_status,
                         last_scan_time=last_scan_time)

@app.route('/scan', methods=['POST'])
def start_scan():
    """Start a market scan"""
    if scan_status["is_scanning"]:
        return jsonify({"error": "Scan already in progress"}), 400

    scan_type = request.form.get('scan_type', 'quick')
    min_volume = int(request.form.get('min_volume', 50000))

    # Start scan in background thread
    thread = threading.Thread(target=perform_scan, args=(scan_type, min_volume))
    thread.daemon = True
    thread.start()

    return jsonify({"message": f"Started {scan_type} scan", "status": "running"})

@app.route('/scan_status')
def get_scan_status():
    """Get current scan status"""
    return jsonify(scan_status)

@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    """Stop the current scan"""
    global scan_stop_flag, scan_status
    
    try:
        if not scan_status["is_scanning"]:
            return jsonify({
                "success": False,
                "error": "No scan is currently running"
            }), 400
        
        scan_stop_flag = True
        app.logger.info("🛑 Scan stop requested by user")
        
        return jsonify({
            "success": True,
            "message": "Scan stop requested successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error stopping scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/results')
def get_results():
    """Get scan results as JSON"""
    return jsonify({
        "results": scan_results,
        "last_scan_time": last_scan_time.isoformat() if last_scan_time else None,
        "total_symbols": len(scan_results)
    })

@app.route('/results/live')
def get_live_results():
    """Get current scan results with additional metadata for live updates"""
    return jsonify({
        "results": scan_results,
        "count": len(scan_results),
        "is_scanning": scan_status["is_scanning"],
        "progress": scan_status["progress"],
        "current_symbol": scan_status.get("current_symbol", ""),
        "message": scan_status.get("message", ""),
        "last_scan_time": last_scan_time.isoformat() if last_scan_time else None
    })

@app.route('/api/symbols/<symbol>')
def get_symbol_details(symbol):
    """Get detailed analysis for a specific symbol"""
    for result in scan_results:
        if result.get('symbol') == symbol and 'error' not in result:
            return jsonify(result)

    return jsonify({"error": "Symbol not found or analysis failed"}), 404

@app.route('/create_order', methods=['POST'])
def create_order():
    """Create a trading order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['symbol', 'signal', 'entry_price', 'take_profit', 'stop_loss', 'position_size']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
        
        symbol = data['symbol']
        signal = data['signal']
        entry_price = float(data['entry_price'])
        take_profit = float(data['take_profit'])
        stop_loss = float(data['stop_loss'])
        position_size_usd = float(data['position_size'])
        confidence = data.get('confidence', 0)
        leverage = data.get('leverage', 10)
        order_type = data.get('order_type', 'market_order')
        is_manual = data.get('manual_trade', False)
        
        # Validate data types and ranges
        if position_size_usd <= 0:
            return jsonify({"success": False, "error": "Position size must be positive"}), 400
        
        if leverage < 1 or leverage > 100:
            return jsonify({"success": False, "error": "Leverage must be between 1 and 100"}), 400
        
        if signal not in ['LONG', 'SHORT']:
            return jsonify({"success": False, "error": "Signal must be LONG or SHORT"}), 400
            
        # Validate TP/SL values
        if take_profit <= 0:
            return jsonify({"success": False, "error": f"Take Profit must be positive, got: {take_profit}"}), 400
            
        if stop_loss <= 0:
            return jsonify({"success": False, "error": f"Stop Loss must be positive, got: {stop_loss}"}), 400
            
        # Validate price relationships based on signal
        if signal == 'LONG':
            if take_profit <= entry_price:
                return jsonify({"success": False, "error": f"LONG: Take Profit ({take_profit}) must be higher than Entry ({entry_price})"}), 400
            if stop_loss >= entry_price:
                return jsonify({"success": False, "error": f"LONG: Stop Loss ({stop_loss}) must be lower than Entry ({entry_price})"}), 400
        elif signal == 'SHORT':
            if take_profit >= entry_price:
                return jsonify({"success": False, "error": f"SHORT: Take Profit ({take_profit}) must be lower than Entry ({entry_price})"}), 400
            if stop_loss <= entry_price:
                return jsonify({"success": False, "error": f"SHORT: Stop Loss ({stop_loss}) must be higher than Entry ({entry_price})"}), 400
        
        # Log order attempt with detailed debugging
        trade_type = "Manual" if is_manual else "Auto"
        app.logger.info(f"🎯 Creating {trade_type} {signal} order for {symbol}")
        app.logger.info(f"   Entry: ${entry_price} (type: {type(entry_price)})")
        app.logger.info(f"   TP: ${take_profit} (type: {type(take_profit)})")
        app.logger.info(f"   SL: ${stop_loss} (type: {type(stop_loss)})")
        app.logger.info(f"   Position Size: ${position_size_usd} (type: {type(position_size_usd)})")
        app.logger.info(f"   Confidence: {confidence}%, Leverage: {leverage}x")
        app.logger.info(f"   Order Type: {order_type}, Is Manual: {is_manual}")
        
        # Validate trading client
        if not trading_client.enabled:
            return jsonify({
                "success": False, 
                "error": "Trading not enabled - please check API credentials in .env file"
            }), 400
        
        # Create mock analysis object for the trading client
        mock_analysis = {
            'symbol': symbol,
            'signal': signal,
            'combined_confidence': confidence,
            'trade_levels': {
                'entry_price': entry_price,
                'take_profit': take_profit,
                'stop_loss': stop_loss
            }
        }
        
        # Create order using CoinDCX trading client
        if is_manual:
            # For manual trades, use direct order creation with custom parameters
            # Convert symbol format (e.g., "BTC/USDT" -> "B-BTC_USDT")
            if '/' in symbol:
                base, quote = symbol.split('/')
                coindcx_symbol = f"B-{base}_{quote}"
            else:
                coindcx_symbol = symbol
            
            # Calculate quantity using trading client helper (uses .env settings)
            app.logger.info(f"🔢 Quantity Calculation Debug:")
            app.logger.info(f"   Position Size USD: {position_size_usd} (type: {type(position_size_usd)})")
            app.logger.info(f"   Entry Price: {entry_price} (type: {type(entry_price)})")
            app.logger.info(f"   Default Quantity from .env: {trading_client.default_quantity}")
            app.logger.info(f"   Min Quantity from .env: {trading_client.min_quantity}")
            
            if position_size_usd > 0:
                quantity = trading_client.calculate_quantity(position_size_usd, entry_price)
                app.logger.info(f"   Using calculated quantity: {quantity}")
            else:
                # Use default quantity from .env file
                quantity = trading_client.calculate_quantity()
                app.logger.info(f"   Using default quantity: {quantity}")
            
            app.logger.info(f"   Final quantity: {quantity} (type: {type(quantity)})")
            side = "buy" if signal == "LONG" else "sell"
            
            result = trading_client.create_futures_order(
                symbol=coindcx_symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price if order_type == 'limit_order' else None,
                take_profit=take_profit,
                stop_loss=stop_loss,
                leverage=leverage
            )
        else:
            # Use existing analysis-based order creation
            result = trading_client.create_order_from_analysis(mock_analysis, position_size_usd)
        
        # Handle both dict and list responses from CoinDCX API
        if isinstance(result, dict) and "error" not in result:
            return jsonify({
                "success": True,
                "message": "Order created successfully",
                "order_id": result.get('id'),
                "result": result
            })
        elif isinstance(result, list) and len(result) > 0:
            # CoinDCX sometimes returns a list - use first item
            first_item = result[0] if result else {}
            return jsonify({
                "success": True,
                "message": "Order created successfully",
                "order_id": first_item.get('id') if isinstance(first_item, dict) else None,
                "result": result
            })
        else:
            # Handle error cases
            error_msg = "Unknown error"
            if isinstance(result, dict):
                error_msg = result.get("error", "Unknown error")
            elif isinstance(result, list) and len(result) == 0:
                error_msg = "Empty response from API"
            else:
                error_msg = str(result)
                
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error creating order: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/trading_status')
def get_trading_status():
    """Get trading client status"""
    return jsonify({
        "enabled": trading_client.enabled,
        "has_credentials": bool(trading_client.api_key and trading_client.secret_key),
        "leverage": trading_client.leverage,
        "order_type": trading_client.order_type,
        "default_quantity": trading_client.default_quantity,
        "min_quantity": trading_client.min_quantity
    })

@app.route('/test_api', methods=['POST'])
def test_api_connection():
    """Test CoinDCX API connection"""
    try:
        result = trading_client.test_api_connection()
        
        if "error" not in result:
            return jsonify({
                "success": True,
                "message": "API connection successful",
                "balance_data": result
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error testing API: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/positions')
def get_positions():
    """Get current futures positions"""
    try:
        # Get query parameters for pagination
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        margin_currencies = request.args.getlist('margin_currency')
        
        # Default to USDT if no currencies specified
        if not margin_currencies:
            margin_currencies = ["USDT"]
        
        app.logger.info(f"🔍 Fetching positions: page={page}, size={size}, currencies={margin_currencies}")
        
        result = trading_client.get_futures_positions(
            page=page, 
            size=size, 
            margin_currencies=margin_currencies
        )
        
        if "error" not in result:
            return jsonify({
                "success": True,
                "positions": result,
                "page": page,
                "size": size,
                "margin_currencies": margin_currencies
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error fetching positions: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/wallets')
def get_wallets():
    """Get current futures wallet balances"""
    try:
        app.logger.info("🔍 Fetching futures wallet balances...")
        
        result = trading_client.get_futures_wallets()
        
        if "error" not in result:
            return jsonify({
                "success": True,
                "wallets": result.get('wallets', []),
                "summary": result.get('summary', {}),
                "count": result.get('count', 0)
            })
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error fetching wallets: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/wallets/history')
def get_wallet_history():
    """Get wallet balance history from database"""
    try:
        from database import get_db_manager
        
        # Get query parameters
        currency = request.args.get('currency')  # Optional currency filter
        hours = int(request.args.get('hours', 24))  # Default 24 hours
        
        app.logger.info(f"📊 Fetching wallet history: currency={currency}, hours={hours}")
        
        db_manager = get_db_manager()
        history_data = db_manager.get_wallet_history(currency=currency, hours=hours)
        
        return jsonify({
            "success": True,
            "history": history_data,
            "count": len(history_data),
            "currency": currency,
            "hours": hours
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching wallet history: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/wallets/history/daily')
def get_daily_wallet_history():
    """Get daily wallet balance history from database (one point per day)"""
    try:
        from database import get_db_manager
        
        # Get query parameters
        currency = request.args.get('currency')  # Optional currency filter
        days = int(request.args.get('days', 30))  # Default 30 days
        
        app.logger.info(f"📊 Fetching daily wallet history: currency={currency}, days={days}")
        
        db_manager = get_db_manager()
        history_data = db_manager.get_daily_wallet_history(currency=currency, days=days)
        
        return jsonify({
            "success": True,
            "history": history_data,
            "count": len(history_data),
            "currency": currency,
            "days": days,
            "type": "daily"
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching daily wallet history: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/wallets/summary/history')
def get_wallet_summary_history():
    """Get wallet summary history from database"""
    try:
        from database import get_db_manager
        
        # Get query parameters
        hours = int(request.args.get('hours', 24))  # Default 24 hours
        
        app.logger.info(f"📈 Fetching wallet summary history: hours={hours}")
        
        db_manager = get_db_manager()
        summary_data = db_manager.get_balance_summary_history(hours=hours)
        
        return jsonify({
            "success": True,
            "summary_history": summary_data,
            "count": len(summary_data),
            "hours": hours
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching wallet summary history: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/wallets/latest')
def get_latest_wallet_balances():
    """Get latest wallet balances from database"""
    try:
        from database import get_db_manager
        
        app.logger.info("💰 Fetching latest wallet balances from database")
        
        db_manager = get_db_manager()
        latest_data = db_manager.get_latest_balances()
        
        return jsonify({
            "success": True,
            "latest_balances": latest_data,
            "currencies_count": len(latest_data)
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching latest wallet balances: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/database/cleanup', methods=['POST'])
def cleanup_database():
    """Clean up old database records"""
    try:
        from database import get_db_manager
        
        # Get days parameter from request
        data = request.get_json() or {}
        days = int(data.get('days', 30))
        
        app.logger.info(f"🧹 Starting database cleanup: keeping {days} days")
        
        db_manager = get_db_manager()
        deleted_count = db_manager.cleanup_old_data(days=days)
        
        return jsonify({
            "success": True,
            "deleted_records": deleted_count,
            "days_kept": days
        })
        
    except Exception as e:
        app.logger.error(f"Error during database cleanup: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/positions/exit', methods=['POST'])
def exit_position():
    """Exit a specific futures position"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'position_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing position_id in request"
            }), 400
        
        position_id = data['position_id']
        
        app.logger.info(f"🚪 Exit position request: {position_id}")
        
        # Validate trading client
        if not trading_client.enabled:
            return jsonify({
                "success": False,
                "error": "Trading not enabled - please check API credentials in .env file"
            }), 400
        
        # Exit the position
        result = trading_client.exit_position(position_id)
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message", "Position exited successfully"),
                "position_id": position_id,
                "group_id": result.get("group_id"),
                "response": result.get("response")
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to exit position"),
                "position_id": position_id
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error exiting position: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/positions/exit_all', methods=['POST'])
def exit_all_positions():
    """Exit all futures positions"""
    try:
        data = request.get_json() or {}
        
        # Get margin currency (default to USDT)
        margin_currency = data.get('margin_currency', 'USDT')
        
        app.logger.info(f"🚪 Exit all positions request: {margin_currency}")
        
        # Validate trading client
        if not trading_client.enabled:
            return jsonify({
                "success": False,
                "error": "Trading not enabled - please check API credentials in .env file"
            }), 400
        
        # Confirmation check for safety
        confirm = data.get('confirm', False)
        if not confirm:
            return jsonify({
                "success": False,
                "error": "Exit all positions requires confirmation. Set 'confirm': true in request body."
            }), 400
        
        # Exit all positions
        result = trading_client.exit_all_positions(margin_currency)
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message"),
                "positions_count": result.get("positions_count", 0),
                "successful_exits": result.get("successful_exits", 0),
                "failed_exits": result.get("failed_exits", 0),
                "results": result.get("results", [])
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to exit positions")
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error exiting all positions: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("🚀 Starting CoinDCX Market Scanner Dashboard...")
    print("📊 Visit http://localhost:5000 to access the dashboard")
    print("💡 Use Ctrl+C to stop the server")
    app.run(debug=True, host='0.0.0.0', port=5000)