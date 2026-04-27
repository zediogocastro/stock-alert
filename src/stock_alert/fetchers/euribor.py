import io
import ssl
import urllib.request

import certifi
import pandas as pd
from common.logger import logger

from .base import BaseFetcher


class EuriborFetcher(BaseFetcher):
    """Fetcher to retrieve Euribor rates from the ECB Statistical Data Warehouse.

    Data source: ECB Statistical Data Warehouse (SDW), Financial Markets dataset (FM).
    API: https://data-api.ecb.europa.eu/service/data/FM

    The ECB FM dataset publishes Euribor as monthly averages of daily business-day
    fixings (historical close, average of observations through period). This is the
    only frequency available for Euribor via this API — daily business-day fixings
    are published by EMMI (the Euribor administrator) and are not freely accessible
    via the ECB endpoint.

    Each tenor is a separate series in the ECB system:
        1M  → EURIBOR1MD_  (1-month rate)
        3M  → EURIBOR3MD_  (3-month rate, most liquid benchmark)
        6M  → EURIBOR6MD_  (6-month rate)
        12M → EURIBOR1YD_  (12-month / 1-year rate)
    """

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
            raise ValueError(
                f"Invalid tenors: {invalid}. Valid options: {sorted(valid_tenors)}"
            )

    def _build_url(self) -> str:
        series_ids = "+".join(self._TENOR_SERIES[t] for t in self.tenors)
        return f"{self._ECB_BASE_URL}/M.U2.EUR.RT.MM.{series_ids}.HSTA?format=csvdata"

    def fetch(self) -> pd.DataFrame:
        """Fetch monthly Euribor rates from the ECB and return a tidy DataFrame.

        Returns a DataFrame with columns:
            Date       — first day of each month (datetime)
            rate       — Euribor rate in percent per annum
            tenor      — human-readable tenor label (e.g. '3M', '12M')
            identifier — prefixed label used downstream (e.g. 'EURIBOR_3M')
        """
        logger.info(f"Fetching Euribor rates for tenors: {self.tenors}")

        url = self._build_url()
        logger.debug(f"ECB API URL: {url}")

        req = urllib.request.Request(url, headers={"Accept": "text/csv"})
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
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

        logger.info(
            f"Fetched Euribor data: {len(df)} rows for {len(self.tenors)} tenors"
        )

        self._write_data(df)
        return df
