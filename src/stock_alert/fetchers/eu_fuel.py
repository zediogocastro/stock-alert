import io
import ssl
import urllib.request

import certifi
import pandas as pd
from common.logger import logger

from .base import BaseFetcher


class EUFuelFetcher(BaseFetcher):
    """Fetcher for EU consumer fuel prices from the European Commission Weekly Oil Bulletin.

    Source: https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en
    Frequency: weekly (Monday), from 2005 to present.
    Coverage: all EU member states + EU weighted average (EU) + Eurozone average (EUR).
    Fuel types: Eurosuper 95, Diesel — both with and without taxes.
    Unit: EUR/litre.

    The XLSX has a wide layout: one repeating block of columns per country, each block
    containing a CTR (country-code) column followed by 6 fuel-type price columns.
    Prices in the source file are in EUR per 1000 litres and are converted to EUR/litre.
    """

    SUBFOLDER = "eu_fuel"

    _XLSX_URL = (
        "https://energy.ec.europa.eu/document/download/"
        "906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
        "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"
    )

    # Sheet name → price_type label
    _SHEETS: dict[str, str] = {
        "Prices with taxes": "with_tax",
        "Prices wo taxes": "without_tax",
    }

    # Column offset from the CTR column for each fuel type (constant across all country blocks)
    _FUEL_OFFSETS: dict[str, int] = {
        "GASOLINE_95": 1,
        "DIESEL": 2,
    }

    _COUNTRY_NAMES: dict[str, str] = {
        "EU": "European Union",
        "EUR": "Eurozone",
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

    def __init__(self) -> None:
        super().__init__()

    def _download_raw(self) -> bytes:
        req = urllib.request.Request(
            self._XLSX_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as response:
            return response.read()

    def _parse_sheet(
        self, raw: bytes, sheet_name: str, price_type: str
    ) -> pd.DataFrame:
        """Parse one price sheet (with or without taxes) into long format.

        The sheet has three header rows (rows 0-2) followed by weekly data rows.
        Column structure: col 0 = Date, then repeating [CTR, euro95, diesel, ...] blocks.
        CTR positions are identified by the value "CTR" in row 0.
        """
        df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet_name, header=None)

        # Row 0 contains the column identifiers; "CTR" marks each country block start
        header_row = df.iloc[0]
        ctr_positions = [i for i, v in enumerate(header_row) if str(v) == "CTR"]

        # Data rows begin at index 3; column 0 holds the week date
        dates = pd.to_datetime(df.iloc[3:, 0], errors="coerce")
        valid_mask = dates.notna()
        dates_clean = dates[valid_mask]

        parts = []
        for ctr_pos in ctr_positions:
            # Country code is identical across all data rows for this block
            raw_code = df.iloc[3, ctr_pos]
            if pd.isna(raw_code):
                continue
            country_code = str(raw_code).rstrip("_")
            if country_code not in self._COUNTRY_NAMES:
                continue

            for fuel_type, offset in self._FUEL_OFFSETS.items():
                prices = (
                    pd.to_numeric(
                        df.iloc[3:, ctr_pos + offset][valid_mask],
                        errors="coerce",
                    )
                    / 1000.0  # EUR/1000 L → EUR/L
                )
                chunk = pd.DataFrame(
                    {
                        "Date": dates_clean.values,
                        "price": prices.values,
                        "country_code": country_code,
                        "fuel_type": fuel_type,
                        "price_type": price_type,
                    }
                )
                parts.append(chunk)

        return pd.concat(parts, ignore_index=True)

    def fetch(self) -> pd.DataFrame:
        """Fetch weekly EU consumer fuel prices from the EC Weekly Oil Bulletin.

        Returns a DataFrame with columns:
            Date         — Monday of each reporting week (datetime, tz-naive)
            price        — consumer price in EUR/litre
            country      — full country name (e.g. 'Portugal')
            country_code — source code stripped of underscore (e.g. 'PT', 'EU', 'EUR')
            fuel_type    — 'GASOLINE_95' or 'DIESEL'
            price_type   — 'with_tax' or 'without_tax'
            identifier   — e.g. 'EU_FUEL_PT_GASOLINE_95_WITH_TAX'
        """
        logger.info("Fetching EU fuel prices from EC Weekly Oil Bulletin")
        raw = self._download_raw()
        logger.debug(f"Downloaded XLSX: {len(raw):,} bytes")

        parts = []
        for sheet_name, price_type in self._SHEETS.items():
            logger.info(f"Parsing sheet '{sheet_name}'")
            parts.append(self._parse_sheet(raw, sheet_name, price_type))

        df = pd.concat(parts, ignore_index=True)
        df = df.dropna(subset=["price"])

        df["country"] = df["country_code"].map(self._COUNTRY_NAMES)
        df["identifier"] = (
            "EU_FUEL_"
            + df["country_code"]
            + "_"
            + df["fuel_type"]
            + "_"
            + df["price_type"].str.upper()
        )

        if df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_convert(None)

        logger.info(
            f"Fetched {len(df):,} records | "
            f"{df['country_code'].nunique()} countries | "
            f"date range: {df['Date'].min().date()} → {df['Date'].max().date()}"
        )
        self._write_data(df)
        return df
