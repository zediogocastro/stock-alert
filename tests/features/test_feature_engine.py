# tests/features/test_feature_engine.py
import polars as pl
from stock_alert.features.feature_base import FeatureEngine
from stock_alert.features.moving_average import MovingAverage

def test_feature_engine_adds_multiple_columns():
    # Setup
    df = pl.LazyFrame({
        "date": [1, 2, 3],
        "price": [10.0, 20.0, 30.0]
    })
    
    # Create two different features
    features = [
        MovingAverage(column="price", window_days=2, sort_by="date"),
        MovingAverage(column="price", window_days=3, sort_by="date")
    ]
    
    engine = FeatureEngine(features)
    
    # Transform
    result_df = engine.transform(df).collect()
    
    # Check if both columns exist
    assert "sma_2d" in result_df.columns
    assert "sma_3d" in result_df.columns
    # Check if original columns are preserved
    assert "price" in result_df.columns 
    
    # Quick value check for the 2d SMA
    assert result_df["sma_2d"][1] == 15.0