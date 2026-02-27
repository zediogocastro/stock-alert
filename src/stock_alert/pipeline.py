import polars as pl
from pathlib import Path
from common.logger import logger
from stock_alert.fetcher import BaseFetcher
#from stock_alert.transformer import Transformer
from stock_alert.features import FeatureEngine

class DataPipeline:
    """Class that is responsible for the ETL pipeline"""
    def __init__(self, 
                 fetcher: BaseFetcher, 
                 feature_engine: FeatureEngine, 
                 master_table_directory: str | None = None):
        self.fetcher = fetcher
        self.feature_engine = feature_engine
        self.master_table_directory = master_table_directory

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

            if self.master_table_directory:
                master_table_path = Path(self.master_table_directory) / "master_table.parquet"
                self._save_data(transformed, master_table_path)
                
        except Exception as e:
            raise RuntimeError(f"Pipeline failed: {e}") from e
        
    def _save_data(self, data: pl.LazyFrame, path: Path) -> None:
        """Save data to a path.
        
        Args:
            data:  Lazy Polars Data to be saved.
            direcotry: The path of the file to be saved into.
        """
        path.parent.mkdir(parents=True, exist_ok=True)  
        data.sink_parquet(path)
        logger.info(f"Saved raw data to {path}")
        

