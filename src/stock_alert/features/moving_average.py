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
        expr = expr.over(
            partition_by=self.group_by,
            order_by=self.sort_by
        )
 
        return expr.alias(self.name)
    
