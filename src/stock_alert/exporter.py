#TODO improve Exporter
import os
from abc import ABC, abstractmethod
from typing import List
import pandas as pd
import matplotlib.pyplot as plt


"""Plotting utilities for data visualization"""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def create_line_plot(
    data: pd.DataFrame,
    x_column: str,
    y_columns: list[str],
    title: str = "Analysis",
    xlabel: str = "X",
    ylabel: str = "Y",
    figsize: tuple[int, int] = (12, 6)
) -> Figure:
    """Create a line plot and return the figure
    
    Args:
        data: DataFrame with data to plot
        x_column: Column name for x-axis
        y_columns: List of column names for y-axis
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        figsize: Figure size (width, height)
    
    Returns:
        Matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    for column in y_columns:
        if column in data.columns:
            ax.plot(data[x_column], data[column], label=column)
    
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3, linestyle='--')
    fig.tight_layout()
    
    return fig

class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
    
    def export(self, df: pd.DataFrame) -> None:
        """Template method: handles common logic"""
        self._ensure_directory_exists()
        self._write(df)

    @abstractmethod
    def _write(self, df: pd.DataFrame) -> None:
        """Subclasses implement the actual writing logic"""
        pass
    
    def _ensure_directory_exists(self) -> None:
        """Shared utility: ensure output directory exists"""
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)

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

    def export(self, df: pd.DataFrame) -> None:
        """Execute all exporters in sequence"""
        for exporter in self.exporters:
            exporter.export(df)

    # TODO: Moved into a more concrete class 
    def _ensure_directory_exists(self) -> None:
        """Not needed - individual exporters handle this"""
        pass
    
    # TODO: Moved into a more concrete class 
    def _write(self, df:pd.DataFrame) -> None:
        """Not needed - export() handles the logic"""
        pass

class CSVExporter(BaseExporter):
    """Exporter that writes data to CSV files"""
    def __init__(self, output_dir: str, filename: str) -> None:
        super().__init__(output_dir)
        self.filename = filename

    def _write(self, df: pd.DataFrame) -> None:
        filepath = os.path.join(self.output_dir, self.filename)
        df.data.to_csv(filepath, index=True)

class PlotExporter(BaseExporter):
    """Exporter that creates line plots for multiple tickers"""
    def __init__(self, output_dir: str, columns: list[str], group_by: str) -> None:
        super().__init__(output_dir)
        self.columns = columns
        self.group_by = group_by

    def _save_figure(self, fig, filename: str, dpi: int = 100) -> None:
        """Save figure to output directory"""
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=dpi)
        plt.close(fig)

    def _write(self, df: pd.DataFrame) -> None:
        if self.group_by not in df.columns:
            return
        
        tickers = df[self.group_by].unique()
        for ticker in tickers:
            ticker_data = df[df[self.group_by] == ticker]

            fig = create_line_plot(
                data=ticker_data,
                x_column="Date",
                y_columns=self.columns,
                title=f"{ticker} Price Analysis",
                xlabel="Date",
                ylabel="Euro" #TODO Improve this
            )
            
            self._save_figure(fig, ticker)

        
        