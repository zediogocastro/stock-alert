from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd
import yfinance as yf
from common.logger import logger

class BaseFetcher(ABC):
    """Generic base class defining the fetching contract"""
    def __init__(self, cache_dir: str | None) -> None:
        self.cache_dir = cache_dir

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        pass

    def _write_data(self, data:pd.DataFrame, source_name: str) -> None:
        """Save fetched data to a specific path"""
        if not self.cache_dir:
            return  
        
        save_path = Path(self.cache_dir) / source_name / "data.parquet"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(save_path)
        logger.info(f"Write data to {save_path}")

class YFinanceFetcher(BaseFetcher):
    """Fetcher to retrieve stock data from Yahoo Finance"""

    def __init__(self, identifiers: list[str], period: str = "2y", cache_dir: str | None = None) -> None:
        super().__init__(cache_dir)
        self.identifiers=identifiers
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

        logger.info(f"Combined data: {len(combined_df)} rows from {len(all_data)} assets")

        # Write data
        self._write_data(data=combined_df, source_name="stocks")

        return combined_df
    