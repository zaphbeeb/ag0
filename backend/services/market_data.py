import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def fetch_historical_data(tickers: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
    """
    Fetches historical stock data for a list of tickers.
    
    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'GOOG']).
        start_date: Start date in 'YYYY-MM-DD' format.
        end_date: End date in 'YYYY-MM-DD' format.
        
    Returns:
        A dictionary where keys are tickers and values are DataFrames containing historical data.
    """
    data = {}
    for ticker in tickers:
        try:
            # yfinance expects dates in YYYY-MM-DD
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if not df.empty:
                # Ensure we strictly have the data we need and handle multi-level columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df = df.xs(ticker, level=1, axis=1)
                data[ticker] = df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            
    return data
