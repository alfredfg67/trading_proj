import streamlit as st
import httpx
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")
st.title("📈 Trading Analytics Dashboard")

API_BASE = "http://localhost:8000/api/v1"

# Stats
stats_resp = httpx.get(f"{API_BASE}/stats/").json()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Profit", f"${stats_resp.get('total_profit', 0):.2f}")
col2.metric("Win Rate", f"{stats_resp.get('win_rate', 0)}%")
col3.metric("Trades", stats_resp.get('trade_count', 0))
col4.metric("Avg Profit", f"${stats_resp.get('avg_profit', 0):.2f}")

# Trades & equity curve
trades_resp = httpx.get(f"{API_BASE}/trades/").json()
if trades_resp:
    df = pd.DataFrame(trades_resp)
    df['close_time'] = pd.to_datetime(df['close_time'])
    df['cumsum'] = df['profit'].cumsum()
    st.subheader("📈 Equity Curve")
    fig = px.line(df, x='close_time', y='cumsum', title="Cumulative Profit")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📋 Recent Trades")
    st.dataframe(df[['symbol', 'entry_price', 'exit_price', 'profit', 'close_time']].head(20))
else:
    st.info("No trades yet. Create an order via the API!")