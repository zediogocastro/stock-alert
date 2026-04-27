import polars as pl
from pathlib import Path
from common.logger import logger
from stock_alert.fetchers import BaseFetcher
from stock_alert.features import FeatureEngine


class FetcherService:
    """Orchestrates multiple fetchers, running each one independently.

    Each fetcher is responsible for persisting its own raw data upon completion,
    keeping data sources fully decoupled from one another.
    """

    def __init__(self, fetchers: list[BaseFetcher]) -> None:
        self.fetchers = fetchers

    def run(self) -> None:
        """Run all fetchers sequentially, raising on the first failure."""
        logger.info(f"Starting fetch stage ({len(self.fetchers)} fetcher(s))...")
        for fetcher in self.fetchers:
            name = type(fetcher).__name__
            try:
                logger.info(f"Running {name}...")
                fetcher.fetch()
                logger.info(f"{name} completed successfully")
            except Exception as e:
                raise RuntimeError(f"{name} failed: {e}") from e
        logger.info("Fetch stage complete")


class FeatureService:
    """Reads ingested data, applies feature engineering, and writes the master table.

    Intentionally decoupled from fetching so it can be re-run independently
    without making any external API calls.
    """

    def __init__(
        self,
        feature_engine: FeatureEngine,
        ingested_data_path: str,
        output_dir: str,
    ) -> None:
        self.feature_engine = feature_engine
        self.ingested_data_path = Path(ingested_data_path)
        self.output_dir = Path(output_dir)

    def run(self) -> None:
        """Load ingested data, compute all features, and persist the master table."""
        try:
            logger.info(f"Loading data from {self.ingested_data_path}...")
            data = pl.scan_parquet(self.ingested_data_path)

            logger.info("Generating features...")
            transformed = self.feature_engine.transform(data)

            output_path = self.output_dir / "master_table.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            transformed.sink_parquet(output_path)
            logger.info(f"Master table saved to {output_path}")
        except Exception as e:
            raise RuntimeError(f"Feature generation failed: {e}") from e
