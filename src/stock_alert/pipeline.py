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
                 exporter: BaseExporter | None = None):
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
            data = pl.from_pandas(data).lazy()
            transformed = self.feature_engine.transform(data)

            # Export
            if self.exporter: 
                logger.info("Exporting data...")
                data_to_export = transformed.collect().to_pandas()
                self.exporter.export(data_to_export)
            else:
                logger.info("No exporter configured, skipping export")
                
        except Exception as e:
            raise RuntimeError(f"Pipeline failed: {e}") from e
        

