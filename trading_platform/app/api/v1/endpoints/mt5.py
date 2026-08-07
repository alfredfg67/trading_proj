from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.services.mt5_sync import sync_mt5_history

router = APIRouter()

class SyncResponse(BaseModel):
    inserted: int
    updated: int
    total: int

@router.post("/sync", response_model=SyncResponse)
async def trigger_mt5_sync(
    from_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a full sync of MT5 trading history.
    Optionally provide a `from_date` to fetch history from that date onward.
    """
    try:
        result = await sync_mt5_history(from_date=from_date, db=db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))