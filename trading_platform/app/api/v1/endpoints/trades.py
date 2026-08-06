from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dal import DatabaseService
from app.schemas.trade import TradeResponse

router = APIRouter()

@router.get("/", response_model=list[TradeResponse])
async def list_trades(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    service = DatabaseService(db)
    trades = await service.trades.get_trades(limit=limit)
    return trades