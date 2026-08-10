from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime
from app.dal.base import BaseRepository, DatabaseError
from app.models.trades import Trade
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, and_, func, join
from app.models.broker_account import BrokerAccount
from app.models.broker import Broker
from app.models.user import User

class TradeDAL:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(Trade, db)

    @staticmethod
    def detect_session(entry_time: datetime) -> str:
        hour = entry_time.hour
        if 0 <= hour < 8:
            return "Asian"
        elif 8 <= hour < 12:
            return "London"
        elif 12 <= hour < 16:
            return "Overlap"
        else:
            return "NY"

    async def create_trade(self, broker_account_id: int, **kwargs) -> Trade:
        """Create a new trade linked to a broker account."""
        kwargs['broker_account_id'] = broker_account_id
        return await self.repo.create(**kwargs)

    async def bulk_create_trades(self, trades_data: List[Dict[str, Any]]) -> List[Trade]:
        return await self.repo.bulk_create(trades_data)

    async def get_trade(self, trade_id: int) -> Optional[Trade]:
        return await self.repo.get_by_id(trade_id)

    async def get_trade_by_ticket(self, ticket_id: int) -> Optional[Trade]:
        try:
            result = await self.db.execute(select(Trade).where(Trade.ticket_id == ticket_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get trade by ticket {ticket_id}: {e}")

    async def get_trades(
        self,
        user_id: int,
        broker_account_id: Optional[int] = None,
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
        try:
            # Start with Trade table
            query = select(Trade)

            # Join to BrokerAccount, Broker, User to enforce user ownership
            query = query.join(BrokerAccount, Trade.broker_account_id == BrokerAccount.id)
            query = query.join(Broker, BrokerAccount.broker_id == Broker.id)
            query = query.join(User, Broker.user_id == User.id)

            conditions = [User.id == user_id]

            if broker_account_id is not None:
                conditions.append(Trade.broker_account_id == broker_account_id)

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

            order_col = getattr(Trade, order_by, Trade.entry_time)
            if order_desc:
                query = query.order_by(order_col.desc())
            else:
                query = query.order_by(order_col.asc())

            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get trades: {e}")

    async def get_trades_by_order(self, order_id: int) -> List[Trade]:
        try:
            result = await self.db.execute(select(Trade).where(Trade.order_id == order_id))
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get trades by order {order_id}: {e}")

    async def get_trades_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Trade]:
        return await self.get_trades(start_date=start_date, end_date=end_date)

    async def get_trade_metrics(
    self,
    user_id: int,
    broker_account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            query = select(
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
            # Join to enforce user ownership
            query = query.join(BrokerAccount, Trade.broker_account_id == BrokerAccount.id)
            query = query.join(Broker, BrokerAccount.broker_id == Broker.id)
            query = query.join(User, Broker.user_id == User.id)
            query = query.where(User.id == user_id)
            if broker_account_id is not None:
                query = query.where(Trade.broker_account_id == broker_account_id)

            result = await self.db.execute(query)
            return dict(result.one())
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get trade metrics: {e}")
    # Other methods like get_metrics_by_group, get_monthly_performance, get_backtest_comparison
    # can be added later. They will also need to support broker_account_id filtering.