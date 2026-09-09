import json
import ssl
import time
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

    _MAX_ATTEMPTS = 4
    _RETRY_DELAY_SECONDS = 2

    def _fetch_payload(self) -> list:
        """Fetch and parse the INE JSON payload, retrying on transient empty responses.

        The INE BDportal API occasionally responds with HTTP 200 and an empty body
        (no data) on the first request of a session, before the server-side session
        cookie is established. Retrying with a fresh request reliably succeeds.
        """
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        last_error: Exception | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            req = urllib.request.Request(
                self._INE_URL,
                headers={"Accept": "application/json", "User-Agent": "stock-alert/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
                body = response.read()

            if not body:
                last_error = ValueError("INE API returned an empty response body")
                logger.warning(
                    f"Attempt {attempt}/{self._MAX_ATTEMPTS} got an empty response "
                    "from INE API, retrying..."
                )
                if attempt < self._MAX_ATTEMPTS:
                    time.sleep(self._RETRY_DELAY_SECONDS)
                continue

            try:
                return json.loads(body)
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt}/{self._MAX_ATTEMPTS} got invalid JSON from "
                    f"INE API, retrying... ({e})"
                )
                if attempt < self._MAX_ATTEMPTS:
                    time.sleep(self._RETRY_DELAY_SECONDS)

        raise RuntimeError(
            f"INE API did not return a valid response after {self._MAX_ATTEMPTS} attempts"
        ) from last_error

    def fetch(self) -> pd.DataFrame:
        """Fetch the latest Portugal CPI data from INE and append it to the parquet store.

        Returns the newly fetched rows (the current period only). The parquet store
        receives the full deduplicated history (existing + new).
        """
        logger.info("Fetching Portugal CPI data from INE BDportal API")

        payload = self._fetch_payload()

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
