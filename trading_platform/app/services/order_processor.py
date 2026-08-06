"""
Order Processor - Uses DAL for database operations
"""
import asyncio
import random
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.event_queue import event_queue
from app.dal import DatabaseService
from app.models.orders import OrderStatus
from app.services.telegram_notifier import send_trade_alert


async def process_order(order_id: int):
    """Process an order using the DAL"""
    async with AsyncSessionLocal() as db:
        service = DatabaseService(db)

        # Fetch the order
        order = await service.orders.get_order(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return

        # Simulate execution
        if random.random() < 0.8:
            # Execute the trade
            exit_price = order.price * (1 + random.uniform(-0.01, 0.01))
            profit = (exit_price - order.price) * order.quantity if order.side == "buy" else (order.price - exit_price) * order.quantity

            # Detect session
            from app.dal.trade_dal import TradeDAL
            session = TradeDAL.detect_session(datetime.utcnow())

            # Create trade using DAL
            trade = await service.trades.create_trade(
                order_id=order.id,
                symbol=order.symbol,
                direction=order.side,
                lot_size=order.quantity,
                entry_price=order.price,
                exit_price=round(exit_price, 5),
                profit=round(profit, 2),
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                instrument_type="forex",  # Default, can be enhanced
                session=session,
                slippage=0.0,
                commission=0.0,
                swap=0.0,
            )

            # Update order status
            await service.orders.update_order_status(
                order_id,
                OrderStatus.EXECUTED
            )

            # Send Telegram notification
            await send_trade_alert({
                "symbol": trade.symbol,
                "side": order.side,
                "volume": trade.lot_size,
                "profit": trade.profit,
                "entry": trade.entry_price,
                "exit": trade.exit_price
            })

        else:
            # Cancel the order
            await service.orders.update_order_status(
                order_id,
                OrderStatus.CANCELLED
            )


async def start_worker():
    """Continuously consume events from the queue"""
    while True:
        event = await event_queue.get()
        order_id = event.get("order_id")
        if order_id:
            await process_order(order_id)
        event_queue.task_done()