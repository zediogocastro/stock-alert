import polars as pl
from polars.testing import assert_series_equal
from stock_alert.features.moving_average import MovingAverage, MovingAverageSpread


def test_moving_average_calculation():
    # Simple Data
    df = pl.DataFrame({"date": [1, 2, 3, 4], "values": [10.0, 20.0, 30.0, 40.0]})

    # Init feature: 2-day window
    sma = MovingAverage(column="values", window_days=2, sort_by="date")

    # Execute: Apply just the expression
    # Resulting column should be [null, 15.0, 25.0, 35.0]
    result = df.select(sma.compute()).to_series()

    excepted = pl.Series("sma_2d", [None, 15.0, 25.0, 35.0])

    assert_series_equal(result, excepted)


def test_moving_average_with_groups():
    # Setup: Data with two different stocks/groups
    df = pl.DataFrame(
        {
            "stock": ["A", "A", "B", "B"],
            "date": [1, 2, 1, 2],
            "price": [10.0, 20.0, 100.0, 200.0],
        }
    )

    sma = MovingAverage(column="price", window_days=2, sort_by="date", group_by="stock")

    # If grouping works, the SMA of B shouldn't be affected by A
    result = df.select(sma.compute()).to_series()

    expected = pl.Series("sma_2d", [None, 15.0, None, 150.0])

    assert_series_equal(result, expected)


def test_moving_average_spread():
    df = pl.DataFrame({"date": [1, 2, 3, 4], "price": [10.0, 20.0, 30.0, 40.0]})

    # fast (window=1) is the price itself: [10, 20, 30, 40]
    # slow (window=2): [None, 15, 25, 35]
    spread = MovingAverageSpread(
        column="price", fast_window=1, slow_window=2, sort_by="date"
    )
    result = df.select(spread.compute()).to_series()

    expected = pl.Series("sma_gap_1_2d", [None, 5.0, 5.0, 5.0])
    assert_series_equal(result, expected)
