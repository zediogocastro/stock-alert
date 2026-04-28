import json
import pandas as pd
from unittest.mock import patch, MagicMock

from stock_alert.fetchers import INEPortugalFetcher


# ── Fixture: minimal valid INE API response ───────────────────────────────────
_INE_RESPONSE = json.dumps(
    [
        {
            "IndicadorCod": "0014647",
            "IndicadorDsg": "Consumer price index (Year-on-year growth rate - Base 2025 - %)",
            "DataExtracao": "2026-04-13T00:00:00.000+01:00",
            "DataUltimoAtualizacao": "2026-04-13",
            "UltimoPref": "March 2026",
            "Dados": {
                "March 2026": [
                    # Portugal rows (geocod="PT")
                    {
                        "geocod": "PT",
                        "geodsg": "Portugal",
                        "dim_3": "T",
                        "dim_3_t": "Total",
                        "ind_string": "2,71",
                        "valor": "2.71",
                    },
                    {
                        "geocod": "PT",
                        "geodsg": "Portugal",
                        "dim_3": "01",
                        "dim_3_t": "Food and non-alcoholic beverages",
                        "ind_string": "3,65",
                        "valor": "3.65",
                    },
                    {
                        "geocod": "PT",
                        "geodsg": "Portugal",
                        "dim_3": "07",
                        "dim_3_t": "Transport",
                        "ind_string": "3,78",
                        "valor": "3.78",
                    },
                    # Row marked "not available" — must be excluded
                    {
                        "geocod": "PT",
                        "geodsg": "Portugal",
                        "dim_3": "0412",
                        "dim_3_t": "Other actual rental payments",
                        "sinal_conv": "x",
                        "sinal_conv_desc": "Not available",
                        "ind_string": "x",
                    },
                    # Continent row — must be excluded (geocod != "PT")
                    {
                        "geocod": "1",
                        "geodsg": "Continent",
                        "dim_3": "T",
                        "dim_3_t": "Total",
                        "ind_string": "2,71",
                        "valor": "2.71",
                    },
                ]
            },
            "Sucesso": {"Verdadeiro": [{"Msg": "OK"}]},
        }
    ]
).encode()


def _make_mock_urlopen(response_bytes: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_output_schema(mock_urlopen, tmp_path):
    """fetch() must return a DataFrame with the documented columns and correct dtypes."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df.columns) == {"Date", "coicop_code", "category_en", "rate_yoy", "source"}
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert pd.api.types.is_float_dtype(df["rate_yoy"])


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_total_row_present(mock_urlopen, tmp_path):
    """The output must contain a row with coicop_code='T' (Total CPI)."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    total = df[df["coicop_code"] == "T"]
    assert not total.empty, "Expected a 'T' (Total) row"
    assert abs(total.iloc[0]["rate_yoy"] - 2.71) < 0.01


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_not_available_rows_excluded(mock_urlopen, tmp_path):
    """Rows marked sinal_conv='x' (not available) must not appear in the output."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert df["rate_yoy"].isna().sum() == 0
    assert "0412" not in df["coicop_code"].values, "Not-available row should be excluded"


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_continent_rows_excluded(mock_urlopen, tmp_path):
    """Rows with geocod='1' (Continent) must not appear — only geocod='PT'."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    # If continent rows leaked in, we'd have duplicates on (Date, coicop_code="T")
    total_rows = df[df["coicop_code"] == "T"]
    assert len(total_rows) == 1, "Exactly one Total row expected (PT only, not Continent)"


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_date_is_first_of_month(mock_urlopen, tmp_path):
    """Date column must be datetime with day=1 (first of the reference month)."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert (df["Date"].dt.day == 1).all(), "All dates must be first day of month"
    assert (df["Date"].dt.month == 3).all()   # March
    assert (df["Date"].dt.year == 2026).all()


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_source_column(mock_urlopen, tmp_path):
    """source column must always be 'INE'."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert (df["source"] == "INE").all()


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_parquet_written(mock_urlopen, tmp_path):
    """fetch() must write data.parquet to cache_dir/portugal_cpi/."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)

    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    fetcher.fetch()

    parquet_path = tmp_path / "portugal_cpi" / "data.parquet"
    assert parquet_path.exists(), "data.parquet must be written after fetch()"


@patch("stock_alert.fetchers.portugal_cpi.urllib.request.urlopen")
def test_append_deduplicates(mock_urlopen, tmp_path):
    """Running fetch() twice must not duplicate rows for the same period."""
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)
    fetcher = INEPortugalFetcher()
    fetcher.cache_dir = str(tmp_path)
    fetcher.fetch()

    # Second call — same data
    mock_urlopen.side_effect = _make_mock_urlopen(_INE_RESPONSE)
    fetcher.fetch()

    parquet = pd.read_parquet(tmp_path / "portugal_cpi" / "data.parquet")
    total_rows = parquet[parquet["coicop_code"] == "T"]
    assert len(total_rows) == 1, "Duplicate rows must be deduplicated after second fetch"
