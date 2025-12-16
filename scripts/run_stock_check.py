from stock_alert import YFinanceFetcher, CreateMovingAverage, CSVExporter, DataPipeline
from common.logger import logger

# Fetcher
TICKER = "^GSPC"
PERIOD = "2y"

# Transform
WINDOW_SIZE = 21

# Exporter
FILE_NAME = "reports/stock_report.csv"

if __name__ == "__main__":
    fetcher = YFinanceFetcher(
        ticker=TICKER,
        period=PERIOD,
    )
    transformer = CreateMovingAverage(
        window_size=WINDOW_SIZE
    )
    exporter = CSVExporter(
        filename=FILE_NAME
    )
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
