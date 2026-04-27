from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
from common.logger import logger


class BaseFetcher(ABC):
    """Generic base class defining the fetching contract.

    Subclasses must define SUBFOLDER (str) to specify the ingestion subdirectory.
    Override BASE_CACHE_DIR at the class level to change the root cache directory.
    """

    SUBFOLDER: str
    BASE_CACHE_DIR: str = "data/ingested"

    def __init__(self, cache_dir: str | None = None) -> None:
        self.cache_dir = cache_dir or self.BASE_CACHE_DIR

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        pass

    def _write_data(self, data: pd.DataFrame) -> None:
        """Save fetched data to {cache_dir}/{SUBFOLDER}/data.parquet"""
        if not self.cache_dir:
            return

        save_path = Path(self.cache_dir) / self.SUBFOLDER / "data.parquet"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(save_path)
        logger.info(f"Write data to {save_path}")
