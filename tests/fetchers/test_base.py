import pandas as pd
import pytest
from stock_alert.fetchers import BaseFetcher


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
