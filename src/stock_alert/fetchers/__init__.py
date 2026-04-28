from .base import BaseFetcher
from .eu_fuel import EUFuelFetcher
from .euribor import EuriborFetcher
from .inflation import InflationFetcher
from .oil import OilFetcher
from .portugal_cpi import INEPortugalFetcher
from .yfinance import YFinanceFetcher

__all__ = [
    "BaseFetcher",
    "EUFuelFetcher",
    "EuriborFetcher",
    "INEPortugalFetcher",
    "InflationFetcher",
    "OilFetcher",
    "YFinanceFetcher",
]
