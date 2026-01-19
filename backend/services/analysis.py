import pandas as pd
import pandas_ta as ta

def calculate_mas(df: pd.DataFrame, periods: list[int], ma_type: str = 'EMA') -> pd.DataFrame:
    """
    Calculates MAs (EMA or SMA) for the given periods and appends them to the DataFrame.
    """
    df = df.copy()
    # Ensure 'Close' column exists
    if 'Close' not in df.columns:
        cols = [c.lower() for c in df.columns]
        if 'close' in cols:
             df.rename(columns={df.columns[cols.index('close')]: 'Close'}, inplace=True)
        else:
            raise ValueError("DataFrame missing 'Close' column")

    for period in periods:
        col_name = f'{ma_type}_{period}'
        try:
            if ma_type == 'EMA':
                df[col_name] = ta.ema(df['Close'], length=period)
            else: # SMA
                df[col_name] = ta.sma(df['Close'], length=period)
        except Exception:
            # Fallback
            if ma_type == 'EMA':
                df[col_name] = df['Close'].ewm(span=period, adjust=False).mean()
            else:
                df[col_name] = df['Close'].rolling(window=period).mean()
             
    return df

def find_crossovers(df: pd.DataFrame, short_period: int, long_period: int, wait_days: int = 0, ma_type: str = 'EMA'):
    """
    Identifies crossover signals between a short and long MA.
    Returns a DataFrame with 'Signal' column: 1 (Buy), -1 (Sell), 0 (Hold).
    If wait_days > 0, requires the crossover condition to persist for wait_days.
    """
    short_col = f'{ma_type}_{short_period}'
    long_col = f'{ma_type}_{long_period}'
    
    if short_col not in df.columns or long_col not in df.columns:
        raise ValueError(f"MA columns {short_col} or {long_col} not found")

    signals = pd.DataFrame(index=df.index)
    signals['Signal'] = 0.0
    
    # Create a boolean series where short > long
    raw_condition = (df[short_col] > df[long_col]).astype(int)
    
    if wait_days > 0:
        confirmed_condition = raw_condition.rolling(window=wait_days + 1).min()
    else:
        confirmed_condition = raw_condition
    
    signals['Signal'] = confirmed_condition.diff().fillna(0)
    
    return signals

def backtest_strategy(df: pd.DataFrame, signals: pd.DataFrame):
    # ... (No changes logic-wise, but including for complete block replacement if needed? No, logic is generic)
    # Using existing backtest_strategy is fine.
    
    # Re-pasting backtest_strategy to ensure no context issues with tool
    position = 0 # 0: None, 1: Held
    entry_price = 0.0
    total_gain_pct = 0.0
    trades = []

    combined = pd.concat([df['Close'], signals['Signal']], axis=1)
    
    for row in combined.itertuples():
        price = row.Close
        signal = row.Signal
        
        if signal == 1 and position == 0:
            entry_price = price
            position = 1
            trades.append({'type': 'buy', 'price': price, 'date': row.Index})
            
        elif signal == -1 and position == 1:
            exit_price = price
            gain_pct = ((exit_price - entry_price) / entry_price) * 100
            total_gain_pct += gain_pct
            position = 0
            trades.append({'type': 'sell', 'price': price, 'date': row.Index, 'gain_pct': gain_pct})
            
    if position == 1:
        current_price = combined.iloc[-1]['Close']
        gain_pct = ((current_price - entry_price) / entry_price) * 100
        total_gain_pct += gain_pct
        trades.append({'type': 'hold', 'current_price': current_price, 'unrealized_gain_pct': gain_pct})
        
    return total_gain_pct, trades

def optimize_pairs(df: pd.DataFrame, periods: list[int], wait_days: int = 0, ma_type: str = 'EMA'):
    """
    Finds the pair of MA periods that maximizes gain.
    """
    best_gain = -float('inf')
    best_pair = (0, 0)
    best_trades_count = 0
    results = []

    # Calculate all MAs once
    df_mas = calculate_mas(df, periods, ma_type)
    
    import itertools
    for short_p, long_p in itertools.combinations(sorted(periods), 2):
        signals = find_crossovers(df_mas, short_p, long_p, wait_days=wait_days, ma_type=ma_type)
        gain, trades = backtest_strategy(df_mas, signals)
        
        results.append({
            'pair': f"{short_p}/{long_p}",
            'gain': gain,
            'trades': len(trades)
        })
        
        if gain > best_gain:
            best_gain = gain
            best_pair = (short_p, long_p)
            best_trades_count = len(trades)

    # Calculate Buy & Hold Return
    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    buy_hold_return = ((end_price - start_price) / start_price) * 100
            
    return best_pair, best_gain, best_trades_count, buy_hold_return, results, df_mas
