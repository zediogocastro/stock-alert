import io
import ssl
import urllib.request

import certifi
import pandas as pd
from common.logger import logger

from .base import BaseFetcher


class InflationFetcher(BaseFetcher):
    """Fetcher for monthly CPI/HICP inflation (YoY %) from ECB and OECD.

    Data sources:
      - ECB Statistical Data Warehouse (ICP dataset) — HICP annual rate of
        change for EU/EEA countries and Eurozone/EU aggregates.
        API: https://data-api.ecb.europa.eu/service/data/ICP
      - OECD Stats JSON API — CPI YoY for non-EU OECD members and selected
        G20 economies.
        API: https://stats.oecd.org/SDMX-JSON/data/PRICES_CPI

    ECB data is preferred over OECD for any overlapping country codes.

    Output columns:
        Date            — first day of reference month (datetime)
        country_code    — ISO-2 country code (or 'U2' for Eurozone, 'EU' for EU27)
        country_name    — human-readable country name
        inflation_rate  — YoY change in consumer prices (%)
        source          — 'ECB' or 'OECD'
        identifier      — e.g. 'INFLATION_PT', 'INFLATION_U2'
    """

    SUBFOLDER = "inflation"

    _ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data/ICP"
    # OECD Data Explorer SDMX v2 — replaces the deprecated stats.oecd.org endpoint
    _OECD_BASE_URL = "https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL"

    # All available EU/EEA + Eurozone/EU aggregates in the ECB ICP dataset
    _ECB_COUNTRIES: list[str] = [
        "U2",  # Eurozone aggregate
        "EU",  # EU27 aggregate
        "AT",  # Austria
        "BE",  # Belgium
        "BG",  # Bulgaria
        "CY",  # Cyprus
        "CZ",  # Czechia
        "DE",  # Germany
        "DK",  # Denmark
        "EE",  # Estonia
        "ES",  # Spain
        "FI",  # Finland
        "FR",  # France
        "GR",  # Greece
        "HR",  # Croatia
        "HU",  # Hungary
        "IE",  # Ireland
        "IT",  # Italy
        "LT",  # Lithuania
        "LU",  # Luxembourg
        "LV",  # Latvia
        "MT",  # Malta
        "NL",  # Netherlands
        "PL",  # Poland
        "PT",  # Portugal
        "RO",  # Romania
        "SE",  # Sweden
        "SI",  # Slovenia
        "SK",  # Slovakia
    ]

    # Non-EU OECD members + key G20 emerging economies
    _OECD_COUNTRIES: list[str] = [
        "AUS",  # Australia
        "CAN",  # Canada
        "CHL",  # Chile
        "COL",  # Colombia
        "GBR",  # United Kingdom
        "ISL",  # Iceland
        "ISR",  # Israel
        "JPN",  # Japan
        "KOR",  # South Korea
        "MEX",  # Mexico
        "NOR",  # Norway
        "NZL",  # New Zealand
        "CHE",  # Switzerland
        "TUR",  # Turkey
        "USA",  # United States
        "BRA",  # Brazil
        "CHN",  # China
        "IND",  # India
        "IDN",  # Indonesia
        "ZAF",  # South Africa
    ]

    # ISO-2 → display name for ECB country codes (including aggregates)
    _ECB_NAMES: dict[str, str] = {
        "U2": "Eurozone",
        "EU": "European Union",
        "AT": "Austria",
        "BE": "Belgium",
        "BG": "Bulgaria",
        "CY": "Cyprus",
        "CZ": "Czechia",
        "DE": "Germany",
        "DK": "Denmark",
        "EE": "Estonia",
        "ES": "Spain",
        "FI": "Finland",
        "FR": "France",
        "GR": "Greece",
        "HR": "Croatia",
        "HU": "Hungary",
        "IE": "Ireland",
        "IT": "Italy",
        "LT": "Lithuania",
        "LU": "Luxembourg",
        "LV": "Latvia",
        "MT": "Malta",
        "NL": "Netherlands",
        "PL": "Poland",
        "PT": "Portugal",
        "RO": "Romania",
        "SE": "Sweden",
        "SI": "Slovenia",
        "SK": "Slovakia",
    }

    # ISO-3 (OECD) → (ISO-2, display name)
    _OECD_MAP: dict[str, tuple[str, str]] = {
        "AUS": ("AU", "Australia"),
        "CAN": ("CA", "Canada"),
        "CHL": ("CL", "Chile"),
        "COL": ("CO", "Colombia"),
        "GBR": ("GB", "United Kingdom"),
        "ISL": ("IS", "Iceland"),
        "ISR": ("IL", "Israel"),
        "JPN": ("JP", "Japan"),
        "KOR": ("KR", "South Korea"),
        "MEX": ("MX", "Mexico"),
        "NOR": ("NO", "Norway"),
        "NZL": ("NZ", "New Zealand"),
        "CHE": ("CH", "Switzerland"),
        "TUR": ("TR", "Turkey"),
        "USA": ("US", "United States"),
        "BRA": ("BR", "Brazil"),
        "CHN": ("CN", "China"),
        "IND": ("IN", "India"),
        "IDN": ("ID", "Indonesia"),
        "ZAF": ("ZA", "South Africa"),
    }

    def __init__(self, start_year: int = 2000) -> None:
        super().__init__()
        self.start_year = start_year

    # ECB 

    def _fetch_ecb(self) -> pd.DataFrame:
        """Fetch HICP YoY inflation from the ECB ICP dataset."""
        countries_key = "+".join(self._ECB_COUNTRIES)
        start = f"{self.start_year}-01"
        url = (
            f"{self._ECB_BASE_URL}"
            f"/M.{countries_key}.N.000000.4.ANR"
            f"?format=csvdata&startPeriod={start}"
        )
        logger.debug(f"ECB ICP URL: {url}")

        req = urllib.request.Request(url, headers={"Accept": "text/csv"})
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
            raw = pd.read_csv(io.BytesIO(response.read()))

        # ECB CSV has REF_AREA column directly containing the country code
        df = raw[["TIME_PERIOD", "OBS_VALUE", "REF_AREA"]].copy()
        df = df.rename(columns={"TIME_PERIOD": "Date", "OBS_VALUE": "inflation_rate", "REF_AREA": "country_code"})
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")
        df["inflation_rate"] = pd.to_numeric(df["inflation_rate"], errors="coerce")
        df["country_name"] = df["country_code"].map(self._ECB_NAMES)
        df["source"] = "ECB"
        df["identifier"] = "INFLATION_" + df["country_code"]

        df = df.dropna(subset=["inflation_rate"]).reset_index(drop=True)
        logger.info(
            f"ECB ICP: {len(df)} rows, "
            f"{df['country_code'].nunique()} countries, "
            f"from {df['Date'].min().strftime('%Y-%m')} to {df['Date'].max().strftime('%Y-%m')}"
        )
        return df

    # OECD

    def _fetch_oecd(self) -> pd.DataFrame:
        """Fetch CPI YoY inflation from the OECD Data Explorer SDMX v2 API.

        Uses the DSD_PRICES@DF_PRICES_ALL dataflow, filtering for:
          - Monthly frequency (M)
          - National methodology (N)
          - CPI measure
          - Annual percentage change (PA / _T / GY)
        """
        countries_key = "+".join(self._OECD_COUNTRIES)
        start = f"{self.start_year}-01"
        # Dimension order: REF_AREA.FREQ.METHODOLOGY.MEASURE.UNIT_MEASURE.EXPENDITURE.ADJUSTMENT.TRANSFORMATION
        key = f"{countries_key}.M.N.CPI.PA._T.N.GY"
        url = (
            f"{self._OECD_BASE_URL}"
            f"/{key}"
            f"?startPeriod={start}&format=csvfilewithlabels"
        )
        logger.debug(f"OECD CPI URL: {url}")

        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/csv",
                "User-Agent": "Mozilla/5.0",
            },
        )
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as response:
            raw = pd.read_csv(io.BytesIO(response.read()))

        # Map ISO-3 → (ISO-2, country_name)
        df = raw[["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]].copy()
        df = df.rename(columns={"REF_AREA": "iso3", "TIME_PERIOD": "Date", "OBS_VALUE": "inflation_rate"})
        df["country_code"] = df["iso3"].map(lambda c: self._OECD_MAP.get(str(c), (str(c), str(c)))[0])
        df["country_name"] = df["iso3"].map(lambda c: self._OECD_MAP.get(str(c), (str(c), str(c)))[1])
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")
        df["inflation_rate"] = pd.to_numeric(df["inflation_rate"], errors="coerce")
        df["source"] = "OECD"
        df["identifier"] = "INFLATION_" + df["country_code"]
        df = df.drop(columns=["iso3"])

        df = df.dropna(subset=["inflation_rate"]).sort_values(["country_code", "Date"]).reset_index(drop=True)
        logger.info(
            f"OECD CPI: {len(df)} rows, "
            f"{df['country_code'].nunique()} countries, "
            f"from {df['Date'].min().strftime('%Y-%m')} to {df['Date'].max().strftime('%Y-%m')}"
        )
        return df

    # Public 

    def fetch(self) -> pd.DataFrame:
        """Fetch and merge ECB + OECD inflation data.

        ECB data takes precedence for any country present in both sources.
        The merged DataFrame is saved to data/ingested/inflation/data.parquet.

        Returns:
            DataFrame with columns:
                Date, country_code, country_name, inflation_rate, source, identifier
        """
        logger.info("Fetching inflation data (ECB + OECD)...")

        ecb_df = self._fetch_ecb()
        oecd_df = self._fetch_oecd()

        # ECB takes priority: drop OECD rows for countries already covered by ECB
        ecb_iso2 = set(ecb_df["country_code"].unique())
        oecd_filtered = oecd_df[~oecd_df["country_code"].isin(ecb_iso2)].copy()

        df = pd.concat([ecb_df, oecd_filtered], ignore_index=True)
        df = df.sort_values(["country_code", "Date"]).reset_index(drop=True)

        logger.info(
            f"Merged inflation data: {len(df)} rows, "
            f"{df['country_code'].nunique()} countries"
        )

        self._write_data(df)
        return df
