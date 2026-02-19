import polars as pl
import pytest
from datetime import date
from polars.testing import assert_series_equal
from stock_alert.features.atomic_features import Returns

@pytest.fixture
def sample_data():
    return pl.DataFrame({
        "date": pl.date_range(
            start=date(2026, 1, 1), 
            end=date(2026, 1, 5),    
            interval="1d",
            eager=True
        ),  
        "price": [100.0, 110.0, 121.0, 110.0, 100.0],
        "symbol": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"]
    })

def test_returns(sample_data):
    # 1-day returns: (110/100)-1 = 0.1
    feature = Returns(column="price", n_days=1, sort_by="date", group_by="symbol")
    result = sample_data.select(feature.compute()).to_series()
    
    # Expected: [Null, 0.1, 0.1, -0.0909..., -0.0909...]
    assert result[0] is None, "First value should be None (no prior price)"
    assert result[1] == pytest.approx(0.1, abs=1e-6)
    assert result[2] == pytest.approx(0.1, abs=1e-6)
    assert result[3] == pytest.approx(-0.0909, abs=1e-3)
    assert result[4] == pytest.approx(-0.0909, abs=1e-3)