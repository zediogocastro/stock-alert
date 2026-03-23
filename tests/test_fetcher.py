import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from stock_alert.fetchers import BaseFetcher, YFinanceFetcher, EuriborFetcher


# ── BaseFetcher ──────────────────────────────────────────────

class DummyFetcher(BaseFetcher):
    SUBFOLDER = "dummy"

    def fetch(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1, 2, 3]})


def test_base_fetcher_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseFetcher()


def test_base_fetcher_write_data_creates_parquet(tmp_path):
    fetcher = DummyFetcher(cache_dir=str(tmp_path))
    df = fetcher.fetch()
    fetcher._write_data(df)

    expected_path = tmp_path / "dummy" / "data.parquet"
    assert expected_path.exists()

    saved = pd.read_parquet(expected_path)
    pd.testing.assert_frame_equal(saved, df)


def test_base_fetcher_defaults_to_base_cache_dir():
    fetcher = DummyFetcher()
    assert fetcher.cache_dir == BaseFetcher.BASE_CACHE_DIR


# ── YFinanceFetcher ──────────────────────────────────────────

@patch("stock_alert.fetchers.yfinance.yf.Ticker")
def test_yfinance_fetcher_combines_identifiers(mock_ticker_cls, tmp_path):
    mock_history = pd.DataFrame({
        "Close": [100.0, 101.0],
        "Volume": [1000, 1100],
    }, index=pd.date_range("2025-01-01", periods=2))

    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = lambda **kw: mock_history.copy()
    mock_ticker_cls.return_value = mock_ticker

    fetcher = YFinanceFetcher(identifiers=["AAPL", "MSFT"], period="1y")
    fetcher.cache_dir = str(tmp_path)
    result = fetcher.fetch()

    assert "identifier" in result.columns
    assert set(result["identifier"].unique()) == {"AAPL", "MSFT"}
    assert len(result) == 4  # 2 rows × 2 tickers
    assert (tmp_path / "stocks" / "data.parquet").exists()


@patch("stock_alert.fetchers.yfinance.yf.Ticker")
def test_yfinance_fetcher_raises_when_all_fail(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = RuntimeError("API down")
    mock_ticker_cls.return_value = mock_ticker

    fetcher = YFinanceFetcher(identifiers=["BAD"], period="1y")
    with pytest.raises(ValueError, match="No data"):
        fetcher.fetch()


# ── EuriborFetcher ───────────────────────────────────────────

def test_euribor_fetcher_invalid_tenor():
    with pytest.raises(ValueError, match="Invalid tenors"):
        EuriborFetcher(tenors=["99Y"])


def test_euribor_fetcher_defaults_to_all_tenors():
    fetcher = EuriborFetcher()
    assert sorted(fetcher.tenors) == ["12M", "1M", "3M", "6M"]


def _make_mock_urlopen(csv_content: bytes):
    mock_response = MagicMock()
    mock_response.read.return_value = csv_content
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


@patch("stock_alert.fetchers.euribor.urllib.request.urlopen")
def test_euribor_fetcher_parses_ecb_response(mock_urlopen, tmp_path):
    csv_content = (
        "TIME_PERIOD,OBS_VALUE,PROVIDER_FM_ID\n"
        "2025-01,3.25,EURIBOR3MD_\n"
        "2025-02,3.10,EURIBOR3MD_\n"
        "2025-01,3.50,EURIBOR1YD_\n"
    ).encode()
    mock_urlopen.return_value = _make_mock_urlopen(csv_content)

    fetcher = EuriborFetcher(tenors=["3M", "12M"])
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df.columns) == {"Date", "rate", "tenor", "identifier"}
    assert len(df) == 3
    assert set(df["tenor"]) == {"3M", "12M"}
    assert set(df["identifier"]) == {"EURIBOR_3M", "EURIBOR_12M"}
    assert df["Date"].dt.day.eq(1).all()  # monthly dates parsed to first of month
    assert (tmp_path / "euribor" / "data.parquet").exists()
