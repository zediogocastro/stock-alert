from stock_alert import YFinanceFetcher, EuriborFetcher, FetcherService
from common.logger import logger

# ---------------------## Config ##---------------------#
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT", "PLTR"]
PERIOD = "5y"
# ---------------------## End ##------------------------#


if __name__ == "__main__":
    FetcherService(fetchers=[
        YFinanceFetcher(identifiers=TICKERS, period=PERIOD),
        EuriborFetcher(),
    ]).run()
    logger.info("✅ Fetch completed!")
