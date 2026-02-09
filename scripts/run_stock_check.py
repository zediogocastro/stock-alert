from stock_alert import YFinanceFetcher, DataPipeline, PlotExporter
from stock_alert.exporter import CSVExporter, CompositeExporter
from stock_alert.features import FeatureEngine, MovingAverage
from common.logger import logger

#---------------------## Config ##---------------------#
# Fetcher
#TICKER = "AAPL" #"IE00BFMXXD54" # "^GSPC"
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT"]
PERIOD = "2y"

# Feature Engineering
GROUP_BY = "identifier"
SORT_BY = "Date"
COLUMN = "Close"

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

    # Initialize Feature Engine with multiple features
    feature_engine = (
        FeatureEngine(group_by=GROUP_BY)
        .add(MovingAverage(column=COLUMN, window_days=21, sort_by_column=SORT_BY))
        .add(MovingAverage(column=COLUMN, window_days=50, sort_by_column=SORT_BY))
        .add(MovingAverage(column=COLUMN, window_days=200, sort_by_column=SORT_BY))
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
    pipeline = DataPipeline(fetcher, feature_engine, exporter)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
