from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.models.trades import Trade
from app.dal.base import DatabaseError
import numpy as np

class AnalyticsDAL:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_trade_performance(self) -> Dict[str, Any]:
        try:
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
        except Exception as e:
            raise DatabaseError(f"Failed to get trade performance: {e}")

    async def get_win_rate(self) -> float:
        try:
            result = await self.db.execute(
                select(func.count().filter(Trade.profit > 0) / func.nullif(func.count(Trade.id), 0))
            )
            return result.scalar() or 0
        except Exception as e:
            raise DatabaseError(f"Failed to get win rate: {e}")

    async def get_profit_factor(self) -> float:
        try:
            gross_profit = await self.db.scalar(select(func.sum(Trade.profit)).filter(Trade.profit > 0))
            gross_loss = await self.db.scalar(select(func.sum(Trade.profit)).filter(Trade.profit < 0))
            gross_loss = abs(gross_loss) if gross_loss else 0
            if gross_loss == 0:
                return 0 if gross_profit == 0 else float('inf')
            return gross_profit / gross_loss
        except Exception as e:
            raise DatabaseError(f"Failed to get profit factor: {e}")

    async def get_pnl_distribution(self, bins: int = 20) -> Dict[str, List]:
        try:
            result = await self.db.execute(select(Trade.profit))
            profits = [row[0] for row in result.all()]
            if not profits:
                return {"histogram": [], "bin_edges": [], "mean": 0, "median": 0, "std": 0}
            hist, bin_edges = np.histogram(profits, bins=bins)
            return {
                "histogram": hist.tolist(),
                "bin_edges": bin_edges.tolist(),
                "mean": np.mean(profits),
                "median": np.median(profits),
                "std": np.std(profits),
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get P&L distribution: {e}")

    async def get_duration_distribution(self, bins: int = 20) -> Dict[str, List]:
        try:
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
            if not durations:
                return {"histogram": [], "bin_edges": [], "mean": 0, "median": 0}
            hist, bin_edges = np.histogram(durations, bins=bins)
            return {
                "histogram": hist.tolist(),
                "bin_edges": bin_edges.tolist(),
                "mean": np.mean(durations),
                "median": np.median(durations),
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get duration distribution: {e}")

    async def get_max_drawdown(self) -> Dict[str, Any]:
        try:
            result = await self.db.execute(select(Trade.profit, Trade.exit_time).order_by(Trade.exit_time.asc()))
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
        except Exception as e:
            raise DatabaseError(f"Failed to get max drawdown: {e}")

    async def get_streaks(self, limit: int = 100) -> Dict[str, Any]:
        try:
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
            for profit, _ in trades:
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
            max_win_streak = max(max_win_streak, win_streak)
            max_loss_streak = max(max_loss_streak, loss_streak)
            return {
                "max_win_streak": max_win_streak,
                "max_loss_streak": max_loss_streak,
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get streaks: {e}")