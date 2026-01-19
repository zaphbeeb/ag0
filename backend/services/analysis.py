import pandas as pd
import pandas_ta as ta

def calculate_emas(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """
    Calculates EMAs for the given periods and appends them to the DataFrame.
    """
    df = df.copy()
    # Ensure 'Close' column exists and handle potential MultiIndex issues
    if 'Close' not in df.columns:
         # If purely single level index but case mismatch
        cols = [c.lower() for c in df.columns]
        if 'close' in cols:
             df.rename(columns={df.columns[cols.index('close')]: 'Close'}, inplace=True)
        else:
            raise ValueError("DataFrame missing 'Close' column")

    for period in periods:
        # panda_ta or standard pandas ewm can be used. using pandas ewm for simplicity and speed if pandas_ta has overhead, 
        # but pandas_ta is requested, so we use it. A fallback to pure pandas is good if ta fails.
        try:
            df[f'EMA_{period}'] = ta.ema(df['Close'], length=period)
        except Exception:
             df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
             
    return df

def find_crossovers(df: pd.DataFrame, short_period: int, long_period: int):
    """
    Identifies crossover signals between a short and long EMA.
    Returns a DataFrame with 'Signal' column: 1 (Buy), -1 (Sell), 0 (Hold).
    """
    short_col = f'EMA_{short_period}'
    long_col = f'EMA_{long_period}'
    
    if short_col not in df.columns or long_col not in df.columns:
        raise ValueError(f"EMA columns {short_col} or {long_col} not found")

    signals = pd.DataFrame(index=df.index)
    signals['Signal'] = 0.0
    
    # Create a boolean series where short > long
    signals['Long_Signal'] = df[short_col] > df[long_col]
    
    # Take the difference to find where the crossover happened
    # diff will be True (1) when False -> True (Buy), and False (-1) when True -> False (Sell)
    # dependent on casting bool to int: True=1, False=0. 
    # int(True) - int(False) = 1 (Buy)
    # int(False) - int(True) = -1 (Sell)
    signals['Signal'] = signals['Long_Signal'].astype(int).diff()
    
    return signals

def backtest_strategy(df: pd.DataFrame, signals: pd.DataFrame):
    """
    Calculates potential gain/loss based on signals.
    Assumes buying on 1 and selling on -1.
    """
    position = 0 # 0: None, 1: Held
    entry_price = 0.0
    total_gain_pct = 0.0
    trades = []

    # Iterate through signals
    # Using itertuples for speed
    combined = pd.concat([df['Close'], signals['Signal']], axis=1)
    
    for row in combined.itertuples():
        price = row.Close
        signal = row.Signal
        
        if signal == 1 and position == 0:
            # Buy
            entry_price = price
            position = 1
            trades.append({'type': 'buy', 'price': price, 'date': row.Index})
            
        elif signal == -1 and position == 1:
            # Sell
            exit_price = price
            gain_pct = ((exit_price - entry_price) / entry_price) * 100
            total_gain_pct += gain_pct
            position = 0
            trades.append({'type': 'sell', 'price': price, 'date': row.Index, 'gain_pct': gain_pct})
            
    # If still holding at the end, calculate unrealized gain
    if position == 1:
        current_price = combined.iloc[-1]['Close']
        gain_pct = ((current_price - entry_price) / entry_price) * 100
        total_gain_pct += gain_pct
        trades.append({'type': 'hold', 'current_price': current_price, 'unrealized_gain_pct': gain_pct})
        
    return total_gain_pct, trades

def optimize_pairs(df: pd.DataFrame, periods: list[int]):
    """
    Finds the pair of MA periods that maximizes gain.
    """
    best_gain = -float('inf')
    best_pair = (0, 0)
    results = []

    # Calculate all EMAs once
    df_emas = calculate_emas(df, periods)
    
    import itertools
    for short_p, long_p in itertools.combinations(sorted(periods), 2):
        signals = find_crossovers(df_emas, short_p, long_p)
        gain, _ = backtest_strategy(df_emas, signals)
        
        results.append({
            'pair': f"{short_p}/{long_p}",
            'gain': gain
        })
        
        if gain > best_gain:
            best_gain = gain
            best_pair = (short_p, long_p)
            
    return best_pair, best_gain, results, df_emas
