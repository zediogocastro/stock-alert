import pandas as pd
import yfinance as yf
from common.logger import logger

from .base import BaseFetcher


class YFinanceFetcher(BaseFetcher):
    """Fetcher to retrieve stock data from Yahoo Finance"""

    SUBFOLDER = "stocks"

    def __init__(self, identifiers: list[str], period: str = "2y") -> None:
        super().__init__()
        self.identifiers = identifiers
        self.period = period

    def fetch(self) -> pd.DataFrame:
        """Fetch data for all identifiers and return combined DataFrame"""
        logger.info(f"Fetching data for {self.identifiers} (period={self.period})")

        # Start to load consecutevely each stock data
        all_data = []

        for identifier in self.identifiers:
            try:
                logger.debug(f"Fetching {identifier}...")
                tk = yf.Ticker(identifier)
                df = tk.history(period=self.period, interval="1d", rounding=True)

                # Add identifier column to distinguish stocks
                df["identifier"] = identifier
                all_data.append(df)
                logger.debug(f"Fetched {identifier}: {len(df)} rows")

            except Exception as e:
                logger.error(f"Failed to fetch {identifier}: {e}")

        if not all_data:
            raise ValueError("No data fethed for any identifier")

        # Combine all data into one DataFrame
        combined_df = pd.concat(all_data, ignore_index=False)
        combined_df = combined_df.reset_index()

        logger.info(
            f"Combined data: {len(combined_df)} rows from {len(all_data)} assets"
        )

        # Write data
        self._write_data(data=combined_df)

        return combined_df
