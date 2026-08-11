from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.trade import TradeResponse
from app.dal.trade_dal import TradeDAL
from app.dal.base import DatabaseError

router = APIRouter()

@router.get("/", response_model=List[TradeResponse])
async def list_trades(
    account_id: Optional[int] = None,
    symbol: Optional[str] = None,
    instrument_type: Optional[str] = None,
    session: Optional[str] = None,
    strategy_tag: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 5000,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch trades belonging to the authenticated user."""
    try:
        dal = TradeDAL(db)
        trades = await dal.get_trades(
            user_id=current_user.id,
            broker_account_id=account_id,
            symbol=symbol,
            instrument_type=instrument_type,
            session=session,
            strategy_tag=strategy_tag,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            skip=skip,
        )
        return trades
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {str(e)}")