from typing import Protocol
import pandas as pd

class Transformer(Protocol):
    """Protocol for data transformers"""
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        ...
class CreateMovingAverage:
    """Transformer that creates a Moving Average"""
    def __init__(self, window_size: int) -> None:
        self.window_size = window_size

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data[["Close"]].copy()
        df[f"sma_{self.window_size}"] = df["Close"].rolling(window=self.window_size).mean()

        # This next part maybe shouldnt be here
        df["Diff"] = df["Close"] - df[f"sma_{self.window_size}"].round(1)
        df["Diff_pct"] = ((df["Diff"] / df[f"sma_{self.window_size}"]) * 100).round(1)
        return df