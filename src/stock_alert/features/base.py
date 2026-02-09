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
    def compute(self, data: pl.LazyFrame, group_by: str | None = None) -> pl.LazyFrame:
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
    
    def __init__(self, group_by: str | None = None) -> None:
        """
        Args:
            group_by: Optional column to group by (applied to all features)
        """
        self.features: list[Feature] = []
        self.group_by = group_by
    
    def add(self, feature: Feature) -> "FeatureEngine":
        """Add a feature (fluent interface)"""
        self.features.append(feature)
        return self
    
    def transform(self, data: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
        """Apply all features in order"""
        lf = data.lazy() if isinstance(data, pl.DataFrame) else data
        
        for feature in self.features:
            lf = feature.compute(lf, self.group_by)
        
        logger.info(f"Applied {len(self.features)} features")
        return lf.collect()