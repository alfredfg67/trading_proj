from fastapi import APIRouter
from app.api.v1.endpoints import orders, stats, trades, auth, mt5

router = APIRouter()
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(trades.router, prefix="/trades", tags=["trades"])
router.include_router(stats.router, prefix="/stats", tags=["stats"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(mt5.router, prefix="/mt5", tags=["mt5"])   # <-- ADD THIS