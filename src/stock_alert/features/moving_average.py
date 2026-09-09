"""Simple Moving Averages (SMAs) are crucial in economics and finance for
smoothing out volatile, short-term fluctuations (noise) in data
"""

import polars as pl
from .feature_base import Feature


class MovingAverage(Feature):
    """Simple Moving Average feature based on a window of x days

    Sorting is REQUIRED because rolling calculations depend on order.
    Always specify sort_by to ensure correct results
    """

    def __init__(
        self,
        column: str,
        window_days: int,
        sort_by: str,
        group_by: str | None = None,
    ) -> None:
        """
        Args:
            column: Column to compute SMA on.
            window_days: Size of rolling window.
            sort_by_column: Column to sort by before computing.
            group_by: Optional column to group by before computing.
        """
        self.column = column
        self.window_days = window_days
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"sma_{self.window_days}d"

    def compute(self) -> pl.Expr:
        """Returns the rolling mean expression."""
        # Create rolling mean logic
        expr = pl.col(self.column).rolling_mean(window_size=self.window_days)

        # Add the context (Grouping and Sorting)
        # If group_by is None, .over(None) is valid and processes the whole column
        expr = expr.over(partition_by=self.group_by, order_by=self.sort_by)

        return expr.alias(self.name)


class MovingAverageSpread(Feature):
    """Gap between a fast and a slow Simple Moving Average.

    Positive values mark a "golden cross" (fast above slow, bullish trend);
    negative values mark a "death cross" (fast below slow, bearish trend).
    Recomputes both rolling means from the raw price column directly since
    FeatureEngine applies every feature in one batched pass and cannot chain
    off another feature's output column.
    """

    def __init__(
        self,
        column: str,
        fast_window: int,
        slow_window: int,
        sort_by: str,
        group_by: str | None = None,
    ) -> None:
        self.column = column
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"sma_gap_{self.fast_window}_{self.slow_window}d"

    def compute(self) -> pl.Expr:
        price = pl.col(self.column)
        fast = price.rolling_mean(window_size=self.fast_window)
        slow = price.rolling_mean(window_size=self.slow_window)
        expr = fast - slow
        return expr.over(partition_by=self.group_by, order_by=self.sort_by).alias(
            self.name
        )
