from services.market_data import fetch_historical_data
from services.analysis import optimize_pairs

def test_backend():
    tickers = ['AAPL']
    periods = [5, 10, 20]
    start = '2023-01-01'
    end = '2023-06-01'
    
    print("Fetching data...")
    data = fetch_historical_data(tickers, start, end)
    
    if 'AAPL' not in data:
        print("Failed to fetch AAPL data")
        return

    df = data['AAPL']
    print(f"Fetched {len(df)} rows for AAPL")
    
    print("Optimizing pairs...")
    best_pair, best_gain, results, _ = optimize_pairs(df, periods)
    
    print(f"Best Pair: {best_pair}")
    print(f"Best Gain: {best_gain}%")
    print("Results:", results)

if __name__ == "__main__":
    test_backend()
