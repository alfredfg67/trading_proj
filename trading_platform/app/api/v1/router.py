from fastapi import APIRouter
from app.api.v1.endpoints import orders, stats, trades

router = APIRouter()
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(trades.router, prefix="/trades", tags=["trades"])
router.include_router(stats.router, prefix="/stats", tags=["stats"])