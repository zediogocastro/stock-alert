import polars as pl
from common.logger import logger
from stock_alert.fetcher import BaseFetcher
#from stock_alert.transformer import Transformer
from stock_alert.features import FeatureEngine
from stock_alert.exporter import BaseExporter

class DataPipeline:
    """Class that is responsible for the ETL pipeline"""
    def __init__(self, 
                 fetcher: BaseFetcher, 
                 feature_engine: FeatureEngine, 
                 exporter: BaseExporter):
        self.fetcher = fetcher
        self.feature_engine = feature_engine
        self.exporter = exporter

    def run(self) -> None:
        try:
            logger.info("Starting pipeline execution")

            # Fetch Data
            logger.info("Fetching data...")
            data = self.fetcher.fetch()
            if data.empty:
                raise ValueError("No data fetched")
            
            # Transform (Feature Engineering)
            logger.info("Generating features...")
            transformed = self.feature_engine.transform(pl.from_pandas(data))

            # Export 
            logger.info("Exporting data...")
            self.exporter.export(transformed)
        except Exception as e:
            raise RuntimeError(f"Pipeline failed: {e}") from e
        

