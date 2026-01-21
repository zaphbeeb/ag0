import json
import os
import uuid
import threading
import time
import pandas as pd
from datetime import datetime
import yfinance as yf
from .analysis import calculate_mas, find_crossovers

# Determine alerts file path
# If STORAGE_PATH or STORAGE_DIR is set, use it. Otherwise default to project root.
storage_dir = os.environ.get('STORAGE_PATH') or os.environ.get('STORAGE_DIR')
if storage_dir:
    # Ensure directory exists
    os.makedirs(storage_dir, exist_ok=True)
    ALERTS_FILE = os.path.join(storage_dir, 'alerts.json')
else:
    # Default to project root
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

    def add_alert(self, ticker, short_p, long_p, ma_type='EMA', initial_data=None):
        alert = {
            'id': str(uuid.uuid4()),
            'ticker': str(ticker).upper(),
            'short_p': int(short_p),
            'long_p': int(long_p),
            'ma_type': str(ma_type),
            'created_at': datetime.now().isoformat(),
            'last_triggered': None,
            'last_check_data': {
                'short_val': None,
                'long_val': None,
                'trend': 'N/A'
            },
            'last_crossover': None
        }
        
        if initial_data:
            # Populate from provided data
            if 'check_data' in initial_data:
                alert['last_check_data'] = initial_data['check_data']
            if 'crossover' in initial_data:
                alert['last_crossover'] = initial_data['crossover']
        else:
            # Initial check to populate data
            self._check_single_alert(alert)
        
        with self._lock:
            self.alerts.append(alert)
        self.save_alerts()
        return alert

    def delete_alert(self, alert_id):
        with self._lock:
            self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        self.save_alerts()

    def _check_single_alert(self, alert):
        try:
            ticker = alert['ticker']
            df = yf.download(ticker, period="1y", progress=False)
            
            if df.empty:
                return None
            
            periods = [alert['short_p'], alert['long_p']]
            df_mas = calculate_mas(df, periods, alert['ma_type'])
            
            # Extract last 2 rows for trend calculation
            if len(df_mas) >= 2:
                # Get series
                s_col = f"{alert['ma_type']}_{alert['short_p']}"
                l_col = f"{alert['ma_type']}_{alert['long_p']}"
                
                # Last values
                curr_s = df_mas[s_col].iloc[-1]
                curr_l = df_mas[l_col].iloc[-1]
                prev_s = df_mas[s_col].iloc[-2]
                prev_l = df_mas[l_col].iloc[-2]
                
                # Trend
                curr_diff = abs(curr_s - curr_l)
                prev_diff = abs(prev_s - prev_l)
                
                trend = "Converging" if curr_diff < prev_diff else "Diverging"
                
                # Update alert data
                alert['last_check_data'] = {
                    'short_val': round(curr_s, 2),
                    'long_val': round(curr_l, 2),
                    'trend': trend
                }
            
            # Crossover logic
            signals = find_crossovers(df_mas, alert['short_p'], alert['long_p'], wait_days=0, ma_type=alert['ma_type'])
            
            # Find latest historical crossover (Last Crossover column)
            non_zero_signals = signals[signals['Signal'] != 0]
            if not non_zero_signals.empty:
                last_occ = non_zero_signals.iloc[-1]
                alert['last_crossover'] = {
                    'signal': int(last_occ['Signal']),
                    'date': last_occ.name.strftime('%Y-%m-%d')
                }
            
            # Notification trigger (only if it happened just now/today)
            last_signal = signals.iloc[-1]['Signal']
            
            if last_signal != 0:
                alert['last_triggered'] = datetime.now().isoformat()
                return {
                    'ticker': ticker,
                    'type': 'Buy' if last_signal == 1 else 'Sell',
                    'symbol': '📈' if last_signal == 1 else '📉',
                    'price': df['Close'].iloc[-1]
                }
                
        except Exception as e:
            print(f"Error checking alert {alert['id']}: {e}")
        return None

    def check_alerts(self):
        """
        New Logic: Check alerts.
        This function should be called daily.
        """
        triggered = []
        # Create a copy to iterate safely? No need if not modifying list structure.
        # But we modify alert dicts in place.
        
        # Thread safety? self.alerts might change.
        # Iterate over a copy of list
        with self._lock:
            alerts_copy = list(self.alerts)
            
        for alert in alerts_copy:
            result = self._check_single_alert(alert)
            if result:
                triggered.append(result)
        
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
