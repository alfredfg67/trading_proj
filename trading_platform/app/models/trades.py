from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.broker_account import BrokerAccount 

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    broker_account_id = Column(Integer, ForeignKey("broker_accounts.id"), nullable=False)
    broker_account = relationship("BrokerAccount", backref="trades")

    symbol = Column(String, nullable=False)
    instrument_type = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    lot_size = Column(Float, nullable=False)

    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    profit = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    slippage = Column(Float, nullable=True)

    session = Column(String, nullable=True)
    strategy_tag = Column(String, nullable=True)
    account_balance_after = Column(Float, nullable=True)
    backtest_expected_pnl = Column(Float, nullable=True)

    broker_account = relationship("BrokerAccount", backref="trades")

    __table_args__ = (
        Index('idx_trades_symbol_entry_time', 'symbol', 'entry_time'),
        Index('idx_trades_instrument_type', 'instrument_type'),
        Index('idx_trades_session', 'session'),
        Index('idx_trades_strategy_tag', 'strategy_tag'),
        Index('idx_trades_broker_account_id', 'broker_account_id'),
    )