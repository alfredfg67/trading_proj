# --- CRITICAL: Fix import path for Streamlit ---
import sys
import os

# Add the project root to Python's module search path.
# This ensures 'app' can be imported regardless of the working directory.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Now all imports from app.* will work.
# -------------------------------------------------

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots  # <-- Added this for the inline monthly chart

# Import local modules (now all inside app/)
from app.dashboard import config
from app.dashboard import db
from app.dashboard import metrics
from app.dashboard import charts
from app.dashboard.data_gen import generate_synthetic_trades

# Page config
st.set_page_config(
    page_title="Trading Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222d;
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid #00ff88;
    }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .caption { color: #888888; font-size: 0.85rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/trading.png", width=40)
    st.title("📊 Filters")

    # Data source selector
    data_source = st.radio(
        "Data Source",
        ["Database (Live)", "Synthetic (Demo)"],
        index=0,
        help="Switch between live database and synthetic demo data"
    )

    # Date range
    st.subheader("📅 Date Range")
    date_preset = st.selectbox(
        "Quick select",
        ["All", "7D", "30D", "90D", "YTD"],
        index=0,
    )

    # Calculate date range
    today = datetime.now()
    if date_preset == "7D":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_preset == "30D":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_preset == "90D":
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_preset == "YTD":
        start_date = datetime(today.year, 1, 1)
        end_date = today
    else:
        start_date = None
        end_date = None

    # Manual date picker
    if start_date:
        date_range = st.date_input(
            "Custom range",
            value=(start_date, end_date),
            max_value=today,
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = None
            end_date = None

    st.divider()

    # Other filters
    st.subheader("🔍 Filters")

    # Get data to populate filters
    df_filter = None
    if data_source == "Database (Live)":
        try:
            engine = db.get_engine()
            df_filter = db.load_trades(_engine=engine)
            filter_options = db.get_filter_options(df_filter)
        except:
            st.warning("Database not available. Using synthetic data.")
            df_filter = generate_synthetic_trades()
            filter_options = db.get_filter_options(df_filter)
    else:
        df_filter = generate_synthetic_trades()
        filter_options = db.get_filter_options(df_filter)

    instrument_types = st.multiselect(
        "Instrument Type",
        options=filter_options["instrument_types"],
        default=filter_options["instrument_types"], # Selects all available options
        help="Select one or more instrument types"
    )

   # Get the list and add "All" to the front
    sessions_options = ["All"] + filter_options["sessions"]

    sessions = st.multiselect(
        "Sessions",
        options=sessions_options,
        default=["All"],
        help="Select one or more sessions"
    )

    symbols = st.multiselect(
        "Symbols",
        options=filter_options["symbols"],
        default=[],
        help="Select specific symbols (leave empty for all)"
    )

    strategies = st.multiselect(
        "Strategy Tag",
        options=filter_options["strategies"],
        default=[],
        help="Filter by strategy tag"
    )

    st.divider()

    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Data info
    st.caption(f"Data source: {'Database' if data_source == 'Database (Live)' else 'Synthetic'}")

# Main content
st.title("📊 Trading Performance Dashboard")

# Load data based on filters
@st.cache_data(ttl=300)
def load_filtered_data(
    data_source,
    start_date,
    end_date,
    instrument_types,
    sessions,
    symbols,
    strategies,
):
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
            # If empty, fallback to synthetic
            if df.empty:
                st.info("No trades found in database. Using synthetic data for demo.")
                df = generate_synthetic_trades()
        except Exception as e:
            st.warning(f"Database error: {str(e)}. Using synthetic data.")
            df = generate_synthetic_trades()
    else:
        df = generate_synthetic_trades()

    # Apply filters for synthetic data (since we generated new data)
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

# Load data
df = load_filtered_data(
    data_source,
    start_date,
    end_date,
    instrument_types,
    sessions,
    symbols,
    strategies,
)

# If no data, show empty state
if df.empty:
    st.warning("⚠️ No trades match the current filters. Try adjusting your selection.")
    st.stop()

# Calculate metrics
all_metrics = metrics.calculate_all_metrics(df)
deltas = metrics.compare_periods(df, all_metrics)

# --- 1. KPI Row ---
st.subheader("📈 Key Performance Indicators")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    delta = deltas.get("total_trades", 0)
    st.metric(
        "Total Trades",
        f"{all_metrics['total_trades']:,}",
        delta=f"{delta:+,.0f}" if delta != 0 else None,
    )

with col2:
    delta = deltas.get("net_pnl", 0)
    pnl_color = "normal" if all_metrics["net_pnl"] >= 0 else "inverse"
    st.metric(
        "Net P&L",
        f"${all_metrics['net_pnl']:,.2f}",
        delta=f"${delta:+,.2f}" if delta != 0 else None,
        delta_color=pnl_color,
    )

with col3:
    delta = deltas.get("win_rate", 0)
    st.metric(
        "Win Rate",
        f"{all_metrics['win_rate']:.1f}%",
        delta=f"{delta:+.1f}%" if delta != 0 else None,
    )

with col4:
    delta = deltas.get("profit_factor", 0)
    st.metric(
        "Profit Factor",
        f"{all_metrics['profit_factor']:.2f}",
        delta=f"{delta:+.2f}" if delta != 0 else None,
    )

with col5:
    delta = deltas.get("sharpe", 0)
    st.metric(
        "Sharpe Ratio",
        f"{all_metrics['sharpe']:.2f}",
        delta=f"{delta:+.2f}" if delta != 0 else None,
    )

with col6:
    delta = deltas.get("max_drawdown", 0)
    st.metric(
        "Max Drawdown",
        f"{all_metrics['max_drawdown']:.1f}%",
        delta=f"{delta:+.1f}%" if delta != 0 else None,
        delta_color="inverse",
    )

st.caption("🔄 Deltas show change vs previous equal period")

# --- 2. Equity & Risk Section ---
st.divider()
st.subheader("📉 Equity & Risk")

col1, col2 = st.columns([3, 1])

with col1:
    fig_eq = charts.equity_curve(df)
    st.plotly_chart(fig_eq, use_container_width=True)

with col2:
    # Mini stats card
    st.markdown(
        f"""
        <div style="background:#1e222d;padding:16px;border-radius:8px;">
            <b>📊 Key Stats</b><br><br>
            Total P&L: <span class="{'positive' if all_metrics['net_pnl'] > 0 else 'negative'}">
                ${all_metrics['net_pnl']:,.2f}
            </span><br>
            Avg Trade: ${all_metrics['expectancy']:.2f}<br>
            Win Streak: {all_metrics['longest_win_streak']}<br>
            Loss Streak: {all_metrics['longest_loss_streak']}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Drawdown chart
fig_dd = charts.drawdown_chart(df)
st.plotly_chart(fig_dd, use_container_width=True)

# Rolling performance
st.subheader("🔄 Rolling Performance")
col1, col2 = st.columns([3, 1])

with col1:
    window = st.slider("Rolling Window (trades)", min_value=10, max_value=100, value=30, step=5)
    fig_roll = charts.rolling_performance(df, window)
    st.plotly_chart(fig_roll, use_container_width=True)

with col2:
    st.caption(
        """
        **What to look for:**
        - Win Rate trending up/down
        - Avg P&L direction
        - Widening gap = changing market conditions
        """
    )

# --- 3. Stats Table ---
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

# --- 4. Segmentation Section ---
st.divider()
st.subheader("🔬 Segmentation Analysis")

tab1, tab2, tab3, tab4 = st.tabs(
    ["By Instrument", "By Session", "Heatmap", "Monthly"]
)

with tab1:
    fig_inst = charts.pnl_by_category(df, "instrument_type", "Instrument")
    st.plotly_chart(fig_inst, use_container_width=True)

with tab2:
    fig_sess = charts.pnl_by_category(df, "session", "Session")
    st.plotly_chart(fig_sess, use_container_width=True)

with tab3:
    metric = st.radio(
        "Heatmap Metric",
        ["win_rate", "pnl"],
        format_func=lambda x: "Win Rate" if x == "win_rate" else "P&L",
        horizontal=True,
    )
    fig_heat = charts.heatmap_winrate(df, metric)
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# 🟢 FIX APPLIED HERE: Inline monthly performance chart
# ==========================================
with tab4:
    # 1. Work on a safe copy of the dataframe
    monthly_df = df.copy()

    # 2. CREATE THE 'month' COLUMN (Fixes the line 407 error)
    # We convert 'entry_time' to a year-month string so we can group by it.
    if 'entry_time' in monthly_df.columns:
        monthly_df['month'] = pd.to_datetime(monthly_df['entry_time']).dt.strftime('%Y-%m')
    elif 'month' not in monthly_df.columns:
        st.error("Data must contain 'entry_time' or 'month' column for monthly analysis.")
        st.stop()

    # 3. Create the 'is_win' flag
    monthly_df['is_win'] = (monthly_df['profit'] > 0).astype(int)

    # 4. Aggregate by month (This is the line that was failing)
    monthly = monthly_df.groupby('month').agg({
        'profit': 'sum',
        'ticket_id': 'count',
        'is_win': 'sum'
    }).reset_index()

    # 5. Calculate win rate and handle division by zero
    monthly['win_rate'] = monthly['is_win'] / monthly['ticket_id']
    monthly['win_rate'] = monthly['win_rate'].fillna(0)

    # 6. Rename columns to match chart expectations
    monthly = monthly[['month', 'profit', 'ticket_id', 'win_rate']]
    monthly.columns = ["month", "pnL", "trades", "win_rate"]

    # 7. Build the Plotly Figure using make_subplots for dual axes
    fig_month = make_subplots(specs=[[{"secondary_y": True}]])

    fig_month.add_trace(
        go.Bar(x=monthly['month'], y=monthly['pnL'], name='Net P&L'),
        secondary_y=False,
    )

    fig_month.add_trace(
        go.Scatter(
            x=monthly['month'], 
            y=monthly['win_rate'] * 100, 
            name='Win Rate (%)', 
            mode='lines+markers', 
            line=dict(color='#ff4444')
        ),
        secondary_y=True,
    )

    # 8. Final styling
    fig_month.update_layout(
        title="Monthly Performance",
        xaxis_title="Month",
        yaxis_title="Net P&L ($)",
        yaxis2_title="Win Rate (%)",
        legend=dict(x=0.5, y=-0.2, xanchor='center', orientation='h'),
        template="plotly_dark"
    )
    
    st.plotly_chart(fig_month, use_container_width=True)

# --- 5. Distribution Section ---
st.divider()
st.subheader("📊 Distributions")

col1, col2 = st.columns(2)

with col1:
    fig_pnl = charts.pnl_histogram(df)
    st.plotly_chart(fig_pnl, use_container_width=True)

with col2:
    fig_dur = charts.duration_histogram(df)
    st.plotly_chart(fig_dur, use_container_width=True)

# --- 6. Execution Quality Section ---
st.divider()
st.subheader("⚡ Execution Quality")

col1, col2 = st.columns(2)

with col1:
    fig_slip = charts.slippage_histogram(df)
    st.plotly_chart(fig_slip, use_container_width=True)

with col2:
    if "slippage" in df.columns:
        # Calculate average slippage per instrument type
        avg_slip = df.groupby("instrument_type")["slippage"].mean().reset_index()

        # Create an inline Plotly bar chart (bypassing the broken charts.pnl_by_category function)
        fig_avg_slip = go.Figure(
            data=[go.Bar(x=avg_slip['instrument_type'], y=avg_slip['slippage'])]
        )
        fig_avg_slip.update_layout(
            title="Average Slippage by Instrument",
            xaxis_title="Instrument",
            yaxis_title="Avg Slippage",
            template="plotly_dark"
        )
        st.plotly_chart(fig_avg_slip, use_container_width=True)

# Backtest comparison
if "backtest_expected_pnl" in df.columns and not df["backtest_expected_pnl"].isna().all():
    st.subheader("📐 Backtest vs Live Performance")
    fig_backtest = charts.backtest_comparison(df)
    st.plotly_chart(fig_backtest, use_container_width=True)

# Footer
st.divider()
st.caption(
    f"📊 Dashboard powered by Streamlit • {len(df)} trades analyzed • "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)