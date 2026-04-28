import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from stock_alert.fetchers import YFinanceFetcher


def _make_mock_ticker(history: pd.DataFrame) -> MagicMock:
    mock = MagicMock()
    mock.history.side_effect = lambda **kw: history.copy()
    return mock


_MOCK_HISTORY = pd.DataFrame(
    {"Close": [100.0, 101.0], "Volume": [1000, 1100]},
    index=pd.date_range("2025-01-01", periods=2),
)


@patch("stock_alert.fetchers.yfinance.yf.Ticker")
def test_yfinance_fetcher_combines_identifiers(mock_ticker_cls, tmp_path):
    mock_ticker_cls.return_value = _make_mock_ticker(_MOCK_HISTORY)

    fetcher = YFinanceFetcher(identifiers=["AAPL", "MSFT"], period="1y")
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert "identifier" in df.columns
    assert set(df["identifier"].unique()) == {"AAPL", "MSFT"}
    assert len(df) == 4  # 2 rows × 2 tickers
    assert (tmp_path / "stocks" / "data.parquet").exists()


@patch("stock_alert.fetchers.yfinance.yf.Ticker")
def test_yfinance_fetcher_raises_when_all_fail(mock_ticker_cls):
    mock_ticker_cls.return_value = MagicMock(
        history=MagicMock(side_effect=RuntimeError("API down"))
    )

    fetcher = YFinanceFetcher(identifiers=["BAD"], period="1y")
    with pytest.raises(ValueError, match="No data"):
        fetcher.fetch()
