from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dal import DatabaseService
from app.dal.base import DatabaseError

router = APIRouter()

@router.get("/")
async def get_stats(db: AsyncSession = Depends(get_db)):
    try:
        service = DatabaseService(db)
        metrics = await service.trades.get_trade_metrics()
        win_rate = await service.analytics.get_win_rate()
        profit_factor = await service.analytics.get_profit_factor()
        drawdown = await service.analytics.get_max_drawdown()
        return {
            "trade_count": metrics.get("total_trades", 0),
            "total_profit": metrics.get("total_profit", 0),
            "avg_profit": metrics.get("avg_profit", 0),
            "win_rate": win_rate * 100,
            "profit_factor": profit_factor,
            "max_drawdown": drawdown.get("max_drawdown", 0),
            "total_volume": metrics.get("total_volume", 0),
        }
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))