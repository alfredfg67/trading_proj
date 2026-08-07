import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import requests  # <-- ADDED
from app.dashboard import config, db, metrics, charts
from app.dashboard.data_gen import generate_synthetic_trades

st.set_page_config(page_title="Trading Analytics Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .metric-card { background-color: #1e222d; padding: 16px; border-radius: 8px; border-left: 4px solid #00ff88; }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .caption { color: #888888; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/trading.png", width=40)
    st.title("📊 Filters")
    data_source = st.radio("Data Source", ["Database (Live)", "Synthetic (Demo)"], index=0)

    st.subheader("📅 Date Range")
    date_preset = st.selectbox("Quick select", ["All", "7D", "30D", "90D", "YTD"], index=0)
    today = datetime.now()
    if date_preset == "7D":
        start_date, end_date = today - timedelta(days=7), today
    elif date_preset == "30D":
        start_date, end_date = today - timedelta(days=30), today
    elif date_preset == "90D":
        start_date, end_date = today - timedelta(days=90), today
    elif date_preset == "YTD":
        start_date, end_date = datetime(today.year, 1, 1), today
    else:
        start_date, end_date = None, None

    if start_date:
        date_range = st.date_input("Custom range", value=(start_date, end_date), max_value=today)
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = None, None

    st.divider()
    st.subheader("🔍 Filters")

    # Load filter options
    df_filter = None
    if data_source == "Database (Live)":
        try:
            engine = db.get_engine()
            df_filter = db.load_trades(_engine=engine)
            filter_options = db.get_filter_options(df_filter)
        except Exception:
            st.warning("Database not available. Using synthetic data.")
            df_filter = generate_synthetic_trades()
            filter_options = db.get_filter_options(df_filter)
    else:
        df_filter = generate_synthetic_trades()
        filter_options = db.get_filter_options(df_filter)

    # Ensure "All" is always an option for multiselect defaults
    for key in ["instrument_types", "sessions", "strategies"]:
        if key in filter_options:
            if not filter_options[key]:
                filter_options[key] = ["All"]
            elif "All" not in filter_options[key]:
                filter_options[key] = ["All"] + filter_options[key]

    instrument_types = st.multiselect("Instrument Type", options=filter_options["instrument_types"], default=["All"])
    sessions = st.multiselect("Session", options=filter_options["sessions"], default=["All"])
    symbols = st.multiselect("Symbols", options=filter_options["symbols"], default=[])
    strategies = st.multiselect("Strategy Tag", options=filter_options["strategies"], default=[])

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- MT5 Sync Button ---
    if st.button("🔄 Sync MT5 History", use_container_width=True):
        with st.spinner("Syncing with MT5..."):
            try:
                # Use the API endpoint (adjust if your API runs elsewhere)
                response = requests.post("http://localhost:8000/api/v1/mt5/sync", timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Synced {data.get('total', 0)} trades (inserted: {data.get('inserted', 0)}, updated: {data.get('updated', 0)})")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Sync failed: {response.status_code} - {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API server. Is it running?")
            except Exception as e:
                st.error(f"Sync error: {str(e)}")

    st.caption(f"Data source: {'Database' if data_source == 'Database (Live)' else 'Synthetic'}")

st.title("📊 Trading Performance Dashboard")

@st.cache_data(ttl=300)
def load_filtered_data(data_source, start_date, end_date, instrument_types, sessions, symbols, strategies):
    try:
        if data_source == "Database (Live)":
            try:
                engine = db.get_engine()
                df = db.load_trades(
                    start_date=start_date,
                    end_date=end_date,
                    instrument_types=instrument_types,
                    sessions=sessions,
                    symbols=symbols,
                    strategies=strategies,
                    _engine=engine
                )
                if df.empty:
                    st.info("No trades found in database. Using synthetic data.")
                    df = generate_synthetic_trades()
            except Exception as e:
                st.warning(f"Database error: {str(e)}. Using synthetic data.")
                df = generate_synthetic_trades()
        else:
            df = generate_synthetic_trades()

        # Apply filters for synthetic data (since we generated fresh)
        if data_source == "Synthetic (Demo)":
            if instrument_types and "All" not in instrument_types:
                df = df[df["instrument_type"].isin(instrument_types)]
            if sessions and "All" not in sessions:
                df = df[df["session"].isin(sessions)]
            if symbols:
                df = df[df["symbol"].isin(symbols)]
            if strategies:
                df = df[df["strategy_tag"].isin(strategies)]
            if start_date:
                df = df[df["entry_time"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["entry_time"] <= pd.to_datetime(end_date)]
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

df = load_filtered_data(data_source, start_date, end_date, instrument_types, sessions, symbols, strategies)

if df.empty:
    st.warning("⚠️ No trades match the current filters. Try adjusting your selection.")
    st.stop()

all_metrics = metrics.calculate_all_metrics(df)
deltas = metrics.compare_periods(df, all_metrics)

st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Trades", f"{all_metrics['total_trades']:,}",
              delta=f"{deltas.get('total_trades', 0):+,.0f}" if deltas.get('total_trades', 0) != 0 else None)
with col2:
    pnl_color = "normal" if all_metrics["net_pnl"] >= 0 else "inverse"
    st.metric("Net P&L", f"${all_metrics['net_pnl']:,.2f}",
              delta=f"${deltas.get('net_pnl', 0):+,.2f}" if deltas.get('net_pnl', 0) != 0 else None,
              delta_color=pnl_color)
with col3:
    st.metric("Win Rate", f"{all_metrics['win_rate']:.1f}%",
              delta=f"{deltas.get('win_rate', 0):+.1f}%" if deltas.get('win_rate', 0) != 0 else None)
with col4:
    st.metric("Profit Factor", f"{all_metrics['profit_factor']:.2f}",
              delta=f"{deltas.get('profit_factor', 0):+.2f}" if deltas.get('profit_factor', 0) != 0 else None)
with col5:
    st.metric("Sharpe Ratio", f"{all_metrics['sharpe']:.2f}",
              delta=f"{deltas.get('sharpe', 0):+.2f}" if deltas.get('sharpe', 0) != 0 else None)
with col6:
    st.metric("Max Drawdown", f"{all_metrics['max_drawdown']:.1f}%",
              delta=f"{deltas.get('max_drawdown', 0):+.1f}%" if deltas.get('max_drawdown', 0) != 0 else None,
              delta_color="inverse")

st.divider()
st.subheader("📉 Equity & Risk")
col1, col2 = st.columns([3, 1])
with col1:
    try:
        fig_eq = charts.equity_curve(df)
        st.plotly_chart(fig_eq, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering equity curve: {str(e)}")
with col2:
    st.markdown(f"""
        <div style="background:#1e222d;padding:16px;border-radius:8px;">
            <b>📊 Key Stats</b><br><br>
            Total P&L: <span class="{'positive' if all_metrics['net_pnl'] > 0 else 'negative'}">
                ${all_metrics['net_pnl']:,.2f}
            </span><br>
            Avg Trade: ${all_metrics['expectancy']:.2f}<br>
            Win Streak: {all_metrics['longest_win_streak']}<br>
            Loss Streak: {all_metrics['longest_loss_streak']}
        </div>
    """, unsafe_allow_html=True)

try:
    fig_dd = charts.drawdown_chart(df)
    st.plotly_chart(fig_dd, use_container_width=True)
except Exception as e:
    st.error(f"Error rendering drawdown chart: {str(e)}")

st.subheader("🔄 Rolling Performance")
col1, col2 = st.columns([3, 1])
with col1:
    window = st.slider("Rolling Window (trades)", min_value=10, max_value=100, value=30, step=5)
    try:
        fig_roll = charts.rolling_performance(df, window)
        st.plotly_chart(fig_roll, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering rolling performance: {str(e)}")
with col2:
    st.caption("**What to look for:** - Win Rate trending up/down - Avg P&L direction - Widening gap = changing market conditions")

st.divider()
st.subheader("📋 Detailed Statistics")
stats_df = pd.DataFrame([
    {"Metric": "Total Trades", "Value": f"{all_metrics['total_trades']:,}"},
    {"Metric": "Net P&L", "Value": f"${all_metrics['net_pnl']:,.2f}"},
    {"Metric": "Win Rate", "Value": f"{all_metrics['win_rate']:.1f}%"},
    {"Metric": "Profit Factor", "Value": f"{all_metrics['profit_factor']:.2f}"},
    {"Metric": "Sharpe Ratio", "Value": f"{all_metrics['sharpe']:.2f}"},
    {"Metric": "Sortino Ratio", "Value": f"{all_metrics['sortino']:.2f}"},
    {"Metric": "Max Drawdown", "Value": f"{all_metrics['max_drawdown']:.1f}%"},
    {"Metric": "Expectancy per Trade", "Value": f"${all_metrics['expectancy']:.2f}"},
    {"Metric": "Average Win", "Value": f"${all_metrics['avg_win']:.2f}"},
    {"Metric": "Average Loss", "Value": f"${all_metrics['avg_loss']:.2f}"},
    {"Metric": "Win/Loss Ratio", "Value": f"{all_metrics['win_loss_ratio']:.2f}"},
    {"Metric": "Largest Win", "Value": f"${all_metrics['largest_win']:,.2f}"},
    {"Metric": "Largest Loss", "Value": f"${all_metrics['largest_loss']:,.2f}"},
    {"Metric": "Avg Trade Duration", "Value": f"{all_metrics['avg_duration']:.0f} min"},
    {"Metric": "Longest Win Streak", "Value": f"{all_metrics['longest_win_streak']}"},
    {"Metric": "Longest Loss Streak", "Value": f"{all_metrics['longest_loss_streak']}"},
])
st.dataframe(stats_df, hide_index=True, use_container_width=True)

st.divider()
st.subheader("🔬 Segmentation Analysis")
tab1, tab2, tab3, tab4 = st.tabs(["By Instrument", "By Session", "Heatmap", "Monthly"])
with tab1:
    try:
        fig_inst = charts.pnl_by_category(df, "instrument_type", "Instrument")
        st.plotly_chart(fig_inst, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering by instrument: {str(e)}")
with tab2:
    try:
        fig_sess = charts.pnl_by_category(df, "session", "Session")
        st.plotly_chart(fig_sess, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering by session: {str(e)}")
with tab3:
    metric_choice = st.radio("Heatmap Metric", ["win_rate", "pnl"],
                             format_func=lambda x: "Win Rate" if x == "win_rate" else "P&L",
                             horizontal=True)
    try:
        fig_heat = charts.heatmap_winrate(df, metric_choice)
        st.plotly_chart(fig_heat, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering heatmap: {str(e)}")
with tab4:
    try:
        fig_month = charts.monthly_performance(df)
        st.plotly_chart(fig_month, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering monthly performance: {str(e)}")

st.divider()
st.subheader("📊 Distributions")
col1, col2 = st.columns(2)
with col1:
    try:
        fig_pnl = charts.pnl_histogram(df)
        st.plotly_chart(fig_pnl, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering P&L histogram: {str(e)}")
with col2:
    try:
        fig_dur = charts.duration_histogram(df)
        st.plotly_chart(fig_dur, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering duration histogram: {str(e)}")

st.divider()
st.subheader("⚡ Execution Quality")
col1, col2 = st.columns(2)
with col1:
    try:
        fig_slip = charts.slippage_histogram(df)
        st.plotly_chart(fig_slip, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering slippage histogram: {str(e)}")
with col2:
    if "slippage" in df.columns:
        avg_slip = df.groupby("instrument_type")["slippage"].mean().reset_index()
        if not avg_slip.empty:
            avg_slip = avg_slip.rename(columns={"slippage": "profit"})
            try:
                fig_avg_slip = charts.pnl_by_category(avg_slip, "instrument_type", "Average Slippage")
                st.plotly_chart(fig_avg_slip, use_container_width=True)
            except Exception as e:
                st.error(f"Error rendering avg slippage: {str(e)}")

if "backtest_expected_pnl" in df.columns and not df["backtest_expected_pnl"].isna().all():
    st.subheader("📐 Backtest vs Live Performance")
    try:
        fig_backtest = charts.backtest_comparison(df)
        st.plotly_chart(fig_backtest, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering backtest comparison: {str(e)}")

st.divider()
st.caption(f"📊 Dashboard powered by Streamlit • {len(df)} trades analyzed • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")