from stock_alert import FeatureService
from stock_alert.features import FeatureEngine, MovingAverage
from stock_alert.features.atomic_features import Returns, Volatility, RelativeStrengthIndex
from common.logger import logger

# ---------------------## Config ##---------------------#
IDENTIFIER = "identifier"
SORT_BY = "Date"
COLUMN = "Close"

INGESTED_STOCKS_PATH = "data/ingested/stocks/data.parquet"
MASTER_TABLE_DIR = "data/transformed"
# ---------------------## End ##------------------------#


if __name__ == "__main__":
    FeatureService(
        feature_engine=FeatureEngine(features=[
            MovingAverage(column=COLUMN, window_days=21, sort_by=SORT_BY, group_by=IDENTIFIER),
            MovingAverage(column=COLUMN, window_days=200, sort_by=SORT_BY, group_by=IDENTIFIER),
            Returns(column=COLUMN, n_days=1, sort_by=SORT_BY, group_by=IDENTIFIER),
            Volatility(column=COLUMN, window_days=21, sort_by=SORT_BY, group_by=IDENTIFIER),
            Volatility(column=COLUMN, window_days=100, sort_by=SORT_BY, group_by=IDENTIFIER),
            RelativeStrengthIndex(column=COLUMN, window_days=14, sort_by=SORT_BY, group_by=IDENTIFIER),
        ]),
        ingested_data_path=INGESTED_STOCKS_PATH,
        output_dir=MASTER_TABLE_DIR,
    ).run()
    logger.info("✅ Features generated!")
