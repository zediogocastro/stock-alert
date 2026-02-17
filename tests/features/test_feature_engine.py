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
    
    @property
    def name(self) -> str:
        return self._name
    
    def compute(self, data: pl.LazyFrame) -> pl.LazyFrame:
        return data.with_columns(pl.lit(self.value).alias(self.output_col))


class TestFeatureEngineInit:
    """Test FeatureEngine initialization"""
    
    def test_init_with_features(self):
        """Can initialize with a list of features"""
        f1 = MockFeature("f1", "col1")
        f2 = MockFeature("f2", "col2")
        
        engine = FeatureEngine([f1, f2])
        
        assert len(engine.features) == 2
        assert engine.features[0] is f1
        assert engine.features[1] is f2
    
    def test_init_requires_at_least_one_feature(self):
        """FeatureEngine raises ValueError if no features provided"""
        with pytest.raises(ValueError, match="FeatureEngine requires at least one feature"):
            FeatureEngine([])


class TestFeatureEngineTransform:
    """Test transform with different input types"""
    
    def test_transform_dataframe(self):
        """transform() accepts DataFrame and returns DataFrame"""
        features: list[Feature] = [MockFeature("f1", "new_col", value=42.0)]
        engine = FeatureEngine(features)
        
        data = pl.DataFrame({"input": [1, 2, 3]})
        result = engine.transform(data)
        
        assert isinstance(result, pl.DataFrame)
        assert "new_col" in result.columns
        assert result["new_col"].to_list() == [42.0, 42.0, 42.0]



class TestFeatureEngineEdgeCases:
    """Test edge cases"""
    
    def test_empty_dataframe(self):
        """FeatureEngine handles empty dataframes"""
        f = MockFeature("test", "col")
        engine = FeatureEngine([f])
        
        data = pl.DataFrame({"input": pl.Series([], dtype=pl.Int64)})
        result = engine.transform(data)
        
        assert result.shape[0] == 0
        assert "col" in result.columns
    
    def test_preserves_original_columns(self):
        """Original columns are preserved after transform"""
        f = MockFeature("f1", "new_col")
        engine = FeatureEngine([f])
        
        data = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = engine.transform(data)
        
        assert result["a"].to_list() == [1, 2]
        assert result["b"].to_list() == [3, 4]

