from .fetchers import (
    BaseFetcher,
    EUFuelFetcher,
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
    "YFinanceFetcher",
    "EuriborFetcher",
    "OilFetcher",
    "Feature",
    "FeatureEngine",
    "MovingAverage",
    "FetcherService",
    "FeatureService",
]
