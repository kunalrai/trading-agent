#!/usr/bin/env python3
"""
CoinDCX Futures Trading Module
"""

import hmac
import hashlib
import json
import time
import requests
import logging
from typing import Dict, Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class CoinDCXTrading:
    def __init__(self):
        """Initialize CoinDCX trading client"""
        self.api_key = os.getenv('COINDCX_API_KEY')
        self.secret_key = os.getenv('COINDCX_SECRET_KEY')
        self.base_url = "https://api.coindcx.com"
        
        # Trading configuration from environment
        self.leverage = int(os.getenv('COINDCX_LEVERAGE', 10))
        self.order_type = os.getenv('COINDCX_ORDER_TYPE', 'market_order')
        self.time_in_force = os.getenv('COINDCX_TIME_IN_FORCE', 'good_till_cancel')
        self.notification = os.getenv('COINDCX_NOTIFICATION', 'email_notification')
        self.default_quantity = float(os.getenv('COINDCX_DEFAULT_QUANTITY', 10.0))
        self.min_quantity = float(os.getenv('COINDCX_MIN_QUANTITY', 1.0))
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        if not self.api_key or not self.secret_key:
            self.logger.warning("CoinDCX API credentials not found in environment variables")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info("CoinDCX trading client initialized")

    def calculate_quantity(self, position_size_usd: Optional[float] = None, 
                          entry_price: Optional[float] = None) -> float:
        """
        Calculate order quantity based on position size or use default
        
        Args:
            position_size_usd: Position size in USD (optional)
            entry_price: Entry price for calculation (required if position_size_usd provided)
        
        Returns:
            Calculated quantity, properly formatted for CoinDCX
        """
        if position_size_usd and entry_price:
            # Calculate quantity based on position size
            raw_quantity = position_size_usd / entry_price
            # CoinDCX requires quantity divisible by 0.5 (1.0, 1.5, 2.0, 2.5, etc.)
            formatted_quantity = round(raw_quantity * 2) / 2  # Round to nearest 0.5
                
            self.logger.info(f"💰 Calculated quantity from ${position_size_usd} at ${entry_price}: {raw_quantity} -> {formatted_quantity}")
        else:
            # Use default quantity from environment 
            formatted_quantity = float(self.default_quantity)
            self.logger.info(f"📊 Using default quantity from .env: {formatted_quantity}")
        
        # Ensure minimum quantity requirement
        if formatted_quantity < self.min_quantity:
            formatted_quantity = float(self.min_quantity)
            self.logger.info(f"📏 Adjusted to minimum quantity: {formatted_quantity}")
        
        # Final validation: ensure it's divisible by 0.5
        if formatted_quantity % 0.5 != 0:
            formatted_quantity = round(formatted_quantity)
            self.logger.warning(f"⚠️  Final rounding to whole number: {formatted_quantity}")
        
        # Convert to int if it's a whole number
        if formatted_quantity == int(formatted_quantity):
            formatted_quantity = int(formatted_quantity)
            
        self.logger.info(f"✅ Final calculated quantity: {formatted_quantity} (type: {type(formatted_quantity)})")
        
        return formatted_quantity

    def _generate_signature(self, body: str) -> str:
        """Generate API signature"""
        secret_bytes = bytes(self.secret_key, encoding='utf-8')
        return hmac.new(secret_bytes, body.encode(), hashlib.sha256).hexdigest()

    def _make_request(self, endpoint: str, data: Dict, method: str = "POST") -> Dict:
        """Make authenticated request to CoinDCX API"""
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        timestamp = int(round(time.time() * 1000))
        data["timestamp"] = timestamp
        
        json_body = json.dumps(data, separators=(',', ':'))
        signature = self._generate_signature(json_body)
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }
        
        try:
            self.logger.info(f"🔍 Making {method} API request to: {url}")
            self.logger.info(f"📋 Request body: {json_body}")
            self.logger.info(f"🔑 Headers: {dict(headers)}")
            
            if method.upper() == "GET":
                response = requests.get(url, data=json_body, headers=headers, timeout=10)
            else:
                response = requests.post(url, data=json_body, headers=headers, timeout=10)
            
            self.logger.info(f"📡 Response status: {response.status_code}")
            self.logger.info(f"📄 Response body: {response.text}")
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return {"error": f"Invalid JSON response: {response.text if 'response' in locals() else 'No response'}"}

    def create_futures_order(self, symbol: str, side: str, quantity: float, 
                           entry_price: Optional[float] = None,
                           take_profit: Optional[float] = None, 
                           stop_loss: Optional[float] = None,
                           leverage: Optional[int] = None) -> Dict:
        """
        Create a futures order on CoinDCX
        
        Args:
            symbol: Trading pair (e.g., "B-BTC_USDT")
            side: "buy" or "sell"
            quantity: Order quantity
            entry_price: Entry price for limit orders (None for market orders)
            take_profit: Take profit price
            stop_loss: Stop loss price
            leverage: Leverage (uses default if None)
        """
        if not self.enabled:
            return {"error": "Trading not enabled - API credentials missing"}
        
        # Use provided leverage or default
        order_leverage = leverage or self.leverage
        
        # Determine order type and price
        if entry_price and self.order_type == 'limit_order':
            order_type = 'limit_order'
            price = str(entry_price)
        else:
            order_type = 'market_order'
            price = None
        
        # Build order data - ensure proper data types
        # Format quantity to ensure it's divisible by 1.0 (CoinDCX requirement)
        # If quantity is 0 or very small, use default quantity from .env
        if quantity <= 0 or quantity < self.min_quantity:
            formatted_quantity = float(self.default_quantity)
            self.logger.info(f"📊 Using default quantity from .env: {formatted_quantity} (original: {quantity})")
        else:
            # CoinDCX requires quantity to be divisible by 1.0 (whole numbers or .5)
            # Round to nearest 0.5 and ensure it meets minimum
            formatted_quantity = round(float(quantity) * 2) / 2  # Round to nearest 0.5
            
            # If still too small, use minimum
            if formatted_quantity < self.min_quantity:
                formatted_quantity = float(self.min_quantity)
                
            self.logger.info(f"📏 Quantity formatting: {quantity} -> {formatted_quantity}")
            
        # Final validation: ensure it's a proper format (integer or .5)
        # CoinDCX accepts: 1.0, 2.0, 2.5, 3.0, etc.
        if formatted_quantity % 0.5 != 0:
            formatted_quantity = round(formatted_quantity)
            self.logger.warning(f"⚠️  Final rounding to whole number: {formatted_quantity}")
        
        # Convert to int if it's a whole number for cleaner JSON
        if formatted_quantity == int(formatted_quantity):
            formatted_quantity = int(formatted_quantity)
        
        self.logger.info(f"✅ Final quantity: {formatted_quantity} (type: {type(formatted_quantity)}, divisible by 0.5: {formatted_quantity % 0.5 == 0})")
            
        order_data = {
            "side": str(side).lower(),
            "pair": str(symbol),
            "order_type": str(order_type),
            "total_quantity": formatted_quantity,  # Use properly formatted quantity
            "leverage": int(order_leverage),
            "notification": str(self.notification),
            "time_in_force": str(self.time_in_force),
            "hidden": False,
            "post_only": False
        }
        
        # Add price for limit orders - CoinDCX expects strings for prices
        if price:
            order_data["price"] = str(float(price))
            order_data["stop_price"] = str(float(price))
        
        # Add TP/SL if provided - ensure proper formatting and minimum requirements
        tp_price = None
        sl_price = None
        min_tp_percentage = float(os.getenv('COINDCX_MIN_TP_PERCENTAGE', 0.5))  # Minimum TP percentage (default: 0.5%)
        min_sl_percentage = float(os.getenv('COINDCX_MIN_SL_PERCENTAGE', 0.2))  # Minimum SL percentage (default: 0.2%)
        
        # Enable TP/SL functionality
        skip_tp_sl = False  # Set to True to disable TP/SL for testing
        
        # Debug: Show what TP/SL values were passed
        self.logger.info(f"🔍 TP/SL Input Values:")
        self.logger.info(f"   take_profit: {take_profit} (type: {type(take_profit)})")
        self.logger.info(f"   stop_loss: {stop_loss} (type: {type(stop_loss)})")
        self.logger.info(f"   entry_price: {entry_price} (type: {type(entry_price)})")
        self.logger.info(f"   skip_tp_sl: {skip_tp_sl}")
        
        if skip_tp_sl:
            self.logger.info("⚠️ TEMPORARILY SKIPPING TP/SL - Testing basic order creation")
        elif take_profit and stop_loss and entry_price:
            tp_price = round(float(take_profit), 4)
            sl_price = round(float(stop_loss), 4)
            
            # Calculate percentages and validate minimums
            if side == "buy":  # LONG
                tp_percentage = ((tp_price - entry_price) / entry_price) * 100
                sl_percentage = ((entry_price - sl_price) / entry_price) * 100
                
                # Check minimum requirements
                tp_valid = tp_price > entry_price and tp_percentage >= min_tp_percentage
                sl_valid = sl_price < entry_price and sl_percentage >= min_sl_percentage
                
                self.logger.info(f"🔍 LONG Trade Validation:")
                self.logger.info(f"   Entry: {entry_price}")
                self.logger.info(f"   TP: {tp_price} (+{tp_percentage:.2f}%) - Valid: {tp_valid} (min: {min_tp_percentage}%)")
                self.logger.info(f"   SL: {sl_price} (-{sl_percentage:.2f}%) - Valid: {sl_valid} (min: {min_sl_percentage}%)")
                
                # Only add TP/SL if they meet minimum requirements
                if tp_valid:
                    order_data["take_profit_price"] = float(tp_price)
                    self.logger.info(f"✅ Added Take Profit: {tp_price}")
                else:
                    self.logger.warning(f"⚠️ Skipping TP - below minimum {min_tp_percentage}% or invalid")
                    
                if sl_valid:
                    order_data["stop_loss_price"] = float(sl_price)
                    self.logger.info(f"✅ Added Stop Loss: {sl_price}")
                else:
                    self.logger.warning(f"⚠️ Skipping SL - below minimum {min_sl_percentage}% or invalid")
                    
            else:  # SHORT
                tp_percentage = ((entry_price - tp_price) / entry_price) * 100
                sl_percentage = ((sl_price - entry_price) / entry_price) * 100
                
                # Check minimum requirements
                tp_valid = tp_price < entry_price and tp_percentage >= min_tp_percentage
                sl_valid = sl_price > entry_price and sl_percentage >= min_sl_percentage
                
                self.logger.info(f"🔍 SHORT Trade Validation:")
                self.logger.info(f"   Entry: {entry_price}")
                self.logger.info(f"   TP: {tp_price} (-{tp_percentage:.2f}%) - Valid: {tp_valid} (min: {min_tp_percentage}%)")
                self.logger.info(f"   SL: {sl_price} (+{sl_percentage:.2f}%) - Valid: {sl_valid} (min: {min_sl_percentage}%)")
                
                # Only add TP/SL if they meet minimum requirements
                if tp_valid:
                    order_data["take_profit_price"] = float(tp_price)
                    self.logger.info(f"✅ Added Take Profit: {tp_price}")
                else:
                    self.logger.warning(f"⚠️ Skipping TP - below minimum {min_tp_percentage}% or invalid")
                    
                if sl_valid:
                    order_data["stop_loss_price"] = float(sl_price)  
                    self.logger.info(f"✅ Added Stop Loss: {sl_price}")
                else:
                    self.logger.warning(f"⚠️ Skipping SL - below minimum {min_sl_percentage}% or invalid")
        else:
            self.logger.info("🔍 No TP/SL validation - missing values or entry price")
        
        body = {"order": order_data}
        
        self.logger.info(f"🎯 Creating {side} order for {symbol}: {quantity} -> {formatted_quantity} @ leverage {order_leverage}x")
        self.logger.info(f"� Order Data Details:")
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Side: {side}")
        self.logger.info(f"   Quantity: {formatted_quantity}")
        self.logger.info(f"   Order Type: {order_type}")
        self.logger.info(f"   Entry Price: {entry_price}")
        self.logger.info(f"   Take Profit: {take_profit}")
        self.logger.info(f"   Stop Loss: {stop_loss}")
        self.logger.info(f"   Leverage: {order_leverage}")
        self.logger.info(f"   TP/SL in order_data: TP={order_data.get('take_profit_price')}, SL={order_data.get('stop_loss_price')}")
        self.logger.info(f"�📋 Complete Order Payload: {json.dumps(body, indent=2, default=str)}")
        
        endpoint = "/exchange/v1/derivatives/futures/orders/create"
        result = self._make_request(endpoint, body)
        
        # Log the response type and content for debugging
        self.logger.info(f"🔍 API Response Type: {type(result)}")
        self.logger.info(f"📋 API Response Content: {result}")
        
        if isinstance(result, dict) and "error" not in result:
            self.logger.info(f"✅ Order created successfully: {result}")
        elif isinstance(result, list):
            self.logger.info(f"✅ Order created successfully (list response): {result}")
        else:
            self.logger.error(f"❌ Order creation failed: {result}")
        
        return result

    def create_order_from_analysis(self, analysis: Dict, position_size_usd: float = 100) -> Dict:
        """
        Create order based on trading analysis
        
        Args:
            analysis: Analysis result from trading bot
            position_size_usd: Position size in USD
        """
        if not analysis.get('trade_levels'):
            return {"error": "No trade levels in analysis"}
        
        symbol = analysis['symbol']
        signal = analysis['signal']
        confidence = analysis.get('combined_confidence', 0)
        
        # Convert symbol format (e.g., "BTC/USDT" -> "B-BTC_USDT")
        if '/' in symbol:
            base, quote = symbol.split('/')
            coindcx_symbol = f"B-{base}_{quote}"
        else:
            coindcx_symbol = symbol
        
        trade_levels = analysis['trade_levels']
        entry_price = trade_levels.get('entry_price')
        take_profit = trade_levels.get('take_profit')
        stop_loss = trade_levels.get('stop_loss')
        
        # Calculate quantity using the helper method (uses .env settings)
        if entry_price and entry_price > 0:
            if position_size_usd > 0:
                quantity = self.calculate_quantity(position_size_usd, entry_price)
                self.logger.info(f"📊 Calculated quantity from position size: {quantity}")
            else:
                quantity = self.calculate_quantity()
                self.logger.info(f"📊 Using default quantity from .env: {quantity}")
        else:
            return {"error": "Invalid entry price"}
        
        # Determine side
        side = "buy" if signal == "LONG" else "sell" if signal == "SHORT" else None
        if not side:
            return {"error": "Invalid signal - must be LONG or SHORT"}
        
        self.logger.info(f"🎯 Creating order from analysis:")
        self.logger.info(f"   Symbol: {symbol} -> {coindcx_symbol}")
        self.logger.info(f"   Signal: {signal} ({confidence}% confidence)")
        self.logger.info(f"   Position Size: ${position_size_usd}")
        self.logger.info(f"   Entry: ${entry_price}")
        self.logger.info(f"   Quantity: {quantity} (formatted for CoinDCX)")
        self.logger.info(f"   TP: ${take_profit}")
        self.logger.info(f"   SL: ${stop_loss}")
        
        return self.create_futures_order(
            symbol=coindcx_symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss
        )

    def get_account_balance(self) -> Dict:
        """Get account balance"""
        endpoint = "/exchange/v1/users/balances"
        return self._make_request(endpoint, {})

    def test_api_connection(self) -> Dict:
        """Test API connection with a simple balance request"""
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        self.logger.info("🔍 Testing API connection...")
        result = self.get_account_balance()
        
        if "error" not in result:
            self.logger.info("✅ API connection successful")
        else:
            self.logger.error(f"❌ API connection failed: {result}")
        
        return result

    def get_open_positions(self) -> Dict:
        """Get open positions (active orders)"""
        endpoint = "/exchange/v1/derivatives/futures/orders/active"
        return self._make_request(endpoint, {})

    def get_futures_positions(self, page: int = 1, size: int = 10, 
                             margin_currencies: Optional[list] = None) -> Dict:
        """
        Get futures positions from CoinDCX
        
        Args:
            page: Page number for pagination (default: 1)
            size: Number of positions per page (default: 10)
            margin_currencies: List of margin currencies to filter by (default: ["USDT"])
            
        Returns:
            Dict containing positions data or error message
        """
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        # Default to USDT if no margin currencies specified
        if margin_currencies is None:
            margin_currencies = ["USDT"]
        
        # Build request body according to CoinDCX API specification
        body = {
            "page": str(page),
            "size": str(size),
            "margin_currency_short_name": margin_currencies
        }
        
        self.logger.info(f"🔍 Fetching futures positions:")
        self.logger.info(f"   Page: {page}, Size: {size}")
        self.logger.info(f"   Margin Currencies: {margin_currencies}")
        
        endpoint = "/exchange/v1/derivatives/futures/positions"
        result = self._make_request(endpoint, body)
        
        if "error" not in result:
            # Handle different response formats: direct array or nested structure
            positions = []
            if isinstance(result, list):
                # Direct array response
                positions = result
            elif isinstance(result, dict):
                # Nested structure response
                if 'data' in result and 'positions' in result['data']:
                    positions = result['data']['positions']
                elif 'positions' in result:
                    positions = result['positions']
                else:
                    # Assume the dict itself contains position data
                    positions = [result] if result else []
            
            positions_count = len(positions)
            self.logger.info(f"✅ Retrieved {positions_count} futures positions")
            
            # Log position details for debugging
            for pos in positions:
                if isinstance(pos, dict):
                    pair = pos.get('pair', 'Unknown')
                    active_pos = pos.get('active_pos', 0)
                    inactive_buy = pos.get('inactive_pos_buy', 0)
                    inactive_sell = pos.get('inactive_pos_sell', 0)
                    margin = pos.get('locked_margin', 0)
                    self.logger.info(f"   📊 {pair}: Active={active_pos}, Buy={inactive_buy}, Sell={inactive_sell}, Margin={margin}")
            
            # Return positions in consistent format
            return {
                "success": True,
                "positions": positions,
                "count": positions_count
            }
        else:
            self.logger.error(f"❌ Failed to retrieve futures positions: {result}")
        
        return result

    def get_futures_wallets(self) -> Dict:
        """
        Get futures wallet balances from CoinDCX
        
        Returns:
            Dict containing wallet data or error message
        """
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        # Build request body with timestamp only
        body = {
            "timestamp": int(round(time.time() * 1000))
        }
        
        self.logger.info("🔍 Fetching futures wallet balances...")
        
        endpoint = "/exchange/v1/derivatives/futures/wallets"
        result = self._make_request(endpoint, body, method="GET")
        
        if "error" not in result:
            # Handle wallet response format
            wallets = []
            if isinstance(result, list):
                # Direct array response
                wallets = result
            elif isinstance(result, dict):
                # Nested structure response
                if 'data' in result and 'wallets' in result['data']:
                    wallets = result['data']['wallets']
                elif 'wallets' in result:
                    wallets = result['wallets']
                else:
                    # Assume the dict itself contains wallet data
                    wallets = [result] if result else []
            
            wallets_count = len(wallets)
            self.logger.info(f"✅ Retrieved {wallets_count} futures wallets")
            
            # Log wallet details for debugging
            total_available = 0  # Sum of available balances
            total_locked = 0     # Sum of locked balances
            for wallet in wallets:
                if isinstance(wallet, dict):
                    currency = wallet.get('currency_short_name', 'Unknown')
                    available_balance = float(wallet.get('balance', 0))  # API 'balance' field is available amount
                    locked = float(wallet.get('locked_balance', 0))
                    cross_margin = float(wallet.get('cross_user_margin', 0))
                    total_available += available_balance
                    total_locked += locked
                    self.logger.info(f"   💰 {currency}: Available={available_balance:.4f}, Locked={locked:.4f}, Cross Margin={cross_margin:.4f}")
            
            total_balance = total_available + total_locked  # Total = Available + Locked
            self.logger.info(f"📊 Total Available: {total_available:.4f}, Total Locked: {total_locked:.4f}, Total Balance: {total_balance:.4f}")
            
            # Store wallet data to database
            try:
                from database import store_wallet_data
                
                wallet_data_for_db = {
                    "wallets": wallets,
                    "count": wallets_count
                }
                
                summary_data_for_db = {
                    "total_balance": total_balance,
                    "total_locked": total_locked,
                    "available_balance": total_available
                }
                
                db_success = store_wallet_data(wallet_data_for_db, summary_data_for_db)
                if db_success:
                    self.logger.info("💾 Wallet data stored to database successfully")
                else:
                    self.logger.warning("⚠️ Failed to store wallet data to database")
                    
            except Exception as db_error:
                self.logger.error(f"❌ Database storage error: {db_error}")
            
            # Return wallets in consistent format
            return {
                "success": True,
                "wallets": wallets,
                "count": wallets_count,
                "summary": {
                    "total_balance": total_balance,        # Total = Available + Locked
                    "total_locked": total_locked,          # Sum of all locked amounts
                    "available_balance": total_available   # Sum of all available amounts (what user can actually use)
                }
            }
        else:
            self.logger.error(f"❌ Failed to retrieve futures wallets: {result}")
        
        return result

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        body = {"id": order_id}
        endpoint = "/exchange/v1/derivatives/futures/orders/cancel"
        return self._make_request(endpoint, body)
    
    def exit_position(self, position_id: str) -> Dict:
        """
        Exit a specific futures position by position ID
        
        Args:
            position_id (str): The unique position ID to exit
            
        Returns:
            Dict containing the API response
        """
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        self.logger.info(f"🚪 Exiting position: {position_id}")
        
        # Build request body with timestamp and position ID
        body = {
            "timestamp": int(round(time.time() * 1000)),
            "id": position_id
        }
        
        endpoint = "/exchange/v1/derivatives/futures/positions/exit"
        result = self._make_request(endpoint, body)
        
        if "error" not in result:
            self.logger.info(f"✅ Position exit successful: {result}")
            # Extract group_id if available
            group_id = result.get('data', {}).get('group_id', 'N/A')
            return {
                "success": True,
                "message": "Position exited successfully",
                "group_id": group_id,
                "position_id": position_id,
                "response": result
            }
        else:
            self.logger.error(f"❌ Position exit failed: {result}")
            return result
    
    def exit_all_positions(self, margin_currency: str = "USDT") -> Dict:
        """
        Exit all futures positions for a specific margin currency
        
        Args:
            margin_currency (str): The margin currency (default: USDT)
            
        Returns:
            Dict containing the results of all position exits
        """
        if not self.enabled:
            return {"error": "API credentials not configured"}
        
        self.logger.info(f"🚪 Exiting all positions for {margin_currency}")
        
        # First get all current positions
        positions_result = self.get_futures_positions(margin_currencies=[margin_currency])
        
        if "error" in positions_result:
            return {"error": f"Failed to fetch positions: {positions_result['error']}"}
        
        # Extract positions from the response
        positions = positions_result if isinstance(positions_result, list) else []
        
        # Filter for positions with active positions (not just orders)
        active_positions = []
        for position in positions:
            active_pos = float(position.get('active_pos', 0))
            if active_pos != 0:  # Has an active position
                active_positions.append(position)
        
        if not active_positions:
            return {
                "success": True,
                "message": "No active positions to exit",
                "positions_count": 0,
                "results": []
            }
        
        self.logger.info(f"📊 Found {len(active_positions)} active positions to exit")
        
        # Exit each position
        exit_results = []
        successful_exits = 0
        failed_exits = 0
        
        for position in active_positions:
            position_id = position.get('id')
            pair = position.get('pair', 'Unknown')
            active_pos = position.get('active_pos', 0)
            
            if not position_id:
                self.logger.warning(f"⚠️ No position ID found for {pair}")
                exit_results.append({
                    "pair": pair,
                    "position_id": None,
                    "success": False,
                    "error": "No position ID available"
                })
                failed_exits += 1
                continue
            
            self.logger.info(f"🔄 Exiting position: {pair} (ID: {position_id}, Size: {active_pos})")
            
            # Exit this position
            exit_result = self.exit_position(position_id)
            
            if exit_result.get("success"):
                self.logger.info(f"✅ Successfully exited {pair}")
                successful_exits += 1
                exit_results.append({
                    "pair": pair,
                    "position_id": position_id,
                    "active_pos": active_pos,
                    "success": True,
                    "group_id": exit_result.get("group_id"),
                    "message": "Position exited successfully"
                })
            else:
                self.logger.error(f"❌ Failed to exit {pair}: {exit_result}")
                failed_exits += 1
                exit_results.append({
                    "pair": pair,
                    "position_id": position_id,
                    "active_pos": active_pos,
                    "success": False,
                    "error": exit_result.get("error", "Unknown error")
                })
            
            # Small delay between exits to avoid rate limiting
            time.sleep(0.5)
        
        total_positions = len(active_positions)
        self.logger.info(f"📋 Exit Summary: {successful_exits}/{total_positions} positions closed successfully")
        
        return {
            "success": True,
            "message": f"Processed {total_positions} positions: {successful_exits} successful, {failed_exits} failed",
            "positions_count": total_positions,
            "successful_exits": successful_exits,
            "failed_exits": failed_exits,
            "results": exit_results
        }

if __name__ == "__main__":
    # Test the trading client
    trading_client = CoinDCXTrading()
    
    # Test balance retrieval
    print("Testing account balance...")
    balance = trading_client.get_account_balance()
    print(f"Balance result: {balance}")
    
    # Test order creation (commented out for safety)
    # print("\nTesting order creation...")
    # test_order = trading_client.create_futures_order(
    #     symbol="B-BTC_USDT",
    #     side="buy", 
    #     quantity=0.001,
    #     take_profit=65000.0,
    #     stop_loss=60000.0
    # )
    # print(f"Order result: {test_order}")