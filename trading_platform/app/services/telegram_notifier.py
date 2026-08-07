from telegram import Bot
from telegram.error import RetryAfter
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_trade_alert(trade_data: dict):
    if not settings.TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set")
        return

    message = (
        f"📊 *Trade Executed*\n"
        f"Symbol: {trade_data['symbol']}\n"
        f"Side: {trade_data['side'].upper()}\n"
        f"Volume: {trade_data['volume']}\n"
        f"Entry: {trade_data['entry']}\n"
        f"Exit: {trade_data['exit']}\n"
        f"Profit: *${trade_data['profit']:.2f}*"
    )
    try:
        await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
        logger.info("Telegram alert sent")
    except RetryAfter as e:
        logger.warning(f"Flood control, waiting {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")