"""
Tests for FeatureEngine class.
"""
import pytest
import polars as pl
from unittest.mock import Mock

from stock_alert.features.base import Feature, FeatureEngine


class MockFeature(Feature):
    """Mock feature for testing"""
    
    def __init__(self, name: str, output_col: str, value: float = 1.0):
        self._name = name
        self.output_col = output_col
        self.value = value
        self.compute_group_by = None
    
    @property
    def name(self) -> str:
        return self._name
    
    def compute(self, data: pl.LazyFrame, group_by: str | None = None) -> pl.LazyFrame:
        self.compute_group_by = group_by
        return data.with_columns(pl.lit(self.value).alias(self.output_col))


class TestFeatureEngineAdd:
    """Test adding features and fluent interface"""
    
    def test_add_features_and_chain(self):
        """Can add multiple features with fluent interface"""
        engine = FeatureEngine()
        f1 = MockFeature("f1", "col1")
        f2 = MockFeature("f2", "col2")
        
        result = engine.add(f1).add(f2)
        
        assert len(engine.features) == 2
        assert result is engine


class TestFeatureEngineTransform:
    """Test transform with different input types"""
    
    def test_transform_dataframe(self):
        """transform() accepts DataFrame and returns DataFrame"""
        engine = FeatureEngine()
        engine.add(MockFeature("f1", "new_col", value=42.0))
        
        data = pl.DataFrame({"input": [1, 2, 3]})
        result = engine.transform(data)
        
        assert isinstance(result, pl.DataFrame)
        assert "new_col" in result.columns
        assert result["new_col"].to_list() == [42.0, 42.0, 42.0]
    
    def test_transform_empty_engine(self):
        """transform() with no features just returns data"""
        engine = FeatureEngine()
        data = pl.DataFrame({"col": [1, 2, 3]})
        
        result = engine.transform(data)
        
        assert result.to_dict(as_series=False) == {"col": [1, 2, 3]}


class TestFeatureEngineGroupBy:
    """Test group_by propagation"""
    
    def test_group_by_passed_to_all_features(self):
        """group_by parameter is passed to each feature"""
        engine = FeatureEngine(group_by="symbol")
        f1 = MockFeature("f1", "col1")
        f2 = MockFeature("f2", "col2")
        
        engine.add(f1).add(f2)
        data = pl.DataFrame({"symbol": ["A", "B"], "value": [1, 2]})
        engine.transform(data)
        
        assert f1.compute_group_by == "symbol"
        assert f2.compute_group_by == "symbol"
    
    def test_group_by_none_by_default(self):
        """group_by is None when not specified"""
        engine = FeatureEngine()
        feature = MockFeature("test", "col")
        engine.add(feature)
        
        data = pl.DataFrame({"x": [1]})
        engine.transform(data)
        
        assert feature.compute_group_by is None


class TestFeatureEngineEdgeCases:
    """Test edge cases"""
    
    def test_empty_dataframe(self):
        """FeatureEngine handles empty dataframes"""
        engine = FeatureEngine()
        engine.add(MockFeature("test", "col"))
        
        data = pl.DataFrame({"input": pl.Series([], dtype=pl.Int64)})
        result = engine.transform(data)
        
        assert result.shape[0] == 0
        assert "col" in result.columns
    
    def test_preserves_original_columns(self):
        """Original columns are preserved after transform"""
        engine = FeatureEngine()
        engine.add(MockFeature("f1", "new_col"))
        
        data = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = engine.transform(data)
        
        assert result["a"].to_list() == [1, 2]
        assert result["b"].to_list() == [3, 4]

