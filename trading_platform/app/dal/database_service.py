"""
Database Service - Unified entry point for all DAL operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.dal.order_dal import OrderDAL
from app.dal.trade_dal import TradeDAL
from app.dal.analytics_dal import AnalyticsDAL


class DatabaseService:
    """
    Unified database service that provides access to all DALs.
    Use this as the single entry point for all database operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.orders = OrderDAL(db)
        self.trades = TradeDAL(db)
        self.analytics = AnalyticsDAL(db)

    # ─── Transaction Management ──────────────────────────────

    async def begin_transaction(self):
        """Begin a database transaction"""
        await self.db.begin()

    async def commit(self):
        """Commit the current transaction"""
        await self.db.commit()

    async def rollback(self):
        """Rollback the current transaction"""
        await self.db.rollback()

    # ─── Context Manager Support ─────────────────────────────

    async def __aenter__(self):
        """Enter async context manager"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager"""
        if exc_type:
            await self.db.rollback()
        else:
            await self.db.commit()