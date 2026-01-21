from typing import Protocol
import pandas as pd

from stock_alert.data_model import AssetData

class Transformer(Protocol):
    """Protocol for data transformers"""
    def transform(self, asset_data: AssetData) -> AssetData:
        ...
class CreateMovingAverage:
    """Transformer that creates a Moving Average"""
    def __init__(self, window_size: int) -> None:
        self.window_size = window_size

    def transform(self, asset_data: AssetData) -> AssetData:
        df = asset_data.data[["Close"]].copy()
        df[f"sma_{self.window_size}"] = df["Close"].rolling(window=self.window_size).mean()

        # This next part maybe shouldnt be here
        df["Diff"] = df["Close"] - df[f"sma_{self.window_size}"].round(1)
        df["Diff_pct"] = ((df["Diff"] / df[f"sma_{self.window_size}"]) * 100).round(1)
        return asset_data.with_data(df)