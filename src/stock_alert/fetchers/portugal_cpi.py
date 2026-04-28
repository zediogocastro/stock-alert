import json
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

import certifi
import pandas as pd
from common.logger import logger

from .base import BaseFetcher


class INEPortugalFetcher(BaseFetcher):
    """Fetcher for Portugal Consumer Price Index (CPI) data from Statistics Portugal (INE).

    Data source: INE BDportal JSON API, indicator 0014647.
    URL: https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0014647&lang=EN

    The API returns CPI year-on-year growth rates (%) by Individual Consumption by Purpose
    (COICOP classification, base 2025) for Portugal. Each call returns only the latest
    published month; data accumulates over time via repeated fetches.

    Output schema:
        Date          — first day of the reference month (datetime)
        coicop_code   — COICOP classification code (str), e.g. "T" (total), "01" (food)
        category_en   — English description of the COICOP category (str)
        rate_yoy      — CPI year-on-year growth rate in % (float)
        source        — always "INE" (str)
    """

    SUBFOLDER = "portugal_cpi"

    _INE_URL = (
        "https://www.ine.pt/ine/json_indicador/pindica.jsp"
        "?op=2&varcd=0014647&lang=EN"
    )

    def fetch(self) -> pd.DataFrame:
        """Fetch the latest Portugal CPI data from INE and append it to the parquet store.

        Returns the newly fetched rows (the current period only). The parquet store
        receives the full deduplicated history (existing + new).
        """
        logger.info("Fetching Portugal CPI data from INE BDportal API")

        req = urllib.request.Request(
            self._INE_URL,
            headers={"Accept": "application/json", "User-Agent": "stock-alert/1.0"},
        )
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
            payload = json.loads(response.read())

        indicator = payload[0]
        dados = indicator.get("Dados", {})

        if not dados:
            raise ValueError("INE API returned no data in 'Dados' field")

        rows = []
        for period_str, entries in dados.items():
            try:
                date = datetime.strptime(period_str.strip(), "%B %Y").replace(day=1)
            except ValueError:
                logger.warning(f"Could not parse period string: {period_str!r}, skipping")
                continue

            for entry in entries:
                if entry.get("geocod") != "PT":
                    continue
                if "valor" not in entry:
                    # sinal_conv="x" means not available — no "valor" key present
                    continue
                rows.append(
                    {
                        "Date": date,
                        "coicop_code": str(entry["dim_3"]),
                        "category_en": entry["dim_3_t"],
                        "rate_yoy": float(entry["valor"]),
                        "source": "INE",
                    }
                )

        if not rows:
            raise ValueError("INE API returned no valid PT rows for any period")

        new_df = pd.DataFrame(rows)
        new_df["Date"] = pd.to_datetime(new_df["Date"])

        logger.info(
            f"Fetched {len(new_df)} INE CPI rows for period(s): "
            f"{sorted(new_df['Date'].dt.strftime('%b %Y').unique())}"
        )

        # ── Append to existing parquet (accumulate history) ───────────────────
        save_path = Path(self.cache_dir) / self.SUBFOLDER / "data.parquet"
        if save_path.exists():
            existing = pd.read_parquet(save_path)
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(
                subset=["Date", "coicop_code"], keep="last"
            ).reset_index(drop=True)
        else:
            combined = new_df

        self._write_data(combined)

        return new_df
