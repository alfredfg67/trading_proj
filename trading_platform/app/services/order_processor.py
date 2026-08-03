import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.event_queue import event_queue
from app.models.orders import Order, OrderStatus
from app.models.trades import Trade
from app.services.telegram_notifier import send_trade_alert

async def process_order(order_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.PENDING:
            return
        # Simulate market execution: 80% chance fill
        if random.random() < 0.8:
            order.status = OrderStatus.EXECUTED
            exit_price = order.price * (1 + random.uniform(-0.01, 0.01))
            profit = (exit_price - order.price) * order.quantity if order.side == "buy" else (order.price - exit_price) * order.quantity
            trade = Trade(
                order_id=order.id,
                symbol=order.symbol,
                entry_price=order.price,
                exit_price=round(exit_price, 5),
                volume=order.quantity,
                profit=round(profit, 2)
            )
            db.add(trade)
            await db.commit()
            await db.refresh(trade)
            await send_trade_alert({
                "symbol": trade.symbol,
                "side": order.side,
                "volume": trade.volume,
                "profit": trade.profit,
                "entry": trade.entry_price,
                "exit": trade.exit_price
            })
        else:
            order.status = OrderStatus.CANCELLED
            await db.commit()

async def start_worker():
    while True:
        event = await event_queue.get()
        order_id = event.get("order_id")
        if order_id:
            await process_order(order_id)
        event_queue.task_done()