import pandas as pd
import yfinance as yf
from common.logger import logger

from .base import BaseFetcher


class OilFetcher(BaseFetcher):
    """Fetcher to retrieve crude oil benchmark prices from Yahoo Finance.

    Data source: Yahoo Finance (via yfinance), front-month futures contracts.

    The two main global benchmarks are:
        Brent — ICE Brent crude (North Sea origin).  The international
                reference price reported in the news (~70% of traded oil).
                Ticker: BZ=F
        WTI   — West Texas Intermediate (US domestic benchmark).
                Trades within a few dollars of Brent; the spread between
                the two is itself an informative signal.
                Ticker: CL=F

    Both are quoted in USD per barrel on a daily basis.
    """
    SUBFOLDER = "oil"

    _BENCHMARKS: dict[str, str] = {
        "BRENT": "BZ=F",
        "WTI": "CL=F",
    }

    def __init__(
        self,
        benchmarks: list[str] | None = None,
        period: str = "2y",
    ) -> None:
        """
        Args:
            benchmarks: Subset of benchmarks to fetch. Defaults to both
                        ``["BRENT", "WTI"]``. Valid values: ``"BRENT"``, ``"WTI"``.
            period:     History window accepted by yfinance (e.g. ``"1y"``,
                        ``"2y"``, ``"5y"``, ``"max"``). Defaults to ``"2y"``.
        """
        super().__init__()
        valid = set(self._BENCHMARKS)
        self.benchmarks = benchmarks or sorted(valid)
        invalid = set(self.benchmarks) - valid
        if invalid:
            raise ValueError(
                f"Invalid benchmarks: {invalid}. Valid options: {sorted(valid)}"
            )
        self.period = period

    def fetch(self) -> pd.DataFrame:
        """Fetch daily OHLCV data for the selected oil benchmarks.

        Returns a DataFrame with columns:
            Date       — trading day (datetime, timezone-naive)
            Open       — open price (USD/barrel)
            High       — intraday high (USD/barrel)
            Low        — intraday low (USD/barrel)
            Close      — closing price (USD/barrel)
            Volume     — number of contracts traded
            benchmark  — human-readable name (e.g. ``'BRENT'``, ``'WTI'``)
            identifier — prefixed label used downstream (e.g. ``'OIL_BRENT'``)
        """
        logger.info(
            f"Fetching oil prices for benchmarks: {self.benchmarks} "
            f"(period={self.period})"
        )

        all_data = []

        for name in self.benchmarks:
            ticker = self._BENCHMARKS[name]
            try:
                logger.debug(f"Fetching {name} ({ticker})...")
                tk = yf.Ticker(ticker)
                df = tk.history(period=self.period, interval="1d", rounding=True)

                df["benchmark"] = name
                df["identifier"] = f"OIL_{name}"
                all_data.append(df)
                logger.debug(f"Fetched {name}: {len(df)} rows")

            except Exception as e:
                logger.error(f"Failed to fetch {name} ({ticker}): {e}")

        if not all_data:
            raise ValueError("No data fetched for any oil benchmark")

        combined = pd.concat(all_data, ignore_index=False)
        combined = combined.reset_index()

        # Normalise the Date column: drop timezone so it aligns with other datasets
        if hasattr(combined["Date"].dtype, "tz") and combined["Date"].dt.tz is not None:
            combined["Date"] = combined["Date"].dt.tz_localize(None)

        logger.info(
            f"Combined oil data: {len(combined)} rows "
            f"from {len(all_data)} benchmarks"
        )

        self._write_data(combined)
        return combined
