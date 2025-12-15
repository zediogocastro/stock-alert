from abc import ABC, abstractmethod
import pandas as pd
import yfinance as yf
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
    