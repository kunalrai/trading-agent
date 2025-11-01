#!/usr/bin/env python3
"""
Trading Alert System
Sends alerts when trading signals are detected
"""

import smtplib
import json
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ema9_api import EMA9API


class AlertSystem:
    """Alert system for trading signals"""
    
    def __init__(self):
        self.api = EMA9API()
        self.last_signal = None
        self.alert_log = []
    
    def log_alert(self, message, alert_type="INFO"):
        """Log alert to file and memory"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {alert_type}: {message}"
        
        # Add to memory
        self.alert_log.append({
            'timestamp': timestamp,
            'type': alert_type,
            'message': message
        })
        
        # Keep only last 100 alerts
        if len(self.alert_log) > 100:
            self.alert_log.pop(0)
        
        # Log to file
        with open('alerts.log', 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        print(log_entry)
    
    def send_desktop_notification(self, title, message):
        """Send desktop notification (Windows)"""
        try:
            import plyer
            plyer.notification.notify(
                title=title,
                message=message,
                app_name='Trading Monitor',
                timeout=10
            )
        except ImportError:
            # Fallback to Windows toast notification
            try:
                import os
                os.system(f'msg * "{title}: {message}"')
            except:
                pass
    
    def send_email_alert(self, subject, body, to_email, smtp_server=None, smtp_user=None, smtp_pass=None):
        """Send email alert (configure SMTP settings)"""
        try:
            if not all([smtp_server, smtp_user, smtp_pass, to_email]):
                self.log_alert("Email settings not configured", "WARNING")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, 587)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            server.sendmail(smtp_user, to_email, text)
            server.quit()
            
            self.log_alert(f"Email sent to {to_email}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log_alert(f"Email failed: {str(e)}", "ERROR")
            return False
    
    def check_and_alert(self, enable_desktop=True, enable_email=False, email_config=None):
        """Check for signals and send alerts"""
        try:
            signal = self.api.get_trading_signal()
            
            if 'error' in signal:
                self.log_alert(f"API Error: {signal['error']}", "ERROR")
                return None
            
            direction = signal.get('signal_direction', 'HOLD')
            confidence = signal.get('confidence', 0)
            price = signal.get('current_price', 0)
            
            # Check if signal changed to LONG or SHORT
            if direction != 'HOLD' and direction != self.last_signal:
                
                # Create alert message
                emoji = "📈" if direction == "LONG" else "📉"
                title = f"{emoji} {direction} SIGNAL - SOL/USDT"
                
                message = f"""
{direction} Signal Detected!
Price: ${price}
Confidence: {confidence}%
RSI(7): {signal.get('current_rsi7', 0):.1f}
Entry: ${signal.get('entry_price', 0)}
Stop Loss: ${signal.get('stop_loss', 0)}
Take Profit 1: ${signal.get('take_profit_1', 0)}
"""
                
                # Log the alert
                self.log_alert(f"{direction} signal detected - Price: ${price}, Confidence: {confidence}%", "SIGNAL")
                
                # Send desktop notification
                if enable_desktop:
                    self.send_desktop_notification(title, message.strip())
                
                # Send email alert
                if enable_email and email_config:
                    email_body = f"""
Trading Signal Alert - SOL/USDT

Signal: {direction}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Market Data:
- Current Price: ${price}
- RSI(7): {signal.get('current_rsi7', 0):.1f}
- RSI(14): {signal.get('current_rsi14', 0):.1f}
- MACD: {signal.get('current_macd', 0):.3f}

Trade Setup:
- Entry Price: ${signal.get('entry_price', 0)}
- Stop Loss: ${signal.get('stop_loss', 0)}
- Take Profit 1: ${signal.get('take_profit_1', 0)}
- Take Profit 2: ${signal.get('take_profit_2', 0)}
- Take Profit 3: ${signal.get('take_profit_3', 0)}

Position Management:
- Position Size: {signal.get('position_size_pct', 0)}% of capital
- Risk Amount: ${signal.get('risk_amount', 0)}
- Confidence: {confidence}%

Signal Factors:
""" + "\n".join(f"- {factor}" for factor in signal.get('signal_factors', []))
                    
                    self.send_email_alert(
                        subject=title,
                        body=email_body,
                        to_email=email_config.get('to_email'),
                        smtp_server=email_config.get('smtp_server'),
                        smtp_user=email_config.get('smtp_user'),
                        smtp_pass=email_config.get('smtp_pass')
                    )
                
                self.last_signal = direction
                return signal
            
            # Log regular status
            elif direction == 'HOLD':
                self.log_alert(f"Status check - HOLD - Price: ${price}, RSI(7): {signal.get('current_rsi7', 0):.1f}")
            
            self.last_signal = direction
            return signal
            
        except Exception as e:
            self.log_alert(f"Alert check failed: {str(e)}", "ERROR")
            return None
    
    def run_monitoring(self, check_interval_minutes=15, enable_desktop=True, enable_email=False, email_config=None):
        """Run continuous monitoring with alerts"""
        
        self.log_alert("Starting alert monitoring system", "INFO")
        self.log_alert(f"Check interval: {check_interval_minutes} minutes", "INFO")
        self.log_alert(f"Desktop alerts: {'Enabled' if enable_desktop else 'Disabled'}", "INFO")
        self.log_alert(f"Email alerts: {'Enabled' if enable_email else 'Disabled'}", "INFO")
        
        try:
            while True:
                self.check_and_alert(enable_desktop, enable_email, email_config)
                time.sleep(check_interval_minutes * 60)
                
        except KeyboardInterrupt:
            self.log_alert("Alert monitoring stopped by user", "INFO")
        except Exception as e:
            self.log_alert(f"Alert monitoring crashed: {str(e)}", "ERROR")


def main():
    """Main function for alert system"""
    import sys
    
    # Email configuration (optional)
    email_config = {
        'to_email': 'your-email@gmail.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_user': 'your-email@gmail.com',
        'smtp_pass': 'your-app-password'  # Use app password for Gmail
    }
    
    alert_system = AlertSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'once':
            # Single check
            print("🔍 Single Alert Check")
            print("=" * 30)
            alert_system.check_and_alert(enable_desktop=True, enable_email=False)
            
        elif command == 'desktop':
            # Desktop notifications only
            print("🔔 Starting desktop alert monitoring...")
            alert_system.run_monitoring(check_interval_minutes=15, enable_desktop=True, enable_email=False)
            
        elif command == 'email':
            # Email notifications (configure email_config above)
            print("📧 Starting email alert monitoring...")
            alert_system.run_monitoring(check_interval_minutes=15, enable_desktop=False, enable_email=True, email_config=email_config)
            
        elif command == 'all':
            # Both desktop and email
            print("🔔📧 Starting full alert monitoring...")
            alert_system.run_monitoring(check_interval_minutes=15, enable_desktop=True, enable_email=True, email_config=email_config)
            
        else:
            print("Usage:")
            print("  python alerts.py           - Desktop alerts only (default)")
            print("  python alerts.py once      - Single check")
            print("  python alerts.py desktop   - Desktop notifications")
            print("  python alerts.py email     - Email notifications")
            print("  python alerts.py all       - Both desktop and email")
    else:
        # Default: desktop alerts only
        print("🔔 Starting desktop alert monitoring...")
        print("Configure email settings in the script for email alerts")
        alert_system.run_monitoring(check_interval_minutes=15, enable_desktop=True, enable_email=False)


if __name__ == "__main__":
    main()