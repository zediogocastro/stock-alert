import io
import itertools
import json
import ssl
import urllib.request

import certifi
import pandas as pd
from common.logger import logger

from .base import BaseFetcher


class InflationFetcher(BaseFetcher):
    """Fetcher for monthly CPI/HICP inflation (YoY %) from ECB, Eurostat, and OECD.

    Data sources:
      - Eurostat Euro-indicators (teicp000) — latest monthly HICP annual rate
        of change and flash estimates for EU member states and Eurozone/EU aggregates.
        API: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/teicp000
      - ECB Statistical Data Warehouse (ICP dataset) — historical HICP annual rate
        of change for EU/EEA countries and Eurozone/EU aggregates (2000-present).
        API: https://data-api.ecb.europa.eu/service/data/ICP
      - OECD Data Explorer (DSD_PRICES@DF_PRICES_ALL) — CPI YoY for non-EU OECD
        members and selected G20 economies.
        API: https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL

    Eurostat provides the freshest official HICP figures for recent months.
    ECB provides long-term history back to 2000. OECD provides global/non-EU
    coverage and supplementary fallback.

    Output columns:
        Date            — first day of reference month (datetime)
        country_code    — ISO-2 country code (or 'U2' for Eurozone, 'EU' for EU27)
        country_name    — human-readable country name
        inflation_rate  — YoY change in consumer prices (%)
        source          — 'Eurostat', 'ECB', or 'OECD'
        identifier      — e.g. 'INFLATION_PT', 'INFLATION_U2'
    """

    SUBFOLDER = "inflation"

    _ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data/ICP"
    _EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/teicp000"
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

    # OECD members + key G20 emerging economies (includes EU countries for fallback)
    _OECD_COUNTRIES: list[str] = [
        "AUT",  # Austria
        "BEL",  # Belgium
        "BGR",  # Bulgaria
        "AUS",  # Australia
        "CAN",  # Canada
        "CYP",  # Cyprus
        "CZE",  # Czechia
        "DEU",  # Germany
        "DNK",  # Denmark
        "ESP",  # Spain
        "EST",  # Estonia
        "FIN",  # Finland
        "FRA",  # France
        "GRC",  # Greece
        "CHL",  # Chile
        "HRV",  # Croatia
        "HUN",  # Hungary
        "COL",  # Colombia
        "GBR",  # United Kingdom
        "IRL",  # Ireland
        "ISL",  # Iceland
        "ISR",  # Israel
        "ITA",  # Italy
        "JPN",  # Japan
        "KOR",  # South Korea
        "LTU",  # Lithuania
        "LUX",  # Luxembourg
        "LVA",  # Latvia
        "MEX",  # Mexico
        "MLT",  # Malta
        "NLD",  # Netherlands
        "NOR",  # Norway
        "NZL",  # New Zealand
        "POL",  # Poland
        "PRT",  # Portugal
        "ROU",  # Romania
        "SVN",  # Slovenia
        "SVK",  # Slovakia
        "SWE",  # Sweden
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
        "AUT": ("AT", "Austria"),
        "BEL": ("BE", "Belgium"),
        "BGR": ("BG", "Bulgaria"),
        "AUS": ("AU", "Australia"),
        "CAN": ("CA", "Canada"),
        "CYP": ("CY", "Cyprus"),
        "CZE": ("CZ", "Czechia"),
        "DEU": ("DE", "Germany"),
        "DNK": ("DK", "Denmark"),
        "ESP": ("ES", "Spain"),
        "EST": ("EE", "Estonia"),
        "FIN": ("FI", "Finland"),
        "FRA": ("FR", "France"),
        "GRC": ("GR", "Greece"),
        "CHL": ("CL", "Chile"),
        "HRV": ("HR", "Croatia"),
        "HUN": ("HU", "Hungary"),
        "COL": ("CO", "Colombia"),
        "GBR": ("GB", "United Kingdom"),
        "IRL": ("IE", "Ireland"),
        "ISL": ("IS", "Iceland"),
        "ISR": ("IL", "Israel"),
        "ITA": ("IT", "Italy"),
        "JPN": ("JP", "Japan"),
        "KOR": ("KR", "South Korea"),
        "LTU": ("LT", "Lithuania"),
        "LUX": ("LU", "Luxembourg"),
        "LVA": ("LV", "Latvia"),
        "MEX": ("MX", "Mexico"),
        "MLT": ("MT", "Malta"),
        "NLD": ("NL", "Netherlands"),
        "NOR": ("NO", "Norway"),
        "NZL": ("NZ", "New Zealand"),
        "POL": ("PL", "Poland"),
        "PRT": ("PT", "Portugal"),
        "ROU": ("RO", "Romania"),
        "SVN": ("SI", "Slovenia"),
        "SVK": ("SK", "Slovakia"),
        "SWE": ("SE", "Sweden"),
        "CHE": ("CH", "Switzerland"),
        "TUR": ("TR", "Turkey"),
        "USA": ("US", "United States"),
        "BRA": ("BR", "Brazil"),
        "CHN": ("CN", "China"),
        "IND": ("IN", "India"),
        "IDN": ("ID", "Indonesia"),
        "ZAF": ("ZA", "South Africa"),
    }

    # Eurostat geo code → (ISO-2 / standard code, display name)
    _EUROSTAT_MAP: dict[str, tuple[str, str]] = {
        "EA20": ("U2", "Eurozone"),
        "EA": ("U2", "Eurozone"),
        "EU27_2020": ("EU", "European Union"),
        "EU": ("EU", "European Union"),
        "EL": ("GR", "Greece"),
        "UK": ("GB", "United Kingdom"),
        "AT": ("AT", "Austria"),
        "BE": ("BE", "Belgium"),
        "BG": ("BG", "Bulgaria"),
        "CY": ("CY", "Cyprus"),
        "CZ": ("CZ", "Czechia"),
        "DE": ("DE", "Germany"),
        "DK": ("DK", "Denmark"),
        "EE": ("EE", "Estonia"),
        "ES": ("ES", "Spain"),
        "FI": ("FI", "Finland"),
        "FR": ("FR", "France"),
        "HR": ("HR", "Croatia"),
        "HU": ("HU", "Hungary"),
        "IE": ("IE", "Ireland"),
        "IS": ("IS", "Iceland"),
        "IT": ("IT", "Italy"),
        "LT": ("LT", "Lithuania"),
        "LU": ("LU", "Luxembourg"),
        "LV": ("LV", "Latvia"),
        "MT": ("MT", "Malta"),
        "NL": ("NL", "Netherlands"),
        "NO": ("NO", "Norway"),
        "PL": ("PL", "Poland"),
        "PT": ("PT", "Portugal"),
        "RO": ("RO", "Romania"),
        "SE": ("SE", "Sweden"),
        "SI": ("SI", "Slovenia"),
        "SK": ("SK", "Slovakia"),
        "CH": ("CH", "Switzerland"),
        "TR": ("TR", "Turkey"),
        "AL": ("AL", "Albania"),
        "ME": ("ME", "Montenegro"),
        "MK": ("MK", "North Macedonia"),
        "RS": ("RS", "Serbia"),
        "XK": ("XK", "Kosovo"),
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

    # Eurostat

    def _fetch_eurostat(self) -> pd.DataFrame:
        """Fetch latest HICP YoY inflation from Eurostat Euro-indicators dataset (teicp000)."""
        url = f"{self._EUROSTAT_BASE_URL}?lang=en&unit=PCH_M12"
        logger.debug(f"Eurostat HICP URL: {url}")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
            data = json.load(response)

        dims: list[str] = data.get("id", [])
        sizes: list[int] = data.get("size", [])
        if not dims or not sizes:
            return pd.DataFrame(
                columns=["Date", "country_code", "country_name", "inflation_rate", "source", "identifier"]
            )

        dim_values: list[list[str]] = []
        for d in dims:
            cat = data.get("dimension", {}).get(d, {}).get("category", {})
            idx = cat.get("index", {})
            if isinstance(idx, dict):
                rev = {v: k for k, v in idx.items()}
                dim_values.append([rev[i] for i in range(len(rev))])
            else:
                dim_values.append(list(idx))

        strides: list[int] = []
        current_stride = 1
        for s in reversed(sizes):
            strides.append(current_stride)
            current_stride *= s
        strides.reverse()

        values: dict[str, float] = data.get("value", {})
        records: list[dict[str, object]] = []
        dim_indices = [range(s) for s in sizes]
        for coords in itertools.product(*dim_indices):
            flat_idx = sum(c * strd for c, strd in zip(coords, strides))
            if str(flat_idx) in values:
                val = values[str(flat_idx)]
                row: dict[str, object] = {dims[k]: dim_values[k][coords[k]] for k in range(len(dims))}
                row["value"] = val
                records.append(row)

        if not records:
            return pd.DataFrame(
                columns=["Date", "country_code", "country_name", "inflation_rate", "source", "identifier"]
            )

        df = pd.DataFrame(records)
        if "unit" in df.columns:
            df = df[df["unit"] == "PCH_M12"].copy()

        df = df[df["geo"].isin(self._EUROSTAT_MAP)].copy()
        df["country_code"] = df["geo"].map(lambda g: self._EUROSTAT_MAP.get(str(g), (str(g), str(g)))[0])
        df["country_name"] = df["geo"].map(lambda g: self._EUROSTAT_MAP.get(str(g), (str(g), str(g)))[1])
        df["Date"] = pd.to_datetime(df["time"], format="%Y-%m")
        df["inflation_rate"] = pd.to_numeric(df["value"], errors="coerce")
        df["source"] = "Eurostat"
        df["identifier"] = "INFLATION_" + df["country_code"]

        df = df.dropna(subset=["inflation_rate"]).sort_values(["country_code", "Date"]).reset_index(drop=True)
        df = df.drop_duplicates(subset=["country_code", "Date"], keep="first").reset_index(drop=True)
        df = df[["Date", "country_code", "country_name", "inflation_rate", "source", "identifier"]]

        logger.info(
            f"Eurostat HICP: {len(df)} rows, "
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
        """Fetch and merge ECB + Eurostat + OECD inflation data.

        - ECB provides historical HICP series for EU/EEA countries.
        - Eurostat (teicp000) provides the most recent official monthly HICP releases.
        - OECD provides CPI data for non-EU economies and supplementary fallback.

        The merged DataFrame is saved to data/ingested/inflation/data.parquet.

        Returns:
            DataFrame with columns:
                Date, country_code, country_name, inflation_rate, source, identifier
        """
        logger.info("Fetching inflation data (ECB + Eurostat + OECD)...")

        ecb_df = self._fetch_ecb()
        eurostat_df = self._fetch_eurostat()
        oecd_df = self._fetch_oecd()

        # Step 1: Combine ECB historical with Eurostat recent releases.
        # Eurostat takes precedence on overlapping dates.
        eu_frames = [f for f in [ecb_df, eurostat_df] if not f.empty]
        if eu_frames:
            eu_combined = pd.concat(eu_frames, ignore_index=True)
            eu_combined = (
                eu_combined.sort_values(["country_code", "Date"])
                .drop_duplicates(subset=["country_code", "Date"], keep="last")
                .reset_index(drop=True)
            )
        else:
            eu_combined = pd.DataFrame(
                columns=["Date", "country_code", "country_name", "inflation_rate", "source", "identifier"]
            )

        # Step 2: Merge with OECD. Keep OECD rows for non-EU countries or where OECD has newer observations.
        if not eu_combined.empty:
            eu_max_dates = eu_combined.groupby("country_code")["Date"].max()
            oecd_with_eu_max = oecd_df.copy()
            oecd_with_eu_max["eu_max_date"] = oecd_with_eu_max["country_code"].map(eu_max_dates)
            oecd_filtered = oecd_with_eu_max[
                oecd_with_eu_max["eu_max_date"].isna()
                | (oecd_with_eu_max["Date"] > oecd_with_eu_max["eu_max_date"])
            ].drop(columns=["eu_max_date"])
        else:
            oecd_filtered = oecd_df.copy()

        all_frames = [f for f in [eu_combined, oecd_filtered] if not f.empty]
        if all_frames:
            df = pd.concat(all_frames, ignore_index=True)
            df = (
                df.sort_values(["country_code", "Date"])
                .drop_duplicates(subset=["country_code", "Date"], keep="first")
                .reset_index(drop=True)
            )
        else:
            df = pd.DataFrame(
                columns=["Date", "country_code", "country_name", "inflation_rate", "source", "identifier"]
            )

        logger.info(
            f"Merged inflation data: {len(df)} rows, "
            f"{df['country_code'].nunique()} countries"
        )

        self._write_data(df)
        return df
