import pytest
from unittest.mock import patch, MagicMock
from stock_alert.fetchers import EuriborFetcher


def _make_mock_response(csv_content: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = csv_content
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


_ECB_CSV = (
    "TIME_PERIOD,OBS_VALUE,PROVIDER_FM_ID\n"
    "2025-01,3.25,EURIBOR3MD_\n"
    "2025-02,3.10,EURIBOR3MD_\n"
    "2025-01,3.50,EURIBOR1YD_\n"
).encode()


def test_euribor_fetcher_invalid_tenor():
    with pytest.raises(ValueError, match="Invalid tenors"):
        EuriborFetcher(tenors=["99Y"])


def test_euribor_fetcher_defaults_to_all_tenors():
    fetcher = EuriborFetcher()
    assert sorted(fetcher.tenors) == ["12M", "1M", "3M", "6M"]


@patch("stock_alert.fetchers.euribor.urllib.request.urlopen")
def test_euribor_fetcher_parses_ecb_response(mock_urlopen, tmp_path):
    mock_urlopen.return_value = _make_mock_response(_ECB_CSV)

    fetcher = EuriborFetcher(tenors=["3M", "12M"])
    fetcher.cache_dir = str(tmp_path)
    df = fetcher.fetch()

    assert set(df.columns) == {"Date", "rate", "tenor", "identifier"}
    assert len(df) == 3
    assert set(df["tenor"]) == {"3M", "12M"}
    assert set(df["identifier"]) == {"EURIBOR_3M", "EURIBOR_12M"}
    assert df["Date"].dt.day.eq(1).all()
    assert (tmp_path / "euribor" / "data.parquet").exists()
