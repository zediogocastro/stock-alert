from typing import Protocol
import pandas as pd

class Transformer(Protocol):
    """Protocol for data transformers"""
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        ...
class CreateMovingAverage:
    """Transformer that creates a Moving Average of a certain column
    
    Args:
        window_size: Size of the rolling window
        column: Column name to calculate SMA on
        group_by: Optional column to group by 
    """
    def __init__(self, window_size: int, column: str, group_by: str | None = None) -> None:
        self.window_size = window_size
        self.column = column
        self.group_by = group_by

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        ma_col_name = f"moving_average_{self.window_size}d"

        # Calculate SMA wit optional grouping
        if self.group_by and self.group_by in df.columns:
            df[ma_col_name] = (df
                                .groupby(self.group_by)[self.column]
                                .rolling(window=self.window_size)
                                .mean()
                            )
        else:
            df[ma_col_name] = df[self.column].rolling(window=self.window_size).mean()

        # This next part maybe shouldnt be here
        df["Diff"] = df[self.column] - df[f"sma_{self.window_size}"].round(1)
        df["Diff_pct"] = ((df["Diff"] / df[f"sma_{self.window_size}"]) * 100).round(1)

        return df