"""
Feature-specific fixtures for tests/features/ module.

These fixtures are automatically available to all tests in this folder
and its subfolders (pytest discovers conftest.py files automatically).
"""
import pytest
from stock_alert.features.moving_average import MovingAverage
from tests.conftest import COLUMN_NAME, SORT_COLUMN, IDENTIFIER_COLUMN


# MovingAverage-specific constants
WINDOW_3 = 3
WINDOW_21 = 21
WINDOW_50 = 50


@pytest.fixture
def ma_3day() -> MovingAverage:
    """3-day moving average fixture"""
    return MovingAverage(
        column=COLUMN_NAME,
        window_days=WINDOW_3,
        sort_by=SORT_COLUMN,
        group_by=IDENTIFIER_COLUMN,
    )


@pytest.fixture
def ma_21day() -> MovingAverage:
    """21-day moving average fixture"""
    return MovingAverage(
        column=COLUMN_NAME,
        window_days=WINDOW_21,
        sort_by=SORT_COLUMN,
        group_by=IDENTIFIER_COLUMN,
    )


@pytest.fixture
def ma_50day() -> MovingAverage:
    """50-day moving average fixture"""
    return MovingAverage(
        column=COLUMN_NAME,
        window_days=WINDOW_50,
        sort_by=SORT_COLUMN,
        group_by=IDENTIFIER_COLUMN,
    )