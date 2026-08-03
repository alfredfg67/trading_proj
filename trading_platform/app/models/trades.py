from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    symbol = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    open_time = Column(DateTime, server_default=func.now())
    close_time = Column(DateTime, server_default=func.now())