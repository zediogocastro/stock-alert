from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import pandas as pd
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportConfig(BaseModel):
    ticker: str = Field("^GSPC")
    period: str = Field("2y")

    class Config:
        env_prefix = "STOCK_"

class BaseFetcher(ABC):
    """Abstract base class for fetching stock market data."""

    def fetch(self, config: ReportConfig) -> pd.DataFrame:
        """Return a dataframe with at least a 'Close' column."""
        logger.info(f"Starting fetch for {config}!")
        df = self._fetch(config)
        logger.info("Fetch Completed!")
        return df

    @abstractmethod
    def _fetch(self, config: ReportConfig) -> pd.DataFrame:
        """Concrete fetchers must implement this."""
        pass
    

class YFinanceFetcher(BaseFetcher):
    """Fetcher that uses yfinance to retrieve stock data."""

    def _fetch(self, config: ReportConfig) -> pd.DataFrame:
        logger.info(f"Fetching {config.ticker}")
        tk = yf.Ticker(config.ticker)
        df = tk.history(period=config.period, interval="1d", rounding=True)
        return df[["Close"]].copy()


if __name__ == "__main__":
    # TODO: Remove Hard Coded Configuration
    config = ReportConfig(
        ticker="^GSPC", 
        period="1y"
    )
    fetcher = YFinanceFetcher()
    df = fetcher.fetch(config)
    logger.info(df.head())