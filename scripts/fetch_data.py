from stock_alert import (
    YFinanceFetcher,
    EuriborFetcher,
    INEPortugalFetcher,
    InflationFetcher,
    OilFetcher,
    EUFuelFetcher,
    FetcherService,
)
from common.logger import logger

# ---------------------## Config ##---------------------#
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT", "PLTR", "NVDA"]
PERIOD = "5y"
# ---------------------## End ##------------------------#


if __name__ == "__main__":
    FetcherService(
        fetchers=[
            YFinanceFetcher(identifiers=TICKERS, period=PERIOD),
            EuriborFetcher(),
            OilFetcher(period=PERIOD),
            EUFuelFetcher(),
            InflationFetcher(),
            INEPortugalFetcher(),
        ]
    ).run()
    logger.info("✅ Fetch completed!")
