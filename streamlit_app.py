import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
sys.path.append('backend')
from services.market_data import fetch_historical_data
from services.analysis import optimize_pairs
from services.alert_service import AlertService

@st.cache_resource
def get_alert_service():
    service = AlertService()
    service.start_background_scheduler()
    return service

alert_service = get_alert_service()

# Check for notifications
if alert_service.alerts:
    for alert in alert_service.alerts:
        trigger_time = alert.get('last_triggered')
        if trigger_time:
            try:
                t_date = datetime.fromisoformat(trigger_time).date()
                if t_date == datetime.now().date():
                    st.toast(f"🔔 Signal triggered for {alert['ticker']} ({alert['ma_type']} {alert['short_p']}/{alert['long_p']})", icon="⚠️")
            except ValueError:
                pass

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

# Main Layout
tab_analysis, tab_alerts = st.tabs(["Analysis", "Managed Alerts"])

with tab_analysis:
    # Sidebar inputs moved here as per new layout request
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
        def enable_run():
            st.session_state.analysis_run = True
            
        run_analysis = st.button("🚀 Run Analysis", type="primary", on_click=enable_run)

    # Analysis Results
    if st.session_state.get('analysis_run', False):
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
                            
                            # Optimize pairs
                            best_pair, best_gain, best_trades_count, buy_hold_return, opt_results, df_mas = optimize_pairs(df, periods, wait_days=wait_days, ma_type=ma_type)
                            
                            # Header with Quick Add Button
                            h_c1, h_c2 = st.columns([3, 1])
                            with h_c1:
                                st.header(f"📊 {ticker}")
                            with h_c2:
                                # Use a unique key for each ticker
                                if st.button("🔔 Track Best Pair", key=f"track_{ticker}", help=f"Add alert for {ticker} {ma_type} {best_pair[0]}/{best_pair[1]}"):
                                    # Check for duplicates
                                    exists = any(a['ticker'] == ticker and a['short_p'] == best_pair[0] and a['long_p'] == best_pair[1] and a['ma_type'] == ma_type for a in alert_service.alerts)
                                    
                                    if not exists:
                                        # Compute initial data from df_mas to avoid re-fetch
                                        s_col = f"{ma_type}_{best_pair[0]}"
                                        l_col = f"{ma_type}_{best_pair[1]}"
                                        
                                        # Values
                                        curr_s = df_mas[s_col].iloc[-1]
                                        curr_l = df_mas[l_col].iloc[-1]
                                        
                                        # Trend and Est Crossover Days
                                        trend = "N/A"
                                        est_crossover_days = None
                                        if len(df_mas) >= 2:
                                            prev_s = df_mas[s_col].iloc[-2]
                                            prev_l = df_mas[l_col].iloc[-2]
                                            curr_diff = abs(curr_s - curr_l)
                                            prev_diff = abs(prev_s - prev_l)
                                            trend = "Converging" if curr_diff < prev_diff else "Diverging"
                                            
                                            # Calculate Est Crossover Days
                                            if trend == "Converging":
                                                convergence_rate = prev_diff - curr_diff
                                                if convergence_rate > 0:
                                                    est_crossover_days = int(curr_diff / convergence_rate)
                                            
                                        # Last Crossover
                                        crossover_data = None
                                        # Re-use logic: raw crossover
                                        from services.analysis import find_crossovers # Import here or ensure top level
                                        signals = find_crossovers(df_mas, best_pair[0], best_pair[1], wait_days=wait_days, ma_type=ma_type)
                                        non_zero_signals = signals[signals['Signal'] != 0]
                                        if not non_zero_signals.empty:
                                            last_occ = non_zero_signals.iloc[-1]
                                            crossover_data = {
                                                'signal': int(last_occ['Signal']),
                                                'date': last_occ.name.strftime('%Y-%m-%d')
                                            }
                                            
                                        initial_data = {
                                            'check_data': {
                                                'short_val': round(curr_s, 2),
                                                'long_val': round(curr_l, 2),
                                                'trend': trend,
                                                'est_crossover_days': est_crossover_days
                                            },
                                            'crossover': crossover_data
                                        }


                                        alert_service.add_alert(ticker, best_pair[0], best_pair[1], ma_type, initial_data=initial_data)
                                        st.toast(f"Alert added: {ticker} {best_pair[0]}/{best_pair[1]}", icon="✅")
                                    else:
                                        st.toast(f"Alert already exists for {ticker}", icon="ℹ️")
                            
                            # Display metrics
                            # Display metrics
                            symbol = ">" if best_gain > buy_hold_return else "<"
                            col1, col2, col_mid, col3, col4 = st.columns([2.5, 2.5, 0.5, 2.5, 2])
                            
                            with col1:
                                st.metric(f"Best {ma_type} Pair", f"{best_pair[0]} / {best_pair[1]}")
                            with col2:
                                st.metric("Max Potential Gain", f"{best_gain:.2f}%", 
                                         delta=f"{best_gain:.2f}%")
                            with col_mid:
                                st.markdown(f"<div style='display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 25px; font-size: 24px; font-weight: bold;'>{symbol}</div>", unsafe_allow_html=True)
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
                            
                            buy_signals = df_mas[signals == 1]
                            sell_signals = df_mas[signals == -1]
                            
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
                                title=f"{ticker} - Price with Best {ma_type} Pair",
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
                                results_df = results_df.rename(columns={"pair": f"{ma_type} Pair", "gain": "Gain", "trades": "Transactions"})
                                st.dataframe(results_df, hide_index=True)
                            
                            st.divider()
                            
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.exception(e)
    else:
        # Instructions
        with st.expander("ℹ️ How to use"):
            st.markdown("""
            1. **Enter Stock Tickers**: Add one or more ticker symbols (e.g., AAPL, MSFT, GOOGL)
            2. **Select MA Periods**: Choose which moving average periods to analyze
            3. **Set Date Range**: Define the backtesting period
            4. **Run Analysis**: Click the button to calculate optimal MA pairs
            
            The app will:
            - Calculate MAs for all selected periods
            - Identify crossover signals (buy/sell)
            - Backtest each pair combination
            - Show the pair with maximum potential gain
            - Display interactive charts with the best MA pair
            """)

with tab_alerts:
    # Header Row with Reset Button
    c_head, c_btn = st.columns([4,1])
    with c_head:
         st.header("🔔 Managed Alerts")
         st.markdown("Add alerts to be checked daily regarding moving average crossovers.")
    with c_btn:
         if st.button("🔄 Run Updates Now"):
             with st.spinner("Checking all alerts..."):
                 alert_service.check_alerts()
             st.success("Alerts updated!")
             st.rerun()

    # Add Alert Form
    with st.expander("➕ Add New Alert", expanded=True):
        with st.form("add_alert_form"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                t_ticker = st.text_input("Ticker Symbol").upper()
            with col2:
                t_short = st.number_input("Short Period", min_value=1, value=10)
            with col3:
                t_long = st.number_input("Long Period", min_value=1, value=50)
            with col4:
                t_type = st.selectbox("MA Type", ["EMA", "SMA"])
                
            submitted = st.form_submit_button("Create Alert")
            if submitted:
                if t_ticker and t_short < t_long:
                    alert_service.add_alert(t_ticker, t_short, t_long, t_type)
                    st.success(f"Alert created for {t_ticker} ({t_short}/{t_long} {t_type})")
                    st.rerun()
                else:
                    st.error("Invalid input. ensure ticker is set and Short Period < Long Period.")

    # List Alerts
    alerts = alert_service.alerts
    if alerts:
        st.subheader(f"Active Alerts ({len(alerts)})")
        
        # Display as table with delete button
        # Using columns for simple layout
        
        # Header
        h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns([1.5, 1, 0.8, 1, 1, 1, 1, 1.5, 1.5, 0.8])
        h1.markdown("**Ticker**")
        h2.markdown("**Pair**")
        h3.markdown("**Type**")
        h4.markdown("**Short Val**")
        h5.markdown("**Long Val**")
        h6.markdown("**Trend**")
        h7.markdown("**Days to Crossover**")
        h8.markdown("**Last Crossover**")
        h9.markdown("**Last Checked**")
        h10.markdown("**Action**")
        
        st.divider()
        
        for alert in alerts:
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([1.5, 1, 0.8, 1, 1, 1, 1, 1.5, 1.5, 0.8])
            c1.write(alert['ticker'])
            c2.write(f"{alert['short_p']} / {alert['long_p']}")
            c3.write(alert['ma_type'])
            
            # Additional data
            data = alert.get('last_check_data', {})
            c4.write(data.get('short_val', '-'))
            c5.write(data.get('long_val', '-'))
            c6.write(data.get('trend', '-'))
            
            # Estimated Crossover Days
            est_days = data.get('est_crossover_days')
            c7.write(str(est_days) if est_days is not None else "N/A")
            
            # Last Crossover
            last_cross = alert.get('last_crossover')
            if last_cross:
                icon = "🟢" if last_cross['signal'] == 1 else "🔴" # Green Up, Red Down
                arrow = "⬆️" if last_cross['signal'] == 1 else "⬇️"
                c8.write(f"{icon} {arrow} {last_cross['date']}")
            else:
                c8.write("-")
            
            # Format date friendly
            last_check = alert.get('last_checked')
            c9.write(last_check[:10] if last_check else "Never")
            
            if c10.button("🗑️", key=f"del_{alert['id']}", help="Delete Alert"):
                alert_service.delete_alert(alert['id'])
                st.rerun()
    else:
        st.info("No active alerts. Add one above to get started.")
