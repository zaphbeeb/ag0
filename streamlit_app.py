import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
sys.path.append('backend')
from services.market_data import fetch_historical_data
from services.analysis import optimize_pairs

# Page config
st.set_page_config(
    page_title="Momentum Signal Trading App",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    /* Scale down the entire UI by 20% */
    .stApp {
        zoom: 0.80;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #2563eb 0%, #4f46e5 100%);
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border: none;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #1d4ed8 0%, #4338ca 100%);
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📈 Momentum Signal Trading App")
st.markdown("Identify trading momentum signals based on Exponential Moving Average (EMA) crossovers.")

# Sidebar inputs
# Configuration expander
with st.expander("Configuration", expanded=True):
    # Tickers input
    tickers_input = st.text_input(
        "Stock Tickers (comma separated)",
        value="AAPL",
        help="Enter stock ticker symbols separated by commas"
    )
    
    # MA Periods
    st.subheader("Moving Average Periods")
    periods = []
    cols = st.columns(8) # Use more columns for horizontal layout
    period_options = [5, 10, 20, 25, 50, 100, 150, 200]
    for idx, period in enumerate(period_options):
        with cols[idx]:
            if st.checkbox(str(period), value=True, key=f"period_{period}"):
                periods.append(period)
    
    # Settings row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime(2024, 1, 1)
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime(2026, 1, 1)
        )
        
    with col3:
        wait_days = st.number_input("Crossing Wait (days)", min_value=0, value=0, help="Wait N days to confirm crossover signal")
    
    # MA Type
    ma_type = st.radio("Moving Average Type", ["EMA", "SMA"], horizontal=True)

    # Run button
    run_analysis = st.button("🚀 Run Analysis", type="primary")

# Main content
if run_analysis:
    if not periods:
        st.error("Please select at least one moving average period.")
    elif len(periods) < 2:
        st.error("Please select at least two moving average periods for crossover analysis.")
    else:
        # Parse tickers
        ticker_list = [t.strip().upper() for t in tickers_input.split(',')]
        
        with st.spinner("Fetching data and analyzing..."):
            try:
                # Fetch data
                data_map = fetch_historical_data(
                    ticker_list,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not data_map:
                    st.error("No data retrieved. Please check your ticker symbols and date range.")
                else:
                    # Process each ticker
                    for ticker, df in data_map.items():
                        if df.empty:
                            st.warning(f"No data available for {ticker}")
                            continue
                        
                        st.header(f"📊 {ticker}")
                        
                        # Optimize pairs
                        best_pair, best_gain, best_trades_count, buy_hold_return, opt_results, df_mas = optimize_pairs(df, periods, wait_days=wait_days, ma_type=ma_type)
                        
                        # Display metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(f"Best {ma_type} Pair", f"{best_pair[0]} / {best_pair[1]}")
                        with col2:
                            st.metric("Max Potential Gain", f"{best_gain:.2f}%", 
                                     delta=f"{best_gain:.2f}%")
                        with col3:
                            st.metric("Buy & Hold", f"{buy_hold_return:.2f}%",
                                     delta=f"{buy_hold_return:.2f}%")
                        with col4:
                            st.metric("Transactions", best_trades_count)
                        
                        # Create chart
                        fig = go.Figure()
                        
                        # Add price line
                        fig.add_trace(go.Scatter(
                            x=df_mas.index,
                            y=df_mas['Close'],
                            name='Price',
                            line=dict(color='#9ca3af', width=1)
                        ))
                        
                        # Add MA lines for best pair
                        short_p, long_p = best_pair
                        fig.add_trace(go.Scatter(
                            x=df_mas.index,
                            y=df_mas[f'{ma_type}_{short_p}'],
                            name=f'{ma_type} {short_p}',
                            line=dict(color='#3b82f6', width=2)
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=df_mas.index,
                            y=df_mas[f'{ma_type}_{long_p}'],
                            name=f'{ma_type} {long_p}',
                            line=dict(color='#a855f7', width=2)
                        ))

                        # Calculate signals for visualization
                        short_col = f'{ma_type}_{short_p}'
                        long_col = f'{ma_type}_{long_p}'
                        
                        # Create signal series with wait logic
                        raw_crossover = (df_mas[short_col] > df_mas[long_col]).astype(int)
                        
                        if wait_days > 0:
                            confirmed_crossover = raw_crossover.rolling(window=wait_days + 1).min()
                        else:
                            confirmed_crossover = raw_crossover
                            
                        # Diff: 1 = Buy (0->1), -1 = Sell (1->0)
                        signals = confirmed_crossover.diff().fillna(0)
                        
                        buy_signals = df_emas[signals == 1]
                        sell_signals = df_emas[signals == -1]
                        
                        # Add Buy Signals
                        fig.add_trace(go.Scatter(
                            x=buy_signals.index,
                            y=buy_signals['Close'],
                            mode='markers',
                            name='Buy Signal',
                            marker=dict(symbol='triangle-up', size=12, color='#22c55e', line=dict(width=1, color='darkgreen'))
                        ))

                        # Add Sell Signals
                        fig.add_trace(go.Scatter(
                            x=sell_signals.index,
                            y=sell_signals['Close'],
                            mode='markers',
                            name='Sell Signal',
                            marker=dict(symbol='triangle-down', size=12, color='#ef4444', line=dict(width=1, color='darkred'))
                        ))
                        
                        # Update layout
                        fig.update_layout(
                            title=f"{ticker} - Price with Best EMA Pair",
                            xaxis_title="Date",
                            yaxis_title="Price ($)",
                            template="plotly_dark",
                            hovermode='x unified',
                            height=500,
                            margin=dict(l=10, r=10, t=50, b=10)
                        )
                        
                        st.plotly_chart(fig)
                        
                        # Show optimization results
                        with st.expander("📋 View All Combinations"):
                            results_df = pd.DataFrame(opt_results)
                            results_df = results_df.sort_values('gain', ascending=False)
                            results_df['gain'] = results_df['gain'].apply(lambda x: f"{x:.2f}%")
                            results_df = results_df.rename(columns={"pair": "EMA Pair", "gain": "Gain", "trades": "Transactions"})
                            st.dataframe(results_df, hide_index=True)
                        
                        st.divider()
                        
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)
else:
    # Welcome message
    st.info("👈 Configure your analysis parameters in the sidebar and click 'Run Analysis' to begin.")
    
    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. **Enter Stock Tickers**: Add one or more ticker symbols (e.g., AAPL, MSFT, GOOGL)
        2. **Select MA Periods**: Choose which moving average periods to analyze
        3. **Set Date Range**: Define the backtesting period
        4. **Run Analysis**: Click the button to calculate optimal EMA pairs
        
        The app will:
        - Calculate EMAs for all selected periods
        - Identify crossover signals (buy/sell)
        - Backtest each pair combination
        - Show the pair with maximum potential gain
        - Display interactive charts with the best EMA pair
        """)
