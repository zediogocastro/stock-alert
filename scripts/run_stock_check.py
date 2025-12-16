from stock_alert import YFinanceFetcher, CreateMovingAverage, CSVExporter, DataPipeline, PlotExporter
from common.logger import logger

# Fetcher
TICKER = "^GSPC"
PERIOD = "2y"

# Transform
WINDOW_SIZE = 21

# Exporter
#FILE_NAME = "reports/stock_report.csv"
PLOT_NAME = "reports/stock_plot.png"

if __name__ == "__main__":
    fetcher = YFinanceFetcher(
        ticker=TICKER,
        period=PERIOD,
    )
    transformer = CreateMovingAverage(
        window_size=WINDOW_SIZE
    )
    exporter = PlotExporter(
        filename=PLOT_NAME,
        columns=["Close" , "sma_21"]
    )
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
