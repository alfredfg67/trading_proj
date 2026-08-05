"""
Trade Data Access Layer
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta

from app.dal.base import BaseRepository
from app.models.trades import Trade


class TradeDAL:
    """Trade-specific data access operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(Trade, db)

    # ─── Basic CRUD ──────────────────────────────────────────

    async def create_trade(self, **kwargs) -> Trade:
        """Create a new trade"""
        return await self.repo.create(**kwargs)

    async def bulk_create_trades(self, trades_data: List[Dict[str, Any]]) -> List[Trade]:
        """Create multiple trades in bulk"""
        return await self.repo.bulk_create(trades_data)

    async def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get a trade by ID"""
        return await self.repo.get_by_id(trade_id)

    async def get_trade_by_ticket(self, ticket_id: int) -> Optional[Trade]:
        """Get a trade by ticket ID"""
        result = await self.db.execute(
            select(Trade).where(Trade.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()

    # ─── Filtering & Queries ──────────────────────────────────

    async def get_trades(
        self,
        symbol: Optional[str] = None,
        instrument_type: Optional[str] = None,
        session: Optional[str] = None,
        strategy_tag: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
        order_by: str = "entry_time",
        order_desc: bool = True
    ) -> List[Trade]:
        """Get trades with multiple filters"""
        query = select(Trade)
        conditions = []

        if symbol:
            conditions.append(Trade.symbol == symbol)
        if instrument_type:
            conditions.append(Trade.instrument_type == instrument_type)
        if session:
            conditions.append(Trade.session == session)
        if strategy_tag:
            conditions.append(Trade.strategy_tag == strategy_tag)
        if start_date:
            conditions.append(Trade.entry_time >= start_date)
        if end_date:
            conditions.append(Trade.entry_time <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Ordering
        order_col = getattr(Trade, order_by, Trade.entry_time)
        if order_desc:
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_trades_by_order(self, order_id: int) -> List[Trade]:
        """Get all trades for a specific order"""
        result = await self.db.execute(
            select(Trade).where(Trade.order_id == order_id)
        )
        return result.scalars().all()

    async def get_trades_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Trade]:
        """Get trades within a date range"""
        return await self.get_trades(start_date=start_date, end_date=end_date)

    # ─── Analytics Queries ────────────────────────────────────

    async def get_trade_metrics(self) -> Dict[str, Any]:
        """Get aggregated trade metrics"""
        result = await self.db.execute(
            select(
                func.count(Trade.id).label("total_trades"),
                func.sum(Trade.profit).label("total_profit"),
                func.avg(Trade.profit).label("avg_profit"),
                func.max(Trade.profit).label("max_profit"),
                func.min(Trade.profit).label("min_profit"),
                func.avg(Trade.lot_size).label("avg_lot_size"),
                func.sum(Trade.lot_size).label("total_volume"),
                func.count().filter(Trade.profit > 0).label("winning_trades"),
                func.count().filter(Trade.profit < 0).label("losing_trades"),
            )
        )
        return dict(result.one())

    async def get_metrics_by_group(
        self,
        group_by: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get metrics grouped by a column (e.g., instrument_type, session)"""
        query = select(
            getattr(Trade, group_by).label("group"),
            func.count(Trade.id).label("trade_count"),
            func.sum(Trade.profit).label("total_profit"),
            func.avg(Trade.profit).label("avg_profit"),
            func.count().filter(Trade.profit > 0).label("wins"),
            func.count().filter(Trade.profit < 0).label("losses"),
            func.avg(Trade.slippage).label("avg_slippage"),
        ).group_by(getattr(Trade, group_by))

        if start_date:
            query = query.where(Trade.entry_time >= start_date)
        if end_date:
            query = query.where(Trade.entry_time <= end_date)

        result = await self.db.execute(query)
        return [dict(row._mapping) for row in result.all()]

    async def get_monthly_performance(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly performance for the last N months"""
        query = select(
            func.strftime("%Y-%m", Trade.entry_time).label("month"),
            func.count(Trade.id).label("trade_count"),
            func.sum(Trade.profit).label("total_profit"),
            func.avg(Trade.profit).label("avg_profit"),
            func.count().filter(Trade.profit > 0).label("wins"),
            func.count().filter(Trade.profit < 0).label("losses"),
        ).group_by("month").order_by("month")

        result = await self.db.execute(query)
        return [dict(row._mapping) for row in result.all()]

    # ─── Backtest Comparison ──────────────────────────────────

    async def get_backtest_comparison(self) -> List[Dict[str, Any]]:
        """Compare actual vs expected P&L"""
        result = await self.db.execute(
            select(
                Trade.id,
                Trade.profit.label("actual_pnl"),
                Trade.backtest_expected_pnl.label("expected_pnl"),
                (Trade.profit - Trade.backtest_expected_pnl).label("difference"),
                Trade.symbol,
                Trade.entry_time,
            ).where(Trade.backtest_expected_pnl.isnot(None))
        )
        return [dict(row._mapping) for row in result.all()]

    # ─── Session Detection ────────────────────────────────────

    @staticmethod
    def detect_session(entry_time: datetime) -> str:
        """Detect trading session based on entry time (UTC)"""
        hour = entry_time.hour
        if 0 <= hour < 8:
            return "Asian"
        elif 8 <= hour < 12:
            return "London"
        elif 12 <= hour < 16:
            return "Overlap"
        else:
            return "NY"