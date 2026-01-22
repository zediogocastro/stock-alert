from stock_alert import YFinanceFetcher, CreateMovingAverage, DataPipeline, PlotExporter
from stock_alert.exporter import CSVExporter, CompositeExporter
from common.logger import logger

#---------------------## Config ##---------------------#
# Fetcher
#TICKER = "AAPL" #"IE00BFMXXD54" # "^GSPC"
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT"]
PERIOD = "2y"

# Transform
WINDOW_SIZE = 21

# Exporters
FILE_NAME = "reports/stock_report.csv"
PLOT_NAME = "reports/stock_plot.png"

# Display preference
DISPLAY_CURRENCY = None # "EUR" 

#---------------------## End ##---------------------#

if __name__ == "__main__":
    # Initialize fetcher
    fetcher = YFinanceFetcher(
        identifiers=TICKERS,
        period=PERIOD,
        cache_dir="data/ingested"
    )

    # Initialize Transformer
    transformer = CreateMovingAverage(
        window_size=WINDOW_SIZE
    )

    # Initialize multiple exporters
    exporter_plot = PlotExporter(
        filename=PLOT_NAME,
        columns=["Close" , "sma_21"],
        display_currency=DISPLAY_CURRENCY
    )
    exporter_data = CSVExporter(
        filename=FILE_NAME
    )
    exporter = CompositeExporter([
        exporter_plot,
        exporter_data
    ])

    # Initialize and run pipeline
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
