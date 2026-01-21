from abc import ABC, abstractmethod
from typing import List
import pandas as pd

from stock_alert.data_model import AssetData


class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
    
    def export(self, asset_data: AssetData) -> None:
        """Template method: handles common logic"""
        self._ensure_directory_exists()
        self._write(asset_data)

    @abstractmethod
    def _write(self, asset_data: AssetData) -> None:
        """Subclasses implement the actual writing logic"""
        pass
    
    def _ensure_directory_exists(self) -> None:
        """Shared utility: ensure output directory exists"""
        import os
        directory = os.path.dirname(self.filename)
        if directory:
            os.makedirs(directory, exist_ok=True)

class CompositeExporter(BaseExporter):
    """
    Class than enables composition of multiple exporters to be used as
    as one.

    NOTE: This class inherits from BaseExporter for convenience but doesn't
    use file-related functionality (filename, _ensure_directory_exists, _write).
    
    TODO: Refactor to separate Exporter interface from FileExporter implementation.
    This will eliminate the need for these no-op methods and follow Interface
    Segregation Principle (ISP).

    Attributes:
        exporters (List[BaseExporter]): The list of Exporters
    """

    def __init__(self, exporters: List[BaseExporter]) -> None:
        self.exporters = exporters

    def export(self, asset_data: AssetData) -> None:
        """Execute all exporters in sequence"""
        for exporter in self.exporters:
            exporter.export(asset_data)

    # TODO: Moved into a more concrete class 
    def _ensure_directory_exists(self) -> None:
        """Not needed - individual exporters handle this"""
        pass
    
    # TODO: Moved into a more concrete class 
    def _write(self, asset_data:AssetData) -> None:
        """Not needed - export() handles the logic"""
        pass

class CSVExporter(BaseExporter):
    """Exporter that writes data to CSV files"""
    def _write(self, asset_data: AssetData) -> None:
        asset_data.data.to_csv(self.filename, index=True)

class PlotExporter(BaseExporter):
    """Exporter that creates a seaborn plot"""
    def __init__(self, filename: str, columns: list[str],  display_currency: str | None = None) -> None:
        super().__init__(filename)
        self.columns = columns
        self.display_currency = display_currency

    def _write(self, asset_data: AssetData) -> None:
        import seaborn as sns
        import matplotlib.pyplot as plt

        # Conver currency if requested
        if self.display_currency:
            asset_data = asset_data.to_currency(self.display_currency)

        data = asset_data.data

        plt.figure(figsize=(12, 6))
        for column in self.columns:
            sns.lineplot(
                data=data,
                x="Date",
                y=column,
                label=column
            )
        title = f"{asset_data.name or asset_data.ticker} Price Analysis"
        plt.title(title)
        plt.xlabel("Date")
        plt.ylabel(f"Price ({asset_data.currency})")
        plt.legend()
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.savefig(self.filename)
        plt.close()
        