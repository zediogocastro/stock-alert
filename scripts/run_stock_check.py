from stock_alert import YFinanceFetcher, CreateMovingAverage, DataPipeline, PlotExporter
from stock_alert.exporter import CSVExporter, CompositeExporter
from common.logger import get_logger

logger = get_logger(__name__)

# Fetcher
TICKER = "^GSPC"
PERIOD = "2y"

# Transform
WINDOW_SIZE = 21

# Exporters
FILE_NAME = "reports/stock_report.csv"
PLOT_NAME = "reports/stock_plot.png"

if __name__ == "__main__":
    # Initialize fetcher
    fetcher = YFinanceFetcher(
        ticker=TICKER,
        period=PERIOD,
    )

    # Initialize Transformer
    transformer = CreateMovingAverage(
        window_size=WINDOW_SIZE
    )

    # Initialize Exporter
    exporter_plot = PlotExporter(
        filename=PLOT_NAME,
        columns=["Close" , "sma_21"]
    )
    exporter_data = CSVExporter(
        filename=FILE_NAME
    )
    # Create multiple exporter
    exporter = CompositeExporter([
        exporter_plot,
        exporter_data
    ])

    # Initialize and run pipeline
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    logger.info("✅ Pipeline Completed!")
