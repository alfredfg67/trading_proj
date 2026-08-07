import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from app.dashboard.config import COLORS, CHART_HEIGHT, CHART_TEMPLATE

def equity_curve(df):
    if df.empty:
        return go.Figure()
    equity = df["profit"].cumsum()
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["exit_time"],
        y=equity,
        name="Equity",
        line=dict(color=COLORS["primary"], width=2),
        fill=None,
        mode="lines",
    ))
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
    if df.empty or len(df) < window:
        return go.Figure()
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
    if df.empty:
        return go.Figure()
    colors = [COLORS["positive"] if x > 0 else COLORS["negative"] for x in df["profit"]]
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["profit"],
        name="P&L Distribution",
        marker_color=colors,
        opacity=0.7,
        nbinsx=30,
    ))
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

def pnl_by_category(df, category_col, title):
    """
    Bar chart of P&L by category.
    Works even if 'ticket_id' is missing.
    """
    if df.empty or category_col not in df.columns:
        return go.Figure()

    # Compute count per category
    counts = df.groupby(category_col).size().reset_index(name='count')
    # Compute sum of profit per category
    profits = df.groupby(category_col)['profit'].sum().reset_index()
    # Merge
    agg = pd.merge(profits, counts, on=category_col)
    agg.columns = ["category", "profit", "count"]
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
    if df.empty:
        return go.Figure()
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
    if df.empty:
        return go.Figure()

    if not pd.api.types.is_datetime64_any_dtype(df["entry_time"]):
        df["entry_time"] = pd.to_datetime(df["entry_time"])

    df["month"] = df["entry_time"].dt.to_period("M").astype(str)

    monthly = df.groupby("month").agg(
        pnl=("profit", "sum"),
        trades=("ticket_id", "count"),
        win_rate=("profit", lambda x: (x > 0).mean())
    ).reset_index()

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
    if df.empty or "backtest_expected_pnl" not in df.columns:
        return go.Figure()
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