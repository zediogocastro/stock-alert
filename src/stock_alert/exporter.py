from abc import ABC, abstractmethod
import pandas as pd


class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
    
    def export(self, data: pd.DataFrame) -> None:
        """Template method: handles common logic"""
        self._ensure_directory_exists()
        self._write(data)

    @abstractmethod
    def _write(self, data: pd.DataFrame) -> None:
        """Subclasses implement the actual writing logic"""
        pass
    
    def _ensure_directory_exists(self) -> None:
        """Shared utility: ensure output directory exists"""
        import os
        directory = os.path.dirname(self.filename)
        if directory:
            os.makedirs(directory, exist_ok=True)

class CSVExporter(BaseExporter):
    """Exporter that writes data to CSV files"""

    def _write(self, data: pd.DataFrame) -> None:
        data.to_csv(self.filename, index=True)


class PlotExporter(BaseExporter):
    """Exporter that creates a seaborn plot"""
    def __init__(self, filename: str, columns: list[str]) -> None:
        super().__init__(filename)
        self.columns = columns

    def _write(self, data: pd.DataFrame) -> None:
        import seaborn as sns
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 6))
        for column in self.columns:
            sns.lineplot(
                data=data,
                x="Date",
                y=column,
                label=column
            )
        plt.title("Stock Analysis")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.savefig(self.filename)
        plt.close()
        