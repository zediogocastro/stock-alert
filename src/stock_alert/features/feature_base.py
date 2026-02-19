from abc import ABC, abstractmethod
from collections.abc import Sequence
import polars as pl
from common.logger import logger


class Feature(ABC):
    """Abstract base class for feature generators
    
    All concrete feature implementations must inherit from this class and 
    implement the required abstract methods. Features are designed to be 
    composable and chainable within a FeatureEngine.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the generated feature.
        
        Returns:
            str: Name of the generated feture.
        """
        pass
    
    @abstractmethod
    def compute(self) -> pl.Expr:
        """Returns the Polars expression for this feature."""
        pass


class FeatureEngine:
    """Orchestrates the composition and execution of multiple features.
    
    Attributes:
        features: Non-empty sequence of Feature objects to compose.
    """
    
    def __init__(self, features: Sequence[Feature]) -> None:
        if not features:
            raise ValueError("FeatureEngine requires at least one feature")
        self.features = features

    
    def transform(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """Applies all features in a single optimized batch."""
        # Create the expressions from the features
        exprs = [f.compute() for f in self.features]
        # Polars executes all of these in parallel 
        data = data.with_columns(exprs)
        
        logger.info(f"Applied {len(self.features)} features successfully")
        return data