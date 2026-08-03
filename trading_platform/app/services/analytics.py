import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.trades import Trade

async def compute_metrics(db: AsyncSession):
    result = await db.execute(select(Trade))
    trades = result.scalars().all()
    if not trades:
        return {"total_profit": 0, "win_rate": 0, "trade_count": 0}
    df = pd.DataFrame([{
        "profit": t.profit,
        "symbol": t.symbol,
        "volume": t.volume
    } for t in trades])
    total_profit = df["profit"].sum()
    wins = df[df["profit"] > 0]
    win_rate = len(wins) / len(df) if len(df) > 0 else 0
    return {
        "trade_count": len(df),
        "total_profit": round(total_profit, 2),
        "win_rate": round(win_rate * 100, 2),
        "avg_profit": round(df["profit"].mean(), 2),
        "total_volume": round(df["volume"].sum(), 2),
    }