import asyncio
import os
import sys

# Add the project root to Python path (so we can import app modules)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.telegram_notifier import send_trade_alert

async def test():
    """Send a test trade alert via Telegram."""
    print("Sending test message...")
    await send_trade_alert({
        "symbol": "EURUSD",
        "side": "buy",
        "volume": 0.1,
        "profit": 5.50,
        "entry": 1.1000,
        "exit": 1.1005
    })
    print("Test message sent! Check your Telegram.")

if __name__ == "__main__":
    asyncio.run(test())