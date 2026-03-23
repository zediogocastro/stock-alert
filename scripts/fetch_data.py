from stock_alert import YFinanceFetcher, EuriborFetcher, OilFetcher, FetcherService
from common.logger import logger

# ---------------------## Config ##---------------------#
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT", "PLTR"]
PERIOD = "5y"
# ---------------------## End ##------------------------#


if __name__ == "__main__":
    FetcherService(fetchers=[
        YFinanceFetcher(identifiers=TICKERS, period=PERIOD),
        EuriborFetcher(),
        OilFetcher(period=PERIOD),
    ]).run()
    logger.info("✅ Fetch completed!")
