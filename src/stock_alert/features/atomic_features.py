"""Module that create features that capture Momentum, Risk, and Memory."""

import polars as pl
from .feature_base import Feature

class Returns(Feature):
    """Calculates percentage change over N days.
    Reveals Momentum: How fast is the asset grwoing?
    """
    def __init__(self, 
                column: str, 
                n_days: int,
                sort_by: str,
                group_by: str | None
    ) -> None:
        self.column = column
        self.n_days = n_days
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"returns_{self.n_days}d"
    
    def compute(self) -> pl.Expr:
        # (Current / Previous) - 1
        expr = (pl.col(self.column) / pl.col(self.column).shift(self.n_days)) - 1
        return expr.over(
            partition_by=self.group_by,
            order_by=self.sort_by
        ).alias(self.name)
    
class Volatility(Feature):
    """Calculates Rolling Standard Deviation.
    Reveals Risk: How stable or panicky is the market?
    """
    def __init__(self, column: str, window_days: int, sort_by: str, group_by: str | None = None):
        self.column = column
        self.window_days = window_days
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"volatility_{self.window_days}d"

    def compute(self) -> pl.Expr:
        expr = pl.col(self.column).rolling_std(window_size=self.window_days)
        return expr.over(partition_by=self.group_by, order_by=self.sort_by).alias(self.name)
    
class Lag(Feature):
    """Shifts the data back by N days.
    Reveals Memory: What was the value 'then' compared to 'now'?
    """
    def __init__(self, column: str, n_days: int, sort_by: str, group_by: str | None = None):
        self.column = column
        self.n_days = n_days
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"lag_{self.n_days}d"

    def compute(self) -> pl.Expr:
        expr = pl.col(self.column).shift(self.n_days)
        return expr.over(partition_by=self.group_by, order_by=self.sort_by).alias(self.name)