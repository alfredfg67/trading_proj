"""
MetaTrader 5 Sync Service – Fetches history deals and stores them in the database.
Handles large datasets, converts timestamps, and filters only executed trades.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.dal import DatabaseService
from app.dal.trade_dal import TradeDAL

logger = logging.getLogger(__name__)

# Try to import MetaTrader5, but fail gracefully if not installed
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    logger.warning("MetaTrader5 package not installed. MT5 sync will not work.")

# Mapping from MT5 deal type (integer) to direction string
# Only DEAL_TYPE_BUY (0) and DEAL_TYPE_SELL (1) are trades we care about.
MT5_DEAL_TYPE_MAP = {
    0: "buy",   # DEAL_TYPE_BUY
    1: "sell",  # DEAL_TYPE_SELL
}

# Other deal types: 2=balance, 3=credit, 4=charge, 5=correction, 6=bonus,
# 7=commission, 8=commission_daily, 9=commission_monthly, ... we skip them.


def mt5_timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert MT5 integer timestamp to datetime object."""
    return datetime.fromtimestamp(timestamp)


def mt5_deal_to_dict(deal) -> Dict[str, Any]:
    """
    Convert an MT5 deal (history deal object) to a dictionary
    that matches the `trades` table schema.
    """
    # Determine instrument type (heuristic)
    symbol = deal.symbol
    if "USD" in symbol or "EUR" in symbol or "GBP" in symbol or "JPY" in symbol:
        instrument_type = "forex"
    elif "BTC" in symbol or "ETH" in symbol or "LTC" in symbol:
        instrument_type = "crypto"
    elif "XAU" in symbol or "XAG" in symbol:
        instrument_type = "synthetic"
    elif "US30" in symbol or "NAS100" in symbol:
        instrument_type = "index"
    else:
        instrument_type = "other"

    # Direction – only buy/sell
    deal_type = deal.type
    direction = MT5_DEAL_TYPE_MAP.get(deal_type, "unknown")
    if direction == "unknown":
        # This should not happen if we filter correctly, but just in case
        logger.warning(f"Unknown deal type: {deal_type} for ticket {deal.ticket}")

    # Convert timestamp to datetime
    deal_time = mt5_timestamp_to_datetime(deal.time)

    # Profit, commission, swap
    profit = deal.profit or 0.0
    commission = deal.commission or 0.0
    swap = deal.swap or 0.0

    # Slippage not available in MT5 history
    slippage = 0.0

    # Session detection (using TradeDAL.detect_session)
    session = TradeDAL.detect_session(deal_time)

    # Stop loss and take profit – not available in deals, set to None
    stop_loss = None
    take_profit = None

    # Account balance after – not available
    account_balance_after = None
    backtest_expected_pnl = None

    return {
        "ticket_id": deal.ticket,
        "order_id": None,  # not linked to our order table
        "symbol": symbol,
        "instrument_type": instrument_type,
        "direction": direction,
        "lot_size": deal.volume,
        "entry_time": deal_time,
        "exit_time": deal_time,  # deals have a single timestamp
        "entry_price": deal.price,
        "exit_price": deal.price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "profit": profit,
        "commission": commission,
        "swap": swap,
        "slippage": slippage,
        "session": session,
        "strategy_tag": None,
        "account_balance_after": account_balance_after,
        "backtest_expected_pnl": backtest_expected_pnl,
    }


async def sync_mt5_history(
    from_date: Optional[datetime] = None,
    db: AsyncSession = None,
    batch_size: int = 500,
) -> Dict[str, int]:
    """
    Fetch history deals from MT5 and upsert them into the database.
    Handles large history in batches to avoid memory issues.

    Args:
        from_date: Start date for history (if None, fetch last 5 years).
        db: Optional AsyncSession (if not provided, creates its own).
        batch_size: Number of deals to process in one batch.

    Returns:
        Dict with counts: {'inserted': X, 'updated': Y, 'total': Z}
    """
    if mt5 is None:
        raise RuntimeError("MetaTrader5 package not installed. Please install it with: pip install MetaTrader5")

    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed. Is the terminal running and logged in?")

    try:
        account_info = mt5.account_info()
        if account_info is None:
            raise RuntimeError("MT5 account info not available. Is MetaTrader 5 running and logged in?")

        logger.info(f"Connected to MT5 account: {account_info.login}")

        # Determine date range – default to last 5 years
        if from_date is None:
            from_date = datetime.now() - timedelta(days=365 * 5)

        # Fetch all history deals (closed trades)
        deals = mt5.history_deals_get(
            from_date,
            datetime.now(),
        )
        if deals is None:
            logger.warning("No history deals found or error retrieving.")
            return {"inserted": 0, "updated": 0, "total": 0}

        # Filter only buy/sell deals (trade executions)
        trade_deals = [d for d in deals if d.type in (0, 1)]  # 0=buy, 1=sell
        if not trade_deals:
            logger.info("No trade deals found (only non-trade operations).")
            return {"inserted": 0, "updated": 0, "total": 0}

        logger.info(f"Fetched {len(deals)} history entries, of which {len(trade_deals)} are trade deals.")

        # Use the provided db session or create a new one
        async def do_sync(session: AsyncSession) -> Dict[str, int]:
            service = DatabaseService(session)
            inserted = 0
            updated = 0

            # Process in batches
            for i in range(0, len(trade_deals), batch_size):
                batch = trade_deals[i:i+batch_size]
                for deal in batch:
                    trade_data = mt5_deal_to_dict(deal)

                    # Check if trade already exists by ticket_id
                    existing = await service.trades.get_trade_by_ticket(
                        trade_data["ticket_id"]
                    )
                    if existing:
                        # Update all fields except id and order_id
                        await service.trades.repo.update(
                            existing.id,
                            **{k: v for k, v in trade_data.items() if k not in ("id", "order_id")}
                        )
                        updated += 1
                    else:
                        # Ensure broker_account_id is set – default to 1 for now
                        trade_data['broker_account_id'] = 1
                        await service.trades.create_trade(**trade_data)

                # Commit after each batch to avoid huge transaction
                await session.commit()
                logger.info(f"Processed {i+len(batch)} of {len(trade_deals)} deals")

            return {"inserted": inserted, "updated": updated, "total": len(trade_deals)}

        if db is not None:
            result = await do_sync(db)
        else:
            async with AsyncSessionLocal() as session:
                result = await do_sync(session)

        logger.info(f"Sync result: {result}")
        return result

    finally:
        mt5.shutdown()


async def run_mt5_sync_periodically(interval_hours: int = 24):
    """Background task to sync MT5 history every `interval_hours` hours."""
    while True:
        try:
            await sync_mt5_history()
        except Exception as e:
            logger.error(f"MT5 sync failed: {e}", exc_info=True)
        await asyncio.sleep(interval_hours * 3600)