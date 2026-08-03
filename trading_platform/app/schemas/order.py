from pydantic import BaseModel
from datetime import datetime
from app.models.orders import OrderStatus

class OrderCreate(BaseModel):
    symbol: str
    side: str
    quantity: float
    price: float

class OrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True