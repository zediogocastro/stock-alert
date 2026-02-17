from abc import ABC, abstractmethod
import polars as pl
from common.logger import logger


class Feature(ABC):
    """Base class for all feature generators"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the output column"""
        pass
    
    @abstractmethod
    def compute(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """Add the feature column to the LazyFrame and return it
        
        Args:
            data: Input LazyFrame
            group_by: Optional column to group by before computing
        
        Returns:
            LazyFrame with new feature column added
        """
        pass


class FeatureEngine:
    """Composes multiple features with efficient Polars execution"""
    
    def __init__(self, features: list[Feature]) -> None:
        """
        Args:
            features: List of Features to be applied
        """
        if not features:
            raise ValueError("FeatureEngine requires at least one feature")
        self.features = features

    
    def transform(self, data: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
        """Apply all features in order"""
        lf = data.lazy() if isinstance(data, pl.DataFrame) else data

        # TODO take out from feature the responsability of adding to master table, 
        # just return the series
        for feature in self.features:
            lf = feature.compute(lf)
        
        logger.info(f"Applied {len(self.features)} features")
        return lf.collect()