import json
import os
import uuid
import threading
import time
import pandas as pd
from datetime import datetime
import yfinance as yf
from .analysis import calculate_mas, find_crossovers

ALERTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'alerts.json')

class AlertService:
    def __init__(self):
        self._lock = threading.Lock()
        self.alerts = self.load_alerts()
        self._scheduler_thread = None
        self._stop_event = threading.Event()

    def load_alerts(self):
        if not os.path.exists(ALERTS_FILE):
            print(f"Alerts file not found at {ALERTS_FILE}, creating new.")
            return []
        try:
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
                print(f"Loaded {len(alerts)} alerts from {ALERTS_FILE}")
                return alerts
        except Exception as e:
            print(f"Error loading alerts: {e}")
            return []

    def save_alerts(self):
        with self._lock:
            with open(ALERTS_FILE, 'w') as f:
                json.dump(self.alerts, f, indent=4)

    def add_alert(self, ticker, short_p, long_p, ma_type='EMA'):
        alert = {
            'id': str(uuid.uuid4()),
            'ticker': str(ticker).upper(),
            'short_p': int(short_p),
            'long_p': int(long_p),
            'ma_type': str(ma_type),
            'created_at': datetime.now().isoformat(),
            'last_triggered': None
        }
        with self._lock:
            self.alerts.append(alert)
        self.save_alerts()
        return alert

    def delete_alert(self, alert_id):
        with self._lock:
            self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        self.save_alerts()

    def check_alerts(self):
        """
        New Logic: Check alerts.
        This function should be called daily.
        """
        triggered = []
        for alert in self.alerts:
            try:
                # Fetch recent data (enough for long_p)
                # Need at least long_p + some buffer. 300 days is safe.
                ticker = alert['ticker']
                df = yf.download(ticker, period="1y", progress=False)
                
                if df.empty:
                    continue
                
                periods = [alert['short_p'], alert['long_p']]
                df_mas = calculate_mas(df, periods, alert['ma_type'])
                
                # Check crossover for ONLY the last day? 
                # Or wait logic?
                # User asked for "notification if a crossover is detected"
                # We check the most recent crossover.
                
                signals = find_crossovers(df_mas, alert['short_p'], alert['long_p'], wait_days=0, ma_type=alert['ma_type'])
                
                # Get last signal
                last_signal = signals.iloc[-1]['Signal']
                
                if last_signal != 0:
                    alert['last_triggered'] = datetime.now().isoformat()
                    triggered.append({
                        'ticker': ticker,
                        'type': 'Buy' if last_signal == 1 else 'Sell',
                        'symbol': '📈' if last_signal == 1 else '📉',
                        'price': df['Close'].iloc[-1]
                    })
                    
            except Exception as e:
                print(f"Error checking alert {alert['id']}: {e}")
        
        self.save_alerts()
        return triggered

    def start_background_scheduler(self):
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        def run_loop():
            while not self._stop_event.is_set():
                now = datetime.now()
                # Run daily check at midnight (or just run once every 24h? or check every hour if midnight passed?)
                # For simplicity in this demo, we might just check periodically or if the user requests.
                # User request: "calculates ... daily at midnight"
                
                # Logic: Check if hour is 0 and we haven't checked today?
                # Implementation: Check every minute.
                if now.hour == 0 and now.minute == 0:
                    self.check_alerts()
                    time.sleep(61) # Sleep > 1 minute to avoid double run
                
                time.sleep(30)

        self._scheduler_thread = threading.Thread(target=run_loop, daemon=True)
        self._scheduler_thread.start()
