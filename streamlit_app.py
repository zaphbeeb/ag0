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
with st.sidebar:
    st.header("Configuration")
    
    # Tickers input
    tickers_input = st.text_input(
        "Stock Tickers (comma separated)",
        value="AAPL",
        help="Enter stock ticker symbols separated by commas"
    )
    
    # MA Periods
    st.subheader("Moving Average Periods")
    periods = []
    cols = st.columns(4)
    period_options = [5, 10, 20, 25, 50, 100, 150, 200]
    for idx, period in enumerate(period_options):
        with cols[idx % 4]:
            if st.checkbox(str(period), value=True, key=f"period_{period}"):
                periods.append(period)
    
    # Date range
    st.subheader("Date Range")
    start_date = st.date_input(
        "Start Date",
        value=datetime(2022, 1, 1)
    )
    end_date = st.date_input(
        "End Date",
        value=datetime(2025, 1, 1)
    )
    
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
                        best_pair, best_gain, opt_results, df_emas = optimize_pairs(df, periods)
                        
                        # Display metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Best MA Pair", f"{best_pair[0]} / {best_pair[1]}")
                        with col2:
                            st.metric("Max Potential Gain", f"{best_gain:.2f}%", 
                                     delta=f"{best_gain:.2f}%")
                        with col3:
                            st.metric("Data Points", len(df_emas))
                        
                        # Create chart
                        fig = go.Figure()
                        
                        # Add price line
                        fig.add_trace(go.Scatter(
                            x=df_emas.index,
                            y=df_emas['Close'],
                            name='Price',
                            line=dict(color='#9ca3af', width=1)
                        ))
                        
                        # Add EMA lines for best pair
                        short_p, long_p = best_pair
                        fig.add_trace(go.Scatter(
                            x=df_emas.index,
                            y=df_emas[f'EMA_{short_p}'],
                            name=f'EMA {short_p}',
                            line=dict(color='#3b82f6', width=2)
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=df_emas.index,
                            y=df_emas[f'EMA_{long_p}'],
                            name=f'EMA {long_p}',
                            line=dict(color='#a855f7', width=2)
                        ))
                        
                        # Update layout
                        fig.update_layout(
                            title=f"{ticker} - Price with Best EMA Pair",
                            xaxis_title="Date",
                            yaxis_title="Price ($)",
                            template="plotly_dark",
                            hovermode='x unified',
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show optimization results
                        with st.expander("📋 View All Combinations"):
                            results_df = pd.DataFrame(opt_results)
                            results_df = results_df.sort_values('gain', ascending=False)
                            results_df['gain'] = results_df['gain'].apply(lambda x: f"{x:.2f}%")
                            st.dataframe(results_df, use_container_width=True)
                        
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
