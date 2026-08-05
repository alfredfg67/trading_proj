"""
Plotly chart builder functions
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from app.dashboard.config import COLORS, CHART_HEIGHT, CHART_TEMPLATE

def equity_curve(df):
    """Plot equity curve with drawdown shading"""
    if df.empty:
        return go.Figure()

    equity = df["profit"].cumsum()
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100

    fig = go.Figure()

    # Equity curve
    fig.add_trace(go.Scatter(
        x=df["exit_time"],
        y=equity,
        name="Equity",
        line=dict(color=COLORS["primary"], width=2),
        fill=None,
        mode="lines",
    ))

    # Drawdown shading
    fig.add_trace(go.Scatter(
        x=df["exit_time"],
        y=equity,
        name="Drawdown",
        fill="tozeroy",
        fillcolor="rgba(255,68,68,0.2)",
        line=dict(color="rgba(255,68,68,0)"),
        mode="lines",
        showlegend=False,
    ))

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig

def drawdown_chart(df):
    """Plot underwater/drawdown percentage"""
    if df.empty:
        return go.Figure()

    equity = df["profit"].cumsum()
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["exit_time"],
        y=drawdown,
        name="Drawdown %",
        line=dict(color=COLORS["negative"], width=2),
        fill="tozeroy",
        fillcolor="rgba(255,68,68,0.3)",
        mode="lines",
    ))

    fig.update_layout(
        title="Drawdown % (Underwater)",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        height=CHART_HEIGHT // 2,
        template=CHART_TEMPLATE,
        hovermode="x unified",
    )

    return fig

def rolling_performance(df, window=30):
    """Plot rolling win rate and avg P&L"""
    if df.empty or len(df) < window:
        return go.Figure()

    # Calculate rolling metrics
    rolling_wr = df["profit"].rolling(window).apply(lambda x: (x > 0).mean())
    rolling_avg = df["profit"].rolling(window).mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df["exit_time"],
            y=rolling_wr * 100,
            name="Win Rate %",
            line=dict(color=COLORS["primary"], width=2),
            mode="lines",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df["exit_time"],
            y=rolling_avg,
            name="Avg P&L",
            line=dict(color=COLORS["secondary"], width=2, dash="dot"),
            mode="lines",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=f"Rolling Performance (Window = {window} Trades)",
        xaxis_title="Date",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(title_text="Win Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text="Avg P&L ($)", secondary_y=True)

    return fig

def pnl_histogram(df):
    """P&L distribution histogram"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Histogram
    colors = [COLORS["positive"] if x > 0 else COLORS["negative"] for x in df["profit"]]
    fig.add_trace(go.Histogram(
        x=df["profit"],
        name="P&L Distribution",
        marker_color=colors,
        opacity=0.7,
        nbinsx=30,
    ))

    # Mean/median lines
    mean_val = df["profit"].mean()
    median_val = df["profit"].median()

    fig.add_vline(x=mean_val, line_dash="solid", line_color=COLORS["primary"],
                  annotation_text=f"Mean: ${mean_val:.2f}", annotation_position="top")
    fig.add_vline(x=median_val, line_dash="dash", line_color=COLORS["secondary"],
                  annotation_text=f"Median: ${median_val:.2f}", annotation_position="bottom")

    fig.update_layout(
        title="P&L Distribution",
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        bargap=0.05,
    )

    return fig

def duration_histogram(df):
    """Trade duration distribution"""
    if df.empty:
        return go.Figure()

    durations = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=durations,
        name="Duration Distribution",
        marker_color=COLORS["primary"],
        opacity=0.7,
        nbinsx=30,
    ))

    fig.update_layout(
        title="Trade Duration Distribution",
        xaxis_title="Duration (minutes)",
        yaxis_title="Frequency",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        bargap=0.05,
    )

    return fig

def pnl_by_category(df, category_col, title, color_map=None):
    """Bar chart of P&L by category (instrument/session)"""
    if df.empty:
        return go.Figure()

    # Check if category column exists
    if category_col not in df.columns:
        return go.Figure()

    # Validate column exists and has data
    if category_col not in df.columns:
        return go.Figure()

    # Aggregate
    agg = df.groupby(category_col).agg({
        "profit": "sum",
        "ticket_id": "count"
    }).reset_index()

    # If the column is missing, return empty figure
    if agg.empty:
        return go.Figure()

    agg.columns = ["category", "profit", "count"]
    agg["percentage"] = agg["profit"] / agg["profit"].sum() * 100
    agg["color"] = agg["profit"].apply(lambda x: COLORS["positive"] if x > 0 else COLORS["negative"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg["category"],
        y=agg["profit"],
        name="P&L",
        marker_color=agg["color"],
        text=agg["count"],
        textposition="outside",
        hovertemplate="%{x}<br>P&L: $%{y:.2f}<br>Trades: %{text}<extra></extra>",
    ))

    fig.update_layout(
        title=f"P&L by {title}",
        xaxis_title=title,
        yaxis_title="P&L ($)",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        showlegend=False,
    )

    return fig

def heatmap_winrate(df, metric="win_rate"):
    """Heatmap of instrument_type vs session"""
    if df.empty:
        return go.Figure()

    # Create pivot table
    if metric == "win_rate":
        pivot = df.pivot_table(
            values="profit",
            index="instrument_type",
            columns="session",
            aggfunc=lambda x: (x > 0).mean()
        )
        title = "Win Rate by Instrument & Session"
        zlabel = "Win Rate"
    else:
        pivot = df.pivot_table(
            values="profit",
            index="instrument_type",
            columns="session",
            aggfunc="sum"
        )
        title = "P&L by Instrument & Session"
        zlabel = "P&L ($)"

    # Convert to percentages for win rate
    if metric == "win_rate":
        pivot = pivot * 100

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="RdYlGn" if metric == "win_rate" else "RdBu",
        text=pivot.values.round(2),
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Session",
        yaxis_title="Instrument Type",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
    )

    return fig

def monthly_performance(df):
    """Monthly performance bar chart"""
    if df.empty:
        return go.Figure()

    df["month"] = df["entry_time"].dt.to_period("M").astype(str)
    monthly = df.groupby("month").agg({
        "profit": "sum",
        "ticket_id": "count",
        "profit": lambda x: (x > 0).mean()
    }).reset_index()
        # 1. Create a 'is_win' column first (assuming profit > 0 means a win)
    df['is_win'] = (df['profit'] > 0).astype(int)

    # 2. Group by month and calculate the 3 required metrics
    monthly = df.groupby('month').agg({
        'profit': 'sum',     # Total profit
        'ticket_id': 'count',# Number of trades
        'is_win': 'sum'      # Number of winning trades
    }).reset_index()

    # 3. Now calculate the win_rate (Winning Trades / Total Trades)
    monthly['win_rate'] = monthly['is_win'] / monthly['ticket_id']

    # 4. Select only the columns we need and rename them correctly
    monthly = monthly[['month', 'profit', 'ticket_id', 'win_rate']]
    monthly.columns = ["month", "pnL", "trades", "win_rate"]
    monthly["win_rate"] = monthly["win_rate"] * 100
    monthly["color"] = monthly["pnl"].apply(lambda x: COLORS["positive"] if x > 0 else COLORS["negative"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["month"],
        y=monthly["pnl"],
        name="Monthly P&L",
        marker_color=monthly["color"],
        text=monthly["trades"],
        textposition="outside",
        hovertemplate="%{x}<br>P&L: $%{y:.2f}<br>Trades: %{text}<br>Win Rate: %{customdata:.1f}%<extra></extra>",
        customdata=monthly["win_rate"],
    ))

    fig.update_layout(
        title="Monthly Performance",
        xaxis_title="Month",
        yaxis_title="P&L ($)",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        showlegend=False,
    )

    return fig

def slippage_histogram(df):
    """Slippage distribution"""
    if df.empty or "slippage" not in df.columns:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["slippage"],
        name="Slippage Distribution",
        marker_color=COLORS["primary"],
        opacity=0.7,
        nbinsx=30,
    ))

    fig.update_layout(
        title="Slippage Distribution",
        xaxis_title="Slippage",
        yaxis_title="Frequency",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        bargap=0.05,
    )

    return fig

def backtest_comparison(df):
    """Compare live vs backtest expected P&L"""
    if df.empty or "backtest_expected_pnl" not in df.columns:
        return go.Figure()

    # Filter rows with backtest data
    valid = df.dropna(subset=["backtest_expected_pnl"])

    if valid.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid["backtest_expected_pnl"],
        y=valid["profit"],
        mode="markers",
        name="Trades",
        marker=dict(
            color=valid["profit"].apply(lambda x: COLORS["positive"] if x > 0 else COLORS["negative"]),
            size=8,
            opacity=0.7,
        ),
        hovertemplate="Expected: $%{x:.2f}<br>Actual: $%{y:.2f}<extra></extra>",
    ))

    # Add diagonal line (perfect match)
    max_val = max(valid["backtest_expected_pnl"].max(), valid["profit"].max())
    min_val = min(valid["backtest_expected_pnl"].min(), valid["profit"].min())
    fig.add_trace(go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode="lines",
        name="Perfect Match",
        line=dict(dash="dash", color=COLORS["secondary"]),
    ))

    fig.update_layout(
        title="Live vs Backtest Expected P&L",
        xaxis_title="Backtest Expected P&L ($)",
        yaxis_title="Live Actual P&L ($)",
        height=CHART_HEIGHT,
        template=CHART_TEMPLATE,
        showlegend=True,
    )

    return fig