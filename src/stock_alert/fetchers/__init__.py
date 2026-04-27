from .base import BaseFetcher
from .eu_fuel import EUFuelFetcher
from .euribor import EuriborFetcher
from .oil import OilFetcher
from .yfinance import YFinanceFetcher

__all__ = [
    "BaseFetcher",
    "EUFuelFetcher",
    "EuriborFetcher",
    "OilFetcher",
    "YFinanceFetcher",
]
