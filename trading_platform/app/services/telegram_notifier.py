from telegram import Bot
from app.core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_trade_alert(trade_data: dict):
    if not settings.TELEGRAM_CHAT_ID:
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
    await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")