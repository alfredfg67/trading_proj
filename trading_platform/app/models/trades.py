from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base

class Trade(Base):
    __tablename__ = "trades"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Core trade fields
    ticket_id = Column(Integer, unique=True, index=True)  # Broker ticket
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    symbol = Column(String, nullable=False)
    instrument_type = Column(String, nullable=False)      # forex / stock / synthetic / index / crypto
    direction = Column(String, nullable=False)            # buy / sell
    lot_size = Column(Float, nullable=False)

    # Price & timing
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # P&L & costs
    profit = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    slippage = Column(Float, nullable=True)

    # Metadata
    session = Column(String, nullable=True)               # Asian / London / NY / Overlap
    strategy_tag = Column(String, nullable=True)          # e.g., Scalper, Swing
    account_balance_after = Column(Float, nullable=True)

    # Backtest comparison
    backtest_expected_pnl = Column(Float, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_trades_symbol_entry_time', 'symbol', 'entry_time'),
        Index('idx_trades_instrument_type', 'instrument_type'),
        Index('idx_trades_session', 'session'),
        Index('idx_trades_strategy_tag', 'strategy_tag'),
    )