import asyncio
import random
import logging
from datetime import datetime
from app.core.database import AsyncSessionLocal
from app.core.event_queue import event_queue
from app.dal import DatabaseService
from app.models.orders import OrderStatus
from app.services.telegram_notifier import send_trade_alert
from telegram.error import RetryAfter
from app.dal.trade_dal import TradeDAL

logger = logging.getLogger(__name__)

async def process_order(order_id: int):
    async with AsyncSessionLocal() as db:
        service = DatabaseService(db)
        order = await service.orders.get_order(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return

        if random.random() < 0.8:   # 80% fill
            exit_price = order.price * (1 + random.uniform(-0.01, 0.01))
            if order.side == "buy":
                profit = (exit_price - order.price) * order.quantity
            else:
                profit = (order.price - exit_price) * order.quantity

            session = TradeDAL.detect_session(datetime.utcnow())

            # HARDCODE broker_account_id = 1 for now (default account)
            # This will be replaced in Phase 4 when user context is available
            broker_account_id = 1

            trade = await service.trades.create_trade(
                broker_account_id=broker_account_id,
                order_id=order.id,
                symbol=order.symbol,
                direction=order.side,
                lot_size=order.quantity,
                entry_price=order.price,
                exit_price=round(exit_price, 5),
                profit=round(profit, 2),
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                instrument_type="forex",   # You can improve detection later
                session=session,
                slippage=0.0,
                commission=0.0,
                swap=0.0,
            )
            await service.orders.update_order_status(order_id, OrderStatus.EXECUTED)

            alert_data = {
                "symbol": trade.symbol,
                "side": order.side,
                "volume": trade.lot_size,
                "profit": trade.profit,
                "entry": trade.entry_price,
                "exit": trade.exit_price
            }
            try:
                await send_trade_alert(alert_data)
            except RetryAfter as e:
                logger.warning(f"Telegram rate limit, retry after {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                await send_trade_alert(alert_data)
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")

        else:
            await service.orders.update_order_status(order_id, OrderStatus.CANCELLED)

async def start_worker():
    while True:
        event = await event_queue.get()
        order_id = event.get("order_id")
        if order_id:
            try:
                await process_order(order_id)
            except Exception as e:
                logger.error(f"Order {order_id} processing failed: {e}", exc_info=True)
        event_queue.task_done()