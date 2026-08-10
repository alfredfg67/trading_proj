import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from jose import jwt

from app.dashboard import config, metrics, charts
from app.dashboard.data_gen import generate_synthetic_trades
from app.dashboard.auth import login, logout, is_authenticated, get_headers, refresh_token

# ----------------------------------------------------------------------
# Constants
API_BASE = "http://localhost:8000/api/v1"

# ----------------------------------------------------------------------
# Page config & custom CSS (unchanged)
st.set_page_config(page_title="Trading Analytics Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .metric-card { background-color: #1e222d; padding: 16px; border-radius: 8px; border-left: 4px solid #00ff88; }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .caption { color: #888888; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# AUTHENTICATION GATE
if not is_authenticated():
    st.title("🔐 Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if login(email, password):
                st.rerun()
    st.stop()

# ----------------------------------------------------------------------
# SIDEBAR – Filters & Account Selector
with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/trading.png", width=40)
    st.title("📊 Filters")

    # --- Account selector ---
    @st.cache_data(ttl=300)
    def get_user_accounts():
        """Fetch list of broker accounts for the logged‑in user."""
        headers = get_headers()
        try:
            # We'll fetch trades to extract distinct account IDs.
            # In production, a dedicated /broker_accounts endpoint would be better.
            resp = requests.get(f"{API_BASE}/trades/?limit=1000", headers=headers)
            if resp.status_code == 200:
                trades = resp.json()
                account_ids = set(t.get("broker_account_id") for t in trades if t.get("broker_account_id"))
                if not account_ids:
                    account_ids = {1}
                accounts = [{"id": aid, "label": f"Account {aid}"} for aid in sorted(account_ids)]
                return accounts
            else:
                st.sidebar.error("Failed to load accounts")
                return []
        except Exception as e:
            st.sidebar.error(f"Error loading accounts: {e}")
            return []

    accounts = get_user_accounts()
    if accounts:
        account_options = ["All accounts"] + [f"{acc['label']} (ID: {acc['id']})" for acc in accounts]
        account_mapping = {opt: acc['id'] for opt, acc in zip(account_options[1:], accounts)}
        selected_label = st.selectbox("Select Account", account_options, index=0)
        if selected_label == "All accounts":
            account_id = None
        else:
            account_id = account_mapping.get(selected_label)
    else:
        account_id = None
        st.warning("No accounts found. Using default account.")

    # --- Data source ---
    data_source = st.radio("Data Source", ["Database (Live)", "Synthetic (Demo)"], index=0)

    # --- Date range ---
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

    # --- Additional filters (Instrument, Session, Symbol, Strategy) ---
    # We'll compute these from the loaded data, so they go after data loading.
    # But we need placeholders; they will be updated after data loads.
    instrument_types = st.multiselect("Instrument Type", [], default=[])
    sessions = st.multiselect("Session", [], default=[])
    symbols = st.multiselect("Symbols", [], default=[])
    strategies = st.multiselect("Strategy Tag", [], default=[])

    st.divider()

    # --- Refresh & Logout ---
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        logout()

    st.caption(f"User: {st.session_state.get('user_id', 'Unknown')}")

# ----------------------------------------------------------------------
# MAIN DASHBOARD CONTENT
st.title("📊 Trading Performance Dashboard")

# ----------------------------------------------------------------------
# DATA LOADING FUNCTION
@st.cache_data(ttl=300)
def load_filtered_data(account_id, start_date, end_date, data_source, instrument_types, sessions, symbols, strategies):
    """
    Load trades from the authenticated API or generate synthetic data.
    Also apply client‑side filters for instrument, session, symbol, strategy.
    """
    if data_source == "Synthetic (Demo)":
        df = generate_synthetic_trades()
        # Apply date filters
        if start_date:
            df = df[df["entry_time"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["entry_time"] <= pd.to_datetime(end_date)]
        # Apply category filters (if any)
        if instrument_types:
            df = df[df["instrument_type"].isin(instrument_types)]
        if sessions:
            df = df[df["session"].isin(sessions)]
        if symbols:
            df = df[df["symbol"].isin(symbols)]
        if strategies:
            df = df[df["strategy_tag"].isin(strategies)]
        return df
    else:
        # Live database via API
        headers = get_headers()
        url = f"{API_BASE}/trades/"
        params = {}
        if account_id is not None:
            params["account_id"] = account_id
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        # Add limit to avoid huge payloads (e.g., 5000)
        params["limit"] = 5000
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                trades = resp.json()
                if not trades:
                    st.info("No trades found for the selected account. Using synthetic data.")
                    return generate_synthetic_trades()
                df = pd.DataFrame(trades)
                # Convert timestamps
                for col in ["entry_time", "exit_time"]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                # Apply client‑side category filters (if any)
                if instrument_types:
                    df = df[df["instrument_type"].isin(instrument_types)]
                if sessions:
                    df = df[df["session"].isin(sessions)]
                if symbols:
                    df = df[df["symbol"].isin(symbols)]
                if strategies:
                    df = df[df["strategy_tag"].isin(strategies)]
                return df
            else:
                st.error(f"Failed to load trades: {resp.text}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading trades: {e}")
            return pd.DataFrame()

# ----------------------------------------------------------------------
# LOAD DATA
df = load_filtered_data(account_id, start_date, end_date, data_source, instrument_types, sessions, symbols, strategies)

if df.empty:
    st.warning("⚠️ No trades match the current filters. Try adjusting your selection.")
    st.stop()

# ----------------------------------------------------------------------
# UPDATE FILTER OPTIONS (populate multiselects with actual values from loaded data)
# We can't modify widget options after creation, but we can dynamically update them
# by re‑running the script. As a workaround, we'll show the filter options as info.
# A better approach: use st.session_state to store options and re‑render.
# For simplicity, we'll display them as checkboxes in the sidebar? 
# Since they are declared before data load, we'll leave them empty and note they are applied after data load.
# In a real application, you'd fetch filter options from the API or compute after loading.
# We'll skip dynamic population for now; the user can select manually.

# ----------------------------------------------------------------------
# COMPUTE METRICS
all_metrics = metrics.calculate_all_metrics(df)
deltas = metrics.compare_periods(df, all_metrics)

# ----------------------------------------------------------------------
# 1. KPI ROW
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

# ----------------------------------------------------------------------
# 2. EQUITY & RISK
st.divider()
st.subheader("📉 Equity & Risk")
col1, col2 = st.columns([3, 1])
with col1:
    fig_eq = charts.equity_curve(df)
    st.plotly_chart(fig_eq, use_container_width=True)
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

fig_dd = charts.drawdown_chart(df)
st.plotly_chart(fig_dd, use_container_width=True)

st.subheader("🔄 Rolling Performance")
col1, col2 = st.columns([3, 1])
with col1:
    window = st.slider("Rolling Window (trades)", min_value=10, max_value=100, value=30, step=5)
    fig_roll = charts.rolling_performance(df, window)
    st.plotly_chart(fig_roll, use_container_width=True)
with col2:
    st.caption("**What to look for:** - Win Rate trending up/down - Avg P&L direction - Widening gap = changing market conditions")

# ----------------------------------------------------------------------
# 3. STATS TABLE
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

# ----------------------------------------------------------------------
# 4. SEGMENTATION
st.divider()
st.subheader("🔬 Segmentation Analysis")
tab1, tab2, tab3, tab4 = st.tabs(["By Instrument", "By Session", "Heatmap", "Monthly"])
with tab1:
    fig_inst = charts.pnl_by_category(df, "instrument_type", "Instrument")
    st.plotly_chart(fig_inst, use_container_width=True)
with tab2:
    fig_sess = charts.pnl_by_category(df, "session", "Session")
    st.plotly_chart(fig_sess, use_container_width=True)
with tab3:
    metric_choice = st.radio("Heatmap Metric", ["win_rate", "pnl"],
                             format_func=lambda x: "Win Rate" if x == "win_rate" else "P&L",
                             horizontal=True)
    fig_heat = charts.heatmap_winrate(df, metric_choice)
    st.plotly_chart(fig_heat, use_container_width=True)
with tab4:
    fig_month = charts.monthly_performance(df)
    st.plotly_chart(fig_month, use_container_width=True)

# ----------------------------------------------------------------------
# 5. DISTRIBUTIONS
st.divider()
st.subheader("📊 Distributions")
col1, col2 = st.columns(2)
with col1:
    fig_pnl = charts.pnl_histogram(df)
    st.plotly_chart(fig_pnl, use_container_width=True)
with col2:
    fig_dur = charts.duration_histogram(df)
    st.plotly_chart(fig_dur, use_container_width=True)

# ----------------------------------------------------------------------
# 6. EXECUTION QUALITY
st.divider()
st.subheader("⚡ Execution Quality")
col1, col2 = st.columns(2)
with col1:
    fig_slip = charts.slippage_histogram(df)
    st.plotly_chart(fig_slip, use_container_width=True)
with col2:
    if "slippage" in df.columns:
        avg_slip = df.groupby("instrument_type")["slippage"].mean().reset_index()
        if not avg_slip.empty:
            avg_slip = avg_slip.rename(columns={"slippage": "profit"})
            fig_avg_slip = charts.pnl_by_category(avg_slip, "instrument_type", "Average Slippage")
            st.plotly_chart(fig_avg_slip, use_container_width=True)

# Backtest comparison
if "backtest_expected_pnl" in df.columns and not df["backtest_expected_pnl"].isna().all():
    st.subheader("📐 Backtest vs Live Performance")
    fig_backtest = charts.backtest_comparison(df)
    st.plotly_chart(fig_backtest, use_container_width=True)

# ----------------------------------------------------------------------
# FOOTER
st.divider()
st.caption(f"📊 Dashboard powered by Streamlit • {len(df)} trades analyzed • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")