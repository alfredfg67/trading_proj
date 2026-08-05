"""
Analytics Data Access Layer - Advanced metrics and aggregations
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from app.models.trades import Trade


class AnalyticsDAL:
    """Analytics-specific data access operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Core Metrics ─────────────────────────────────────────

    async def get_trade_performance(self) -> Dict[str, Any]:
        """Get core trade performance metrics"""
        result = await self.db.execute(
            select(
                func.count(Trade.id).label("total_trades"),
                func.sum(Trade.profit).label("net_pnl"),
                func.avg(Trade.profit).label("avg_pnl"),
                func.max(Trade.profit).label("max_win"),
                func.min(Trade.profit).label("max_loss"),
                func.sum(Trade.lot_size).label("total_volume"),
                func.avg(Trade.lot_size).label("avg_lot_size"),
                func.avg(Trade.slippage).label("avg_slippage"),
            )
        )
        return dict(result.one())

    async def get_win_rate(self) -> float:
        """Calculate win rate"""
        result = await self.db.execute(
            select(
                func.count().filter(Trade.profit > 0) / func.count(Trade.id)
            )
        )
        return result.scalar() or 0

    async def get_profit_factor(self) -> float:
        """Calculate profit factor"""
        result = await self.db.execute(
            select(
                func.sum(Trade.profit).filter(Trade.profit > 0) /
                func.abs(func.sum(Trade.profit).filter(Trade.profit < 0))
            )
        )
        return result.scalar() or 0

    # ─── Distribution Analysis ───────────────────────────────

    async def get_pnl_distribution(self, bins: int = 20) -> Dict[str, List]:
        """Get P&L distribution data (histogram)"""
        result = await self.db.execute(
            select(Trade.profit)
        )
        profits = [row[0] for row in result.all()]
        import numpy as np
        hist, bin_edges = np.histogram(profits, bins=bins)
        return {
            "histogram": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "mean": np.mean(profits) if profits else 0,
            "median": np.median(profits) if profits else 0,
            "std": np.std(profits) if profits else 0,
        }

    async def get_duration_distribution(self, bins: int = 20) -> Dict[str, List]:
        """Get trade duration distribution"""
        result = await self.db.execute(
            select(
                func.cast(
                    func.strftime('%s', Trade.exit_time) -
                    func.strftime('%s', Trade.entry_time),
                    float
                ) / 60
            ).where(
                Trade.exit_time.isnot(None),
                Trade.entry_time.isnot(None)
            )
        )
        durations = [row[0] for row in result.all() if row[0] is not None]
        import numpy as np
        hist, bin_edges = np.histogram(durations, bins=bins)
        return {
            "histogram": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "mean": np.mean(durations) if durations else 0,
            "median": np.median(durations) if durations else 0,
        }

    # ─── Streak Analysis ──────────────────────────────────────

    async def get_streaks(self, limit: int = 100) -> Dict[str, Any]:
        """Calculate win/loss streaks"""
        result = await self.db.execute(
            select(Trade.profit, Trade.exit_time)
            .order_by(Trade.exit_time.asc())
            .limit(limit)
        )
        trades = result.all()

        if not trades:
            return {"max_win_streak": 0, "max_loss_streak": 0}

        current_streak = 0
        win_streak = 0
        loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0

        for trade in trades:
            profit = trade[0]
            if profit > 0:
                current_streak = current_streak + 1 if current_streak > 0 else 1
                if current_streak > 0:
                    win_streak = max(win_streak, current_streak)
                if loss_streak > 0:
                    max_loss_streak = max(max_loss_streak, loss_streak)
                    loss_streak = 0
            else:
                current_streak = current_streak - 1 if current_streak < 0 else -1
                if current_streak < 0:
                    loss_streak = max(loss_streak, abs(current_streak))
                if win_streak > 0:
                    max_win_streak = max(max_win_streak, win_streak)
                    win_streak = 0

        # Final check
        max_win_streak = max(max_win_streak, win_streak)
        max_loss_streak = max(max_loss_streak, loss_streak)

        return {
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        }

    # ─── Drawdown ─────────────────────────────────────────────

    async def get_max_drawdown(self) -> Dict[str, Any]:
        """Calculate maximum drawdown"""
        result = await self.db.execute(
            select(Trade.profit, Trade.exit_time)
            .order_by(Trade.exit_time.asc())
        )
        profits = [row[0] for row in result.all()]
        if not profits:
            return {"max_drawdown": 0, "peak": 0, "trough": 0}

        peak = 0
        max_drawdown = 0
        peak_value = 0
        trough_value = 0
        cumulative = 0

        for profit in profits:
            cumulative += profit
            if cumulative > peak:
                peak = cumulative
                peak_value = cumulative
            drawdown = (peak - cumulative) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                trough_value = cumulative

        return {
            "max_drawdown": max_drawdown * 100,
            "peak": peak_value,
            "trough": trough_value,
        }