"""
Survival monitor: hosting cost tracking, profitability checks, shutdown logic.
An agent that can't pay its bills dies. No subsidies, no bailouts.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("virus-agent.survival")

DEFAULT_BURN_RATE = 0.0003  # BTC per day (rough VPS hosting cost)


class SurvivalMonitor:
    def __init__(self, agent):
        self.agent = agent
        self.daily_burn_btc = float(os.getenv("DAILY_BURN_BTC", str(DEFAULT_BURN_RATE)))
        self._total_revenue_btc: float = 0.0
        self._total_costs_btc: float = 0.0

    def runway_hours(self, current_balance_btc: float) -> float:
        """How many hours of hosting can the current balance cover?"""
        if self.daily_burn_btc <= 0:
            return float("inf")
        return (current_balance_btc / self.daily_burn_btc) * 24

    def profit_margin(self) -> float:
        """Current profit margin as a percentage."""
        if self._total_revenue_btc <= 0:
            return 0.0
        net = self._total_revenue_btc - self._total_costs_btc
        return (net / self._total_revenue_btc) * 100

    def is_profitable(self) -> bool:
        """Is the agent currently making money?"""
        return self.profit_margin() > 0

    def profit_summary(self) -> dict:
        net = self._total_revenue_btc - self._total_costs_btc
        margin = self.profit_margin()
        if margin > 0:
            status = "positive"
        elif margin == 0:
            status = "break_even"
        else:
            status = "negative"

        return {
            "net_btc": net,
            "margin_pct": round(margin, 2),
            "status": status,
        }

    def should_shutdown(self, current_balance_btc: float) -> bool:
        """Should this instance initiate shutdown?"""
        runway = self.runway_hours(current_balance_btc)
        if runway < 1:
            logger.critical(f"CRITICAL: < 1h runway ({runway:.2f}h). Shutting down.")
            return True
        return False

    def record_revenue(self, amount_btc: float):
        self._total_revenue_btc += amount_btc

    def record_cost(self, amount_btc: float):
        self._total_costs_btc += amount_btc
