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
    
class RelativeStrengthIndex(Feature):
    """RSI (Relative Strength Index) - 14 day standard.
    Reveals Exhaustion: Is the world 'Overbought' or 'Oversold'?
    """
    def __init__(self, column: str, window_days: int = 14, sort_by: str = "date", group_by: str | None = None):
        self.column = column
        self.window_days = window_days
        self.sort_by = sort_by
        self.group_by = group_by

    @property
    def name(self) -> str:
        return f"rsi_{self.window_days}d"

    def compute(self) -> pl.Expr:
        # Calculate price changes
        diff = pl.col(self.column).diff()
        
        # Get gains (positive changes) and losses (negative changes)
        gain = pl.when(diff > 0).then(diff).otherwise(0)
        loss = pl.when(diff < 0).then(-diff).otherwise(0)
        
        # Average gains and losses
        avg_gain = gain.rolling_mean(window_size=self.window_days)
        avg_loss = loss.rolling_mean(window_size=self.window_days)
        
        # RS and RSI formula
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.over(partition_by=self.group_by, order_by=self.sort_by).alias(self.name)