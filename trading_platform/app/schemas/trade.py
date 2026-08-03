from pydantic import BaseModel
from datetime import datetime

class TradeResponse(BaseModel):
    id: int
    order_id: int
    symbol: str
    entry_price: float
    exit_price: float
    volume: float
    profit: float
    open_time: datetime
    close_time: datetime

    class Config:
        from_attributes = True