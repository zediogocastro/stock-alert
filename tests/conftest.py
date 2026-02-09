"""
Shared fixtures for all tests.

- Fixtures defined here are automatically available to ALL test files
- No need to import them - pytest discovers them automatically
- Great for common test data used across multiple test modules
"""
import pytest
import polars as pl

COLUMN_NAME = "Column_A"
IDENTIFIER_COLUMN = "identifier"
SORT_COLUMN = "Date"

@pytest.fixture
def simple_price_data() -> pl.LazyFrame:
    """Simple price series for basic feature tests"""
    return pl.LazyFrame({
        SORT_COLUMN: pl.date_range(pl.date(2024, 1, 1), pl.date(2024, 1, 10), eager=True),
        COLUMN_NAME: [100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0, 110.0, 109.0],
    })


@pytest.fixture
def grouped_price_data() -> pl.LazyFrame:
    """Multi-stock data for testing grouped operations"""
    return pl.LazyFrame({
        SORT_COLUMN: pl.date_range(pl.date(2024, 1, 1), pl.date(2024, 1, 5), eager=True).to_list() * 2,
        IDENTIFIER_COLUMN: ["AAPL"] * 5 + ["MSFT"] * 5,
        COLUMN_NAME: [
            # AAPL: steady increase
            100.0, 102.0, 104.0, 106.0, 108.0,
            # MSFT: different pattern
            200.0, 198.0, 202.0, 204.0, 200.0,
        ],
    })


@pytest.fixture
def empty_price_data() -> pl.LazyFrame:
    """Empty dataframe for edge case testing"""
    return pl.LazyFrame({"Close": pl.Series([], dtype=pl.Float64)})


@pytest.fixture
def single_row_data() -> pl.LazyFrame:
    """Single row for edge case testing"""
    return pl.LazyFrame({"Close": [100.0]})