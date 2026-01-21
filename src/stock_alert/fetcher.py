from abc import ABC, abstractmethod
import pandas as pd
import yfinance as yf
from common.logger import logger
from stock_alert.data_model import AssetData

class BaseFetcher(ABC):
    """Base class for stock data fetchers"""
    def __init__(self, ticker: str, period: str) -> None:
        self.ticker = ticker.upper()
        self.period = period

    @abstractmethod
    def fetch(self) -> AssetData:
        pass

class YFinanceFetcher(BaseFetcher):
    """Fetcher that uses yfinance to retrieve stock data"""

    def fetch(self) -> AssetData:
        logger.debug(f"Fetching data for {self.ticker} (period={self.period})")
        tk = yf.Ticker(self.ticker)
        df = tk.history(period=self.period, interval="1d", rounding=True)

        # Get metadata from yfinance
        info = tk.info

        # Validate required fields
        currency = info.get("currency")
        if not currency:
            raise ValueError(f"Currency information not available for {self.ticker}")
        
        asset_type = info.get("quoteType")
        if not asset_type:
            raise ValueError(f"Asset type information not available for {self.ticker}")
        
        return AssetData(
            data=df,
            ticker=self.ticker,
            name=info.get("longName", self.ticker),
            currency=currency,
            asset_type=info.get("quoteType", None),
            source="yfinance"
        )
    