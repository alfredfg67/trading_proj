import numpy as np
import pandas as pd
from scipy import stats

def sharpe_ratio(returns, risk_free_rate=0.02, trading_days=252):
    if len(returns) < 2 or returns.std() == 0:
        return 0
    excess_returns = returns - risk_free_rate / trading_days
    return np.sqrt(trading_days) * excess_returns.mean() / returns.std()

def sortino_ratio(returns, risk_free_rate=0.02, trading_days=252):
    if len(returns) < 2:
        return 0
    excess_returns = returns - risk_free_rate / trading_days
    downside = returns[returns < 0].std()
    if downside == 0:
        return 0
    return np.sqrt(trading_days) * excess_returns.mean() / downside

def max_drawdown(equity_curve):
    if len(equity_curve) == 0:
        return 0
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()

def profit_factor(trades):
    if trades.empty:
        return 0
    gross_profit = trades[trades["profit"] > 0]["profit"].sum()
    gross_loss = abs(trades[trades["profit"] < 0]["profit"].sum())
    if gross_loss == 0:
        return 0 if gross_profit == 0 else float('inf')
    return gross_profit / gross_loss

def expectancy(trades):
    if trades.empty:
        return 0
    return trades["profit"].mean()

def win_rate(trades):
    if trades.empty:
        return 0
    return (trades["profit"] > 0).mean()

def streak(trades, kind="win"):
    if trades.empty:
        return 0
    wins = trades["profit"] > 0
    series = wins.astype(int) if kind == "win" else (~wins).astype(int)
    max_streak = 0
    current = 0
    for val in series:
        if val == 1:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak

def average_trade_duration(trades):
    if trades.empty:
        return 0
    durations = (trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 60
    return durations.mean()

def calculate_all_metrics(df):
    if df.empty:
        return { "total_trades": 0, "net_pnl": 0, "win_rate": 0, "profit_factor": 0, "sharpe": 0, "sortino": 0, "max_drawdown": 0, "expectancy": 0, "avg_win": 0, "avg_loss": 0, "win_loss_ratio": 0, "largest_win": 0, "largest_loss": 0, "avg_duration": 0, "longest_win_streak": 0, "longest_loss_streak": 0 }
    equity = df["profit"].cumsum()
    returns = df["profit"]
    avg_win = df[df["profit"] > 0]["profit"].mean() if (df["profit"] > 0).any() else 0
    avg_loss = df[df["profit"] < 0]["profit"].mean() if (df["profit"] < 0).any() else 0
    win_loss_ratio = 0
    if avg_loss != 0:
        win_loss_ratio = abs(avg_win / avg_loss)
    metrics = {
        "total_trades": len(df),
        "net_pnl": df["profit"].sum(),
        "win_rate": win_rate(df) * 100,
        "profit_factor": profit_factor(df),
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "max_drawdown": max_drawdown(equity) * 100,
        "expectancy": expectancy(df),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_loss_ratio": win_loss_ratio,
        "largest_win": df["profit"].max(),
        "largest_loss": df["profit"].min(),
        "avg_duration": average_trade_duration(df),
        "longest_win_streak": streak(df, "win"),
        "longest_loss_streak": streak(df, "loss"),
    }
    for key, value in metrics.items():
        if isinstance(value, float):
            metrics[key] = round(value, 2)
    return metrics

def compare_periods(df, baseline_metrics):
    if len(df) < 2:
        return {k: 0 for k in baseline_metrics.keys()}
    mid = len(df) // 2
    recent = df.iloc[mid:]
    previous = df.iloc[:mid]
    if recent.empty or previous.empty:
        return {k: 0 for k in baseline_metrics.keys()}
    recent_metrics = calculate_all_metrics(recent)
    previous_metrics = calculate_all_metrics(previous)
    deltas = {}
    for key in baseline_metrics.keys():
        deltas[key] = recent_metrics.get(key, 0) - previous_metrics.get(key, 0)
    return deltas