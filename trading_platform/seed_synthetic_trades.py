"""
Seed script: creates a Broker + BrokerAccount for a given user (default:
admin@example.com) and generates a batch of realistic synthetic trades
so the dashboard has data to render.

Usage:
    python seed_synthetic_trades.py                # 500 trades for admin@example.com
    python seed_synthetic_trades.py --email admin@example.com --count 1500
    python seed_synthetic_trades.py --wipe          # delete existing trades for that account first
"""
import argparse
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.broker import Broker
from app.models.broker_account import BrokerAccount
from app.models.trades import Trade

# ---- Reference data -------------------------------------------------------

INSTRUMENTS = {
    "Forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"],
    "Indices": ["US30", "NAS100", "SPX500", "GER40"],
    "Commodities": ["XAUUSD", "XAGUSD", "USOIL"],
    "Crypto": ["BTCUSD", "ETHUSD"],
}

STRATEGY_TAGS = ["breakout", "mean_reversion", "trend_follow", "scalp", "news_fade", None]

# Base "price levels" so entry/exit prices look plausible per symbol
BASE_PRICE = {
    "EURUSD": 1.08, "GBPUSD": 1.27, "USDJPY": 151.0, "AUDUSD": 0.66,
    "USDCAD": 1.36, "NZDUSD": 0.61,
    "US30": 39500, "NAS100": 18200, "SPX500": 5200, "GER40": 18000,
    "XAUUSD": 2350, "XAGUSD": 28.5, "USOIL": 78.0,
    "BTCUSD": 64000, "ETHUSD": 3400,
}

PIP_SIZE = {  # rough "one tick" size per symbol, just for plausible price movement
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "AUDUSD": 0.0001,
    "USDCAD": 0.0001, "NZDUSD": 0.0001,
    "US30": 1, "NAS100": 1, "SPX500": 0.25, "GER40": 1,
    "XAUUSD": 0.1, "XAGUSD": 0.01, "USOIL": 0.01,
    "BTCUSD": 1, "ETHUSD": 0.1,
}


def session_for_hour(hour: int) -> str:
    if 0 <= hour < 8:
        return "Asian"
    elif 8 <= hour < 12:
        return "London"
    elif 12 <= hour < 16:
        return "Overlap"
    else:
        return "NY"


def random_entry_time(days_back: int) -> datetime:
    days_ago = random.uniform(0, days_back)
    dt = datetime.utcnow() - timedelta(days=days_ago)
    # bias trades toward "market hours" spread across all sessions
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def make_trade(broker_account_id: int, ticket_id: int, days_back: int) -> Trade:
    instrument_type = random.choice(list(INSTRUMENTS.keys()))
    symbol = random.choice(INSTRUMENTS[instrument_type])
    direction = random.choice(["buy", "sell"])
    entry_time = random_entry_time(days_back)
    hold_minutes = random.choice([5, 15, 30, 60, 120, 240, 480])
    exit_time = entry_time + timedelta(minutes=hold_minutes)

    base = BASE_PRICE[symbol]
    pip = PIP_SIZE[symbol]

    # win ~55% of trades, loss ~45%, with realistic-ish size distribution
    is_win = random.random() < 0.55
    move_pips = random.uniform(5, 80) * (1 if is_win else -1)
    if direction == "sell":
        move_pips *= -1

    entry_price = round(base * random.uniform(0.995, 1.005), 5)
    exit_price = round(entry_price + move_pips * pip, 5)

    lot_size = round(random.choice([0.01, 0.05, 0.1, 0.25, 0.5, 1.0]), 2)

    price_diff = (exit_price - entry_price) if direction == "buy" else (entry_price - exit_price)
    # crude contract-size multiplier so profit magnitudes look sane per asset class
    multiplier = {
        "Forex": 100000, "Indices": 1, "Commodities": 100, "Crypto": 1,
    }[instrument_type]
    profit = round(price_diff * lot_size * multiplier, 2)

    commission = round(-abs(lot_size) * random.uniform(2, 7), 2)
    swap = round(random.uniform(-3, 1), 2)
    slippage = round(random.uniform(0, 0.5), 2)

    return Trade(
        ticket_id=ticket_id,
        broker_account_id=broker_account_id,
        symbol=symbol,
        instrument_type=instrument_type,
        direction=direction,
        lot_size=lot_size,
        volume=lot_size,
        entry_time=entry_time,
        exit_time=exit_time,
        open_time=entry_time,
        close_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=round(entry_price - pip * 20, 5) if direction == "buy" else round(entry_price + pip * 20, 5),
        take_profit=round(entry_price + pip * 40, 5) if direction == "buy" else round(entry_price - pip * 40, 5),
        profit=profit,
        commission=commission,
        swap=swap,
        slippage=slippage,
        session=session_for_hour(entry_time.hour),
        strategy_tag=random.choice(STRATEGY_TAGS),
        account_balance_after=None,
        backtest_expected_pnl=round(profit * random.uniform(0.8, 1.2), 2),
    )


async def get_or_create_broker_account(db, user: User) -> BrokerAccount:
    result = await db.execute(select(Broker).where(Broker.user_id == user.id))
    broker = result.scalars().first()
    if broker is None:
        broker = Broker(user_id=user.id, broker_name="Synthetic Broker", server_info="Demo-Server")
        db.add(broker)
        await db.flush()

    result = await db.execute(select(BrokerAccount).where(BrokerAccount.broker_id == broker.id))
    account = result.scalars().first()
    if account is None:
        # mt5_login must be unique across the whole table
        mt5_login = random.randint(9_000_000, 9_999_999)
        account = BrokerAccount(
            broker_id=broker.id,
            mt5_login=mt5_login,
            account_currency="USD",
            label="Synthetic Test Account",
        )
        db.add(account)
        await db.flush()

    return account


async def seed(email: str, count: int, days_back: int, wipe: bool):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user is None:
            print(f"❌ No user found with email {email}. Create it first (e.g. via fix_db.py).")
            return

        account = await get_or_create_broker_account(db, user)
        await db.commit()
        print(f"✅ Using broker_account_id={account.id} (mt5_login={account.mt5_login}) for {email}")

        if wipe:
            await db.execute(delete(Trade).where(Trade.broker_account_id == account.id))
            await db.commit()
            print(f"🧹 Wiped existing trades for broker_account_id={account.id}")

        # figure out next ticket_id so we don't collide with existing unique tickets
        result = await db.execute(select(Trade.ticket_id).order_by(Trade.ticket_id.desc()).limit(1))
        last_ticket = result.scalar()
        next_ticket = (last_ticket or 1_000_000) + 1

        batch_size = 200
        created = 0
        trades_batch = []
        for i in range(count):
            trade = make_trade(account.id, next_ticket + i, days_back)
            trades_batch.append(trade)
            if len(trades_batch) >= batch_size:
                db.add_all(trades_batch)
                await db.commit()
                created += len(trades_batch)
                print(f"  ...{created}/{count} trades inserted")
                trades_batch = []

        if trades_batch:
            db.add_all(trades_batch)
            await db.commit()
            created += len(trades_batch)

        print(f"✅ Done. Inserted {created} synthetic trades for {email} "
              f"(broker_account_id={account.id}, spread over the last {days_back} days).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic trades for dashboard testing.")
    parser.add_argument("--email", default="admin01@example.com", help="User email to attach trades to.")
    parser.add_argument("--count", type=int, default=500, help="Number of trades to generate.")
    parser.add_argument("--days-back", type=int, default=180, help="Spread trades over this many past days.")
    parser.add_argument("--wipe", action="store_true", help="Delete existing trades for this account first.")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.count, args.days_back, args.wipe))