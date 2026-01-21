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
            logger.info("Fetching data...")
            asset_data = self.fetcher.fetch()
            if asset_data.data.empty:
                raise ValueError("No data fetched")
            logger.debug(f"Fetched {len(asset_data.data)} rows for {asset_data.ticker} ({asset_data.currency})")
            
            # Transform 
            logger.info("Transforming data...")
            transformed = self.transformer.transform(asset_data)

            # Export 
            logger.info("Exporting data...")
            self.exporter.export(transformed)
        except Exception as e:
            raise RuntimeError(f"Pipeline failed: {e}") from e
        

