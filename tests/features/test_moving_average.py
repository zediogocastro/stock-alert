"""
Tests for MovingAverage feature.
"""
import pytest
import polars as pl
from datetime import date

from tests.conftest import COLUMN_NAME, IDENTIFIER_COLUMN, SORT_COLUMN
from stock_alert.features.moving_average import MovingAverage


class TestMovingAverageName:
    """Test feature name generation"""
    
    def test_generates_correct_name(self, ma_3day: MovingAverage):
        """Feature name includes window size"""
        assert ma_3day.name == "sma_3d"
    
    def test_different_windows_have_different_names(self):
        """Different window sizes produce different names"""
        ma5 = MovingAverage(column="Close", window_days=5, sort_by_column="Date")
        ma50 = MovingAverage(column="Close", window_days=50, sort_by_column="Date")
        
        assert ma5.name == "sma_5d"
        assert ma50.name == "sma_50d"


class TestMovingAverageComputation:
    """Test SMA calculation correctness"""
    
    def test_calculates_mean_correctly(self, ma_3day: MovingAverage, simple_price_data: pl.LazyFrame):
        """SMA values are mathematically correct"""
        result = ma_3day.compute(simple_price_data).collect()
        
        assert result["sma_3d"][2] == pytest.approx(102.0)
        assert result["sma_3d"][3] == pytest.approx(103.0)
    
    def test_preserves_original_columns(self, ma_3day: MovingAverage, simple_price_data: pl.LazyFrame):
        """Original data columns remain unchanged"""
        original = simple_price_data.collect()
        result = ma_3day.compute(simple_price_data).collect()
        
        assert result[COLUMN_NAME].to_list() == original[COLUMN_NAME].to_list()

class TestGroupBy:
    """Test grouped operations"""
    
    def test_computes_independently_per_group(self, ma_3day: MovingAverage, grouped_price_data: pl.LazyFrame):
        """With group_by, each group has independent SMA"""
        result = ma_3day.compute(grouped_price_data, group_by=IDENTIFIER_COLUMN).collect()
        
        aapl = result.filter(pl.col(IDENTIFIER_COLUMN) == "AAPL")
        msft = result.filter(pl.col(IDENTIFIER_COLUMN) == "MSFT")
        
        assert aapl["sma_3d"][2] == pytest.approx(102.0)
        assert msft["sma_3d"][2] == pytest.approx(200.0)


class TestSortingBehavior:
    """Test data sorting and ordering"""
    
    def test_sorts_data_before_computing(self):
        """Unsorted data is sorted before SMA calculation"""
        unsorted = pl.LazyFrame({
            SORT_COLUMN: [
                date(2024, 1, 3), 
                date(2024, 1, 1), 
                date(2024, 1, 2)],
            "Close": [104.0, 100.0, 102.0],
        })
        
        feature = MovingAverage(column="Close", window_days=2, sort_by_column=SORT_COLUMN)
        result = feature.compute(unsorted).collect()
        
        assert result["sma_2d"][1] == pytest.approx(101.0)


class TestErrorHandling:
    """Test error cases"""
    
    def test_invalid_sort_column_raises_error(self, ma_3day: MovingAverage, simple_price_data: pl.LazyFrame):
        """Missing sort column raises error"""
        bad_feature = MovingAverage(column="Close", window_days=3, sort_by_column="InvalidColumn")
        
        with pytest.raises(pl.exceptions.ColumnNotFoundError):
            bad_feature.compute(simple_price_data).collect()

    def test_invalid_data_column_raises_error(self, simple_price_data: pl.LazyFrame):
        """Missing data column raises error"""
        bad_feature = MovingAverage(column="InvalidColumn", window_days=3, sort_by_column=SORT_COLUMN)
        
        with pytest.raises(pl.exceptions.ColumnNotFoundError):
            bad_feature.compute(simple_price_data).collect()