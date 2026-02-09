import polars as pl
from .base import Feature


class MovingAverage(Feature):
    """Simple Moving Average feature based on a window of x days
    
    Sorting is REQUIRED because rolling calculations depend on order.
    Always specify sort_by_column to ensure correct results
    """

    def __init__(self, column: str, window_days: int, sort_by_column: str) -> None:
        """
        Args:
            column: Column to compute SMA on
            window_days: Size of rolling window
            sort_by_column: Column to sort by before computing
        """
        self.column = column
        self.window_days = window_days
        self.sort_by_column = sort_by_column

    @property
    def name(self) -> str:
        return f"sma_{self.window_days}d"
    
    def compute(self, data: pl.LazyFrame, group_by: str | None = None) -> pl.LazyFrame:
        """Compute SMA with sorting applied"""
        if group_by:
            # Sort within each group
            data = data.sort([group_by, self.sort_by_column])
        else:
            # Sort entire dataset
            data = data.sort(self.sort_by_column)
        
        # Compute rolling mean
        expr = pl.col(self.column).rolling_mean(window_size=self.window_days)

        if group_by:
            expr = expr.over(group_by)

        return data.with_columns(expr.alias(self.name))
    

