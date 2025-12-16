from common.logger import logger
from stock_alert.fetcher import BaseFetcher
from stock_alert.transformer import Transformer
from stock_alert.exporter import BaseExporter


class DataPipeline:
    """Class that is responsible for the ETL pipeline"""
    def __init__(self, 
                 fetcher: BaseFetcher, 
                 transformer: Transformer, 
                 exporter: BaseExporter):
        self.fetcher = fetcher
        self.transformer = transformer
        self.exporter = exporter

    def run(self) -> None:
        try:
            logger.info("Starting pipeline execution")

            # Fetch Data
            logger.debug("Fetching data...")
            data = self.fetcher.fetch()
            if data.empty:
                raise ValueError("No data fetched")
            
            # Transform 
            logger.debug("Transforming data...")
            transformed = self.transformer.transform(data)

            # Export 
            logger.debug("Exporting data...")
            self.exporter.export(transformed)
        except Exception as e:
            raise RuntimeError(f"Pipeline failed: {e}") from e
        

