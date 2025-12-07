from abc import ABC, abstractmethod
from typing import Protocol
import yfinance as yf
import pandas as pd

class BaseFetcher(ABC):
    """Base class for stock data fetchers"""
    def __init__(self, ticker: str, period: str) -> None:
        self.ticker = ticker.upper()
        self.period = period

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        pass

class YFinanceFetcher(BaseFetcher):
    """Fetcher that uses yfinance to retrieve stock data"""

    def fetch(self) -> pd.DataFrame:
        tk = yf.Ticker(self.ticker)
        return tk.history(period=self.period, interval="1d", rounding=True)
    

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
    
class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
    
    def export(self, data: pd.DataFrame) -> None:
        """Template method: handles common logic"""
        self._ensure_directory_exists()
        self._write(data)

    @abstractmethod
    def _write(self, data: pd.DataFrame) -> None:
        """Subclasses implement the actual writing logic"""
        pass
    
    def _ensure_directory_exists(self) -> None:
        """Shared utility: ensure output directory exists"""
        import os
        directory = os.path.dirname(self.filename)
        if directory:
            os.makedirs(directory, exist_ok=True)

class CSVExporter(BaseExporter):
    """Exporter that writes data to CSV files"""
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def _write(self, data: pd.DataFrame) -> None:
        data.to_csv(self.filename, index=True)
        

class DataPipeline:
    """Class that is responsible for the ETL pipeline"""
    def __init__(self, 
                 fetcher: BaseFetcher, 
                 transformer: Transformer, 
                 exporter: BaseExporter):
        self.fetcher = fetcher
        self.transformer = transformer
        self.exporter = exporter

    def run(self) -> None:
        data = self.fetcher.fetch()
        transformed = self.transformer.transform(data)
        self.exporter.export(transformed)

