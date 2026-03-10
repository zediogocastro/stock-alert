from abc import ABC, abstractmethod
from pathlib import Path
import io
import urllib.request

import pandas as pd
import yfinance as yf
from common.logger import logger

class BaseFetcher(ABC):
    """Generic base class defining the fetching contract.

    Subclasses must define SUBFOLDER (str) to specify the ingestion subdirectory.
    Override BASE_CACHE_DIR at the class level to change the root cache directory.
    """
    SUBFOLDER: str
    BASE_CACHE_DIR: str = "data/ingested"

    def __init__(self, cache_dir: str | None = None) -> None:
        self.cache_dir = cache_dir or self.BASE_CACHE_DIR

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        pass

    def _write_data(self, data: pd.DataFrame) -> None:
        """Save fetched data to {cache_dir}/{SUBFOLDER}/data.parquet"""
        if not self.cache_dir:
            return  
        
        save_path = Path(self.cache_dir) / self.SUBFOLDER / "data.parquet"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(save_path)
        logger.info(f"Write data to {save_path}")

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

        logger.info(f"Combined data: {len(combined_df)} rows from {len(all_data)} assets")

        # Write data
        self._write_data(data=combined_df)

        return combined_df


class EuriborFetcher(BaseFetcher):
    """Fetcher to retrieve Euribor rates from the ECB Statistical Data Warehouse"""
    SUBFOLDER = "euribor"

    _ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data/FM"

    _TENOR_SERIES: dict[str, str] = {
        "1M": "EURIBOR1MD_",
        "3M": "EURIBOR3MD_",
        "6M": "EURIBOR6MD_",
        "12M": "EURIBOR1YD_",
    }

    def __init__(self, tenors: list[str] | None = None) -> None:
        super().__init__()
        valid_tenors = set(self._TENOR_SERIES)
        self.tenors = tenors or sorted(valid_tenors)
        invalid = set(self.tenors) - valid_tenors
        if invalid:
            raise ValueError(f"Invalid tenors: {invalid}. Valid options: {sorted(valid_tenors)}")

    def _build_url(self) -> str:
        series_ids = "+".join(self._TENOR_SERIES[t] for t in self.tenors)
        return f"{self._ECB_BASE_URL}/M.U2.EUR.RT.MM.{series_ids}.HSTA?format=csvdata"

    def fetch(self) -> pd.DataFrame:
        """Fetch Euribor rates from the ECB and return a tidy DataFrame."""
        logger.info(f"Fetching Euribor rates for tenors: {self.tenors}")

        url = self._build_url()
        logger.debug(f"ECB API URL: {url}")

        req = urllib.request.Request(url, headers={"Accept": "text/csv"})
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = pd.read_csv(io.BytesIO(response.read()))

        # Map internal ECB series IDs back to friendly tenor names
        reverse_map = {v: k for k, v in self._TENOR_SERIES.items()}

        df = raw[["TIME_PERIOD", "OBS_VALUE", "PROVIDER_FM_ID"]].copy()
        df = df.rename(columns={"TIME_PERIOD": "Date", "OBS_VALUE": "rate"})
        df["tenor"] = df["PROVIDER_FM_ID"].map(reverse_map)
        df["identifier"] = "EURIBOR_" + df["tenor"]
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        df = df.drop(columns=["PROVIDER_FM_ID"]).reset_index(drop=True)

        logger.info(f"Fetched Euribor data: {len(df)} rows for {len(self.tenors)} tenors")

        self._write_data(df)
        return df
