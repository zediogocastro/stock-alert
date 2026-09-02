from .fetchers import (
    BaseFetcher,
    EUFuelFetcher,
    InflationFetcher,
    YFinanceFetcher,
    EuriborFetcher,
    OilFetcher,
)
from .features import Feature, FeatureEngine, MovingAverage
from .pipeline import FetcherService, FeatureService

__version__ = "0.1.0"

__all__ = [
    "BaseFetcher",
    "EUFuelFetcher",
    "InflationFetcher",
    "YFinanceFetcher",
    "EuriborFetcher",
    "OilFetcher",
    "Feature",
    "FeatureEngine",
    "MovingAverage",
    "FetcherService",
    "FeatureService",
]
