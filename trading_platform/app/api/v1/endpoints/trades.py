from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.trades import Trade
from app.schemas.trade import TradeResponse

router = APIRouter()

@router.get("/", response_model=list[TradeResponse])
async def list_trades(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).order_by(Trade.close_time.desc()).limit(100))
    return result.scalars().all()