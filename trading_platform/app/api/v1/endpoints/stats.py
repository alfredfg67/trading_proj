from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.dal import DatabaseService
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.dal.base import DatabaseError

router = APIRouter()

@router.get("/")
async def get_stats(
    account_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = DatabaseService(db)
    try:
        metrics = await service.analytics.get_user_metrics(
            user_id=current_user.id,
            broker_account_id=account_id
        )
        # Also compute win rate and profit factor if needed
        return metrics
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))