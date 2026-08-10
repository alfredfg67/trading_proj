from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(Integer, primary_key=True, index=True)
    broker_id = Column(Integer, ForeignKey("brokers.id"), nullable=False)
    mt5_login = Column(Integer, unique=True, nullable=False)
    account_currency = Column(String, default="USD")
    label = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    broker = relationship("Broker", backref="accounts")