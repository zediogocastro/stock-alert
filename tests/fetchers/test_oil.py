import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from stock_alert.fetchers import OilFetcher


def _make_oil_history(tz=None) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=3, name="Date", tz=tz)
    return pd.DataFrame(
        {"Open": [75.0, 76.0, 77.0], "Close": [76.0, 77.0, 78.0], "Volume": [100, 110, 120]},
        index=idx,
    )


def test_oil_fetcher_invalid_benchmark():
    with pytest.raises(ValueError, match="Invalid benchmarks"):
        OilFetcher(benchmarks=["OPEC"])


def test_oil_fetcher_defaults_to_all_benchmarks():
    fetcher = OilFetcher()
    assert sorted(fetcher.benchmarks) == ["BRENT", "WTI"]


@patch("stock_alert.fetchers.oil.yf.Ticker")
def test_oil_fetcher_combines_benchmarks(mock_ticker_cls, tmp_path):
    mock_ticker_cls.return_value = MagicMock(
        history=MagicMock(side_effect=lambda **kw: _make_oil_history())
    )

    fetcher = OilFetcher(benchmarks=["BRENT", "WTI"], period="1y")
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df["benchmark"].unique()) == {"BRENT", "WTI"}
    assert set(df["identifier"].unique()) == {"OIL_BRENT", "OIL_WTI"}
    assert len(df) == 6  # 3 rows × 2 benchmarks
    assert (tmp_path / "oil" / "data.parquet").exists()


@patch("stock_alert.fetchers.oil.yf.Ticker")
def test_oil_fetcher_raises_when_all_fail(mock_ticker_cls):
    mock_ticker_cls.return_value = MagicMock(
        history=MagicMock(side_effect=RuntimeError("API down"))
    )

    fetcher = OilFetcher()
    with pytest.raises(ValueError, match="No data fetched"):
        fetcher.fetch()


@patch("stock_alert.fetchers.oil.yf.Ticker")
def test_oil_fetcher_strips_timezone(mock_ticker_cls, tmp_path):
    mock_ticker_cls.return_value = MagicMock(
        history=MagicMock(side_effect=lambda **kw: _make_oil_history(tz="America/New_York"))
    )

    fetcher = OilFetcher(benchmarks=["BRENT"], period="1y")
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert df["Date"].dt.tz is None
