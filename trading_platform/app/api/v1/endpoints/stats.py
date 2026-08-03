from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.analytics import compute_metrics

router = APIRouter()

@router.get("/")
async def get_stats(db: AsyncSession = Depends(get_db)):
    metrics = await compute_metrics(db)
    return metrics