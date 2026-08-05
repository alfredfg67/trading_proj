"""
Synthetic trade data generator for demo/testing
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_synthetic_trades(n_trades=500):
    """Generate realistic synthetic trade data"""
    np.random.seed(42)
    random.seed(42)

    # Time range: last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    # Instruments
    symbols = {
        "EURUSD": "forex",
        "GBPUSD": "forex",
        "USDJPY": "forex",
        "US30": "index",
        "NAS100": "index",
        "Volatility75": "synthetic",
        "BTCUSD": "crypto",
        "ETHUSD": "crypto",
        "AAPL": "stock",
        "TSLA": "stock",
    }

    # Sessions
    sessions = ["Asian", "London", "NY", "Overlap"]

    # Generate data
    trades = []

    for i in range(n_trades):
        # Random symbol
        symbol = random.choice(list(symbols.keys()))
        instrument_type = symbols[symbol]

        # Direction (slight buy bias for trending markets)
        direction = random.choices(["buy", "sell"], weights=[0.55, 0.45])[0]

        # Lot size (0.01 to 2.0)
        lot_size = round(random.uniform(0.01, 2.0), 2)

        # Entry time (random within last 6 months, more recent slightly weighted)
        days_ago = random.expovariate(1/60)  # More recent trades
        entry_time = end_date - timedelta(days=min(days_ago, 180))
        entry_time = entry_time.replace(minute=random.randint(0, 59), second=0)

        # Session based on time
        hour = entry_time.hour
        if 0 <= hour < 8:
            session = "Asian"
        elif 8 <= hour < 12:
            session = "London"
        elif 12 <= hour < 16:
            session = "Overlap"
        else:
            session = "NY"

        # Price levels (random walk)
        base_price = random.uniform(1.0, 100.0)
        if symbol in ["EURUSD", "GBPUSD", "USDJPY"]:
            base_price = random.uniform(1.0, 1.5)
        elif symbol in ["US30", "NAS100"]:
            base_price = random.uniform(30000, 45000)
        elif symbol in ["BTCUSD"]:
            base_price = random.uniform(30000, 70000)
        elif symbol in ["ETHUSD"]:
            base_price = random.uniform(2000, 4000)

        entry_price = round(base_price * random.uniform(0.95, 1.05), 5)

        # Exit price with realistic win/loss distribution (45% win rate)
        win = random.random() < 0.45
        if win:
            pct_move = random.uniform(0.01, 0.05)
        else:
            pct_move = random.uniform(0.01, 0.08)

        if direction == "buy":
            exit_price = entry_price * (1 + pct_move) if win else entry_price * (1 - pct_move)
        else:
            exit_price = entry_price * (1 - pct_move) if win else entry_price * (1 + pct_move)

        exit_price = round(exit_price, 5)

        # Profit
        if direction == "buy":
            profit = (exit_price - entry_price) * lot_size * 100000
        else:
            profit = (entry_price - exit_price) * lot_size * 100000

        # Add realistic noise
        profit = profit * random.uniform(0.8, 1.2)

        # Commission & swap
        commission = -abs(random.uniform(0.5, 5.0))
        swap = -abs(random.uniform(0, 2.0)) if session in ["Asian", "Overlap"] else 0

        # Slippage (more in volatile sessions)
        slippage = random.uniform(0.0001, 0.001) if random.random() < 0.3 else 0
        slippage = slippage * (1 if direction == "buy" else -1)

        # Exit time (duration 5 min to 4 hours)
        duration_minutes = random.expovariate(1/30) * 60  # avg 30 min
        exit_time = entry_time + timedelta(minutes=min(duration_minutes, 240))

        # Stop loss & take profit (some trades have them)
        stop_loss = entry_price * (1 - random.uniform(0.005, 0.02)) if random.random() < 0.7 else None
        take_profit = entry_price * (1 + random.uniform(0.01, 0.05)) if random.random() < 0.6 else None

        # Strategy tag (multi-strategy support)
        strategy_tag = random.choice(["Scalper", "Swing", "Breakout", "MeanReversion", None])

        # Backtest expected P&L (simulate)
        backtest_expected = profit * random.uniform(0.7, 1.3)

        trades.append({
            "ticket_id": i + 1,
            "symbol": symbol,
            "instrument_type": instrument_type,
            "direction": direction,
            "lot_size": lot_size,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "profit": round(profit, 2),
            "commission": round(commission, 2),
            "swap": round(swap, 2),
            "slippage": round(slippage, 5),
            "session": session,
            "strategy_tag": strategy_tag,
            "account_balance_after": None,  # Will calculate below
            "backtest_expected_pnl": round(backtest_expected, 2),
        })

    df = pd.DataFrame(trades)

    # Calculate account balance after (cumulative)
    df = df.sort_values("entry_time")
    df["account_balance_after"] = 10000 + df["profit"].cumsum() + df["commission"].cumsum() + df["swap"].cumsum()
    df["account_balance_after"] = df["account_balance_after"].round(2)

    return df

if __name__ == "__main__":
    # Quick test
    df = generate_synthetic_trades(500)
    print(f"Generated {len(df)} trades")
    print(df.head())
    print("\nWin rate:", (df["profit"] > 0).mean())
    print("Total P&L:", df["profit"].sum())