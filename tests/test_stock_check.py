import pytest
import pandas as pd
from stock_alert.fetcher import BaseFetcher, YFinanceFetcher
from stock_alert.transformer import CreateMovingAverage
from stock_alert.exporter import BaseExporter, CSVExporter
from stock_alert.pipeline import DataPipeline


# ============ FETCHER TESTS ============

class MockFetcher(BaseFetcher):
    """Mock fetcher for testing"""
    def fetch(self) -> pd.DataFrame:
        # Return fake stock data
        return pd.DataFrame({
            'Close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        })


def test_base_fetcher_normalizes_ticker():
    """Test that ticker is converted to uppercase"""
    fetcher = MockFetcher(ticker="aapl", period="1mo")
    assert fetcher.ticker == "AAPL"


def test_base_fetcher_stores_period():
    """Test that period is stored correctly"""
    fetcher = MockFetcher(ticker="AAPL", period="1y")
    assert fetcher.period == "1y"


def test_mock_fetcher_returns_dataframe():
    """Test that fetcher returns a DataFrame"""
    fetcher = MockFetcher(ticker="AAPL", period="1mo")
    result = fetcher.fetch()
    assert isinstance(result, pd.DataFrame)
    assert "Close" in result.columns


@pytest.mark.integration
def test_yfinance_fetcher_real_data():
    """Integration test with real yfinance data"""
    fetcher = YFinanceFetcher(ticker="AAPL", period="5d")
    result = fetcher.fetch()
    
    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "Close" in result.columns


# ============ TRANSFORMER TESTS ============

def test_create_moving_average_adds_sma_column():
    """Test that SMA column is added"""
    data = pd.DataFrame({'Close': [100, 102, 104, 106, 108]})
    transformer = CreateMovingAverage(window_size=3)
    
    result = transformer.transform(data)
    
    assert "sma_3" in result.columns


def test_create_moving_average_calculates_correctly():
    """Test SMA calculation is correct"""
    data = pd.DataFrame({'Close': [100, 102, 104, 106, 108]})
    transformer = CreateMovingAverage(window_size=3)
    
    result = transformer.transform(data)
    
    # Check specific SMA value: (100+102+104)/3 = 102
    assert result.loc[2, "sma_3"] == 102.0


def test_create_moving_average_adds_diff_columns():
    """Test that Diff and Diff_pct columns are added"""
    data = pd.DataFrame({'Close': [100, 102, 104, 106, 108]})
    transformer = CreateMovingAverage(window_size=3)
    
    result = transformer.transform(data)
    
    assert "Diff" in result.columns
    assert "Diff_pct" in result.columns


def test_create_moving_average_handles_nan():
    """Test that NaN values are handled in rolling window"""
    data = pd.DataFrame({'Close': [100, 102, 104]})
    transformer = CreateMovingAverage(window_size=3)
    
    result = transformer.transform(data)
    
    # First two rows should have NaN for window_size=3
    assert pd.isna(result.loc[0, "sma_3"])
    assert pd.isna(result.loc[1, "sma_3"])
    assert not pd.isna(result.loc[2, "sma_3"])


def test_transformer_returns_dataframe():
    """Test that transformer returns DataFrame"""
    data = pd.DataFrame({'Close': [100, 102, 104, 106, 108]})
    transformer = CreateMovingAverage(window_size=2)
    
    result = transformer.transform(data)
    
    assert isinstance(result, pd.DataFrame)


# ============ EXPORTER TESTS ============

class MockExporter(BaseExporter):
    """Mock exporter for testing"""
    def __init__(self, filename: str):
        super().__init__(filename)
        self.write_called = False
        self.data_received = None
    
    def _write(self, data: pd.DataFrame) -> None:
        self.write_called = True
        self.data_received = data


def test_base_exporter_stores_filename():
    """Test that filename is stored"""
    exporter = MockExporter(filename="test.csv")
    assert exporter.filename == "test.csv"


def test_base_exporter_calls_write():
    """Test that export calls _write method"""
    data = pd.DataFrame({'A': [1, 2, 3]})
    exporter = MockExporter(filename="test.csv")
    
    exporter.export(data)
    
    assert exporter.write_called
    assert exporter.data_received is not None


def test_csv_exporter_creates_file(tmp_path):
    """Test that CSV file is created"""
    output_file = tmp_path / "test_output.csv"
    data = pd.DataFrame({'Close': [100, 102, 104], 'sma_3': [None, None, 102.0]})
    
    exporter = CSVExporter(filename=str(output_file))
    exporter.export(data)
    
    assert output_file.exists()


def test_csv_exporter_creates_directory(tmp_path):
    """Test that nested directories are created"""
    output_file = tmp_path / "reports" / "nested" / "output.csv"
    data = pd.DataFrame({'Close': [100, 102, 104]})
    
    exporter = CSVExporter(filename=str(output_file))
    exporter.export(data)
    
    assert output_file.exists()
    assert output_file.parent.exists()


def test_csv_exporter_writes_correct_data(tmp_path):
    """Test that CSV contains correct data"""
    output_file = tmp_path / "test.csv"
    data = pd.DataFrame({'Close': [100, 102, 104]})
    
    exporter = CSVExporter(filename=str(output_file))
    exporter.export(data)
    
    # Read back and verify
    result = pd.read_csv(output_file, index_col=0)
    pd.testing.assert_frame_equal(result, data)


# ============ PIPELINE TESTS ============

def test_pipeline_runs_end_to_end(tmp_path):
    """Test complete pipeline execution"""
    output_file = tmp_path / "pipeline_output.csv"
    
    fetcher = MockFetcher(ticker="TEST", period="1mo")
    transformer = CreateMovingAverage(window_size=3)
    exporter = CSVExporter(filename=str(output_file))
    
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    
    assert output_file.exists()


def test_pipeline_stores_components():
    """Test that pipeline stores all components"""
    fetcher = MockFetcher(ticker="TEST", period="1mo")
    transformer = CreateMovingAverage(window_size=3)
    exporter = MockExporter(filename="test.csv")
    
    pipeline = DataPipeline(fetcher, transformer, exporter)
    
    assert pipeline.fetcher is fetcher
    assert pipeline.transformer is transformer
    assert pipeline.exporter is exporter


def test_pipeline_data_flows_correctly(tmp_path):
    """Test that data flows through pipeline correctly"""
    output_file = tmp_path / "flow_test.csv"
    
    fetcher = MockFetcher(ticker="TEST", period="1mo")
    transformer = CreateMovingAverage(window_size=3)
    exporter = CSVExporter(filename=str(output_file))
    
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    
    # Read result and verify transformations applied
    result = pd.read_csv(output_file, index_col=0)
    assert "Close" in result.columns
    assert "sma_3" in result.columns
    assert "Diff" in result.columns
    assert "Diff_pct" in result.columns


@pytest.mark.integration
def test_pipeline_with_real_fetcher(tmp_path):
    """Integration test with real yfinance data"""
    output_file = tmp_path / "real_data.csv"
    
    fetcher = YFinanceFetcher(ticker="AAPL", period="5d")
    transformer = CreateMovingAverage(window_size=2)
    exporter = CSVExporter(filename=str(output_file))
    
    pipeline = DataPipeline(fetcher, transformer, exporter)
    pipeline.run()
    
    assert output_file.exists()
    result = pd.read_csv(output_file, index_col=0)
    assert not result.empty