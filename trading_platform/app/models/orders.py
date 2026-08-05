from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    trades = relationship("Trade", backref="order", lazy="select")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())