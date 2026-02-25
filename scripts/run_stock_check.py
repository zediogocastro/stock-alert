from stock_alert import YFinanceFetcher, DataPipeline
from stock_alert.features import FeatureEngine, MovingAverage
from stock_alert.features.atomic_features import Returns, Volatility, RelativeStrengthIndex
#from stock_alert.exporter import PlotExporter, CSVExporter, CompositeExporter

from common.logger import logger

#---------------------## Config ##---------------------#
# Fetcher
#TICKER = "AAPL" #"IE00BFMXXD54" # "^GSPC"
TICKERS = ["AAPL", "AMZN", "TSLA", "MSFT"]
PERIOD = "5y"

# Feature Engineering
IDENTIFIER = "identifier"
SORT_BY = "Date"
COLUMN = "Close"

# Exporters
REPORTS_DIR = "reports"

# General
MASTER_TABLE_CACHE = "data/transformed"


#---------------------## End ##---------------------#

if __name__ == "__main__":
    # Initialize fetcher
    fetcher = YFinanceFetcher(
        identifiers=TICKERS,
        period=PERIOD,
        cache_dir="data/ingested"
    )

    # Initialize Feature Engine with multiple features
    features_to_copute = [
        MovingAverage(column=COLUMN, window_days=21, sort_by=SORT_BY, group_by=IDENTIFIER),
        MovingAverage(column=COLUMN, window_days=200, sort_by=SORT_BY, group_by=IDENTIFIER),
        Returns(column=COLUMN, n_days=1, sort_by=SORT_BY, group_by=IDENTIFIER),
        Volatility(column=COLUMN, window_days=21, sort_by=SORT_BY, group_by=IDENTIFIER),
        Volatility(column=COLUMN, window_days=100, sort_by=SORT_BY, group_by=IDENTIFIER),
        RelativeStrengthIndex(column=COLUMN, window_days=14, sort_by=SORT_BY, group_by=IDENTIFIER)
    ]
    feature_engine = FeatureEngine(features=features_to_copute)

    # # Initialize multiple exporters
    # exporter_plot = PlotExporter(
    #     output_dir=REPORTS_DIR,
    #     columns=["Close" , "sma_21d", "sma_200d"],
    #     GROUP_BY=IDENTIFIER
    # )
    # exporter_data = CSVExporter(
    #     output_dir=REPORTS_DIR,
    #     filename="stock_report.csv"
    # )
    # exporter = CompositeExporter([
    #     exporter_plot,
    #     exporter_data
    # ])

    # Initialize and run pipeline
    pipeline = DataPipeline(fetcher, feature_engine, master_table_directory=MASTER_TABLE_CACHE)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
