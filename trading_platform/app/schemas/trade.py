from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TradeResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    symbol: str
    entry_price: float
    exit_price: float
    volume: Optional[float] = None
    profit: float
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None

    class Config:
        from_attributes = True