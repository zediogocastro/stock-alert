import polars as pl
from .base import Feature

class MovingAverage(Feature):
    """Simple Moving Average feature based on a window of x days
    
    Sorting is REQUIRED because rolling calculations depend on order.
    Always specify sort_by to ensure correct results
    """

    def __init__(
            self, column: str, 
            window_days: int, 
            sort_by: str, 
            group_by: str | None = None,
    ) -> None:
        """
        Args:
            column: Column to compute SMA on
            window_days: Size of rolling window
            sort_by_column: Column to sort by before computing
            group_by: Optional column to group by before computing
        """
        self.column = column
        self.window_days = window_days
        self.sort_by = sort_by
        self.group_by = group_by
        
    @property
    def name(self) -> str:
        return f"sma_{self.window_days}d"
    
    def compute(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """Compute SMA with sorting applied"""
        if self.group_by:
            # Sort within each group
            data = data.sort([self.group_by, self.sort_by])
        else:
            # Sort entire dataset
            data = data.sort(self.sort_by)
        
        # Compute rolling mean 
        expr = pl.col(self.column).rolling_mean(window_size=self.window_days)

        if self.group_by:
            expr = expr.over(self.group_by)

        result = data.select(expr.alias(self.name))

        return data.with_columns(expr.alias(self.name))
    

