from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TradeResponse(BaseModel):
    id: int
    ticket_id: Optional[int] = None
    order_id: Optional[int] = None
    broker_account_id: int

    symbol: str
    instrument_type: str
    direction: str
    lot_size: float
    volume: Optional[float] = None

    entry_time: datetime
    exit_time: datetime
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None

    entry_price: float
    exit_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    profit: float
    commission: Optional[float] = None
    swap: Optional[float] = None
    slippage: Optional[float] = None

    session: Optional[str] = None
    strategy_tag: Optional[str] = None
    account_balance_after: Optional[float] = None
    backtest_expected_pnl: Optional[float] = None

    class Config:
        from_attributes = True