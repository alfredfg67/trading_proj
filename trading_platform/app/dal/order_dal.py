"""
Order Data Access Layer
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime

from app.dal.base import BaseRepository
from app.models.orders import Order, OrderStatus
from app.models.trades import Trade


class OrderDAL:
    """Order-specific data access operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(Order, db)

    # ─── Basic CRUD ──────────────────────────────────────────

    async def create_order(self, **kwargs) -> Order:
        """Create a new order"""
        return await self.repo.create(**kwargs)

    async def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by ID"""
        return await self.repo.get_by_id(order_id)

    async def get_order_by_ticket(self, ticket_id: int) -> Optional[Order]:
        """Get an order by external ticket ID"""
        result = await self.db.execute(
            select(Order).where(Order.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Order]:
        """Get orders with filters"""
        query = select(Order)
        conditions = []

        if status:
            conditions.append(Order.status == status)
        if symbol:
            conditions.append(Order.symbol == symbol)
        if start_date:
            conditions.append(Order.created_at >= start_date)
        if end_date:
            conditions.append(Order.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_order_status(
        self,
        order_id: int,
        status: OrderStatus,
        **kwargs
    ) -> Optional[Order]:
        """Update order status and optional fields"""
        update_data = {"status": status, **kwargs}
        return await self.repo.update(order_id, **update_data)

    async def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return await self.get_orders(status=OrderStatus.PENDING)

    # ─── Order ↔ Trade Relations ────────────────────────────

    async def get_order_with_trades(self, order_id: int) -> Optional[Order]:
        """Get order with its associated trades"""
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(select(Order).options(Order.trades))
        )
        return result.scalar_one_or_none()

    async def link_order_to_trade(
        self,
        order_id: int,
        trade_id: int
    ) -> bool:
        """Link an order to a trade"""
        result = await self.db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if not trade:
            return False
        trade.order_id = order_id
        await self.db.commit()
        return True

    # ─── Stats ────────────────────────────────────────────────

    async def get_order_stats(self) -> Dict[str, Any]:
        """Get order statistics"""
        total = await self.repo.count()
        pending = await self.repo.count({"status": OrderStatus.PENDING})
        executed = await self.repo.count({"status": OrderStatus.EXECUTED})
        cancelled = await self.repo.count({"status": OrderStatus.CANCELLED})

        return {
            "total": total,
            "pending": pending,
            "executed": executed,
            "cancelled": cancelled,
        }