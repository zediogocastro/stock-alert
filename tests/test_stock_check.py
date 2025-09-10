import pandas as pd
import pytest

import stock_alert.stock_check as sc

class DummyTicker:
    def history(self, period, interval, rounding):
        data = {"Close": list(range(100, 125))}  
        return pd.DataFrame(data)
    
def test_prepare_report_adds_expected_columns(monkeypatch):
    # Replace yfinance.Ticker with DummyTicker
    monkeypatch.setattr(sc.yf, "Ticker", lambda ticker: DummyTicker())

    df = sc.prepare_report(window_size=5)

    # Ensure expected columns exist
    assert "Close" in df.columns
    assert "sma_5" in df.columns
    assert "Diff" in df.columns
    assert "Diff_pct" in df.columns

def test_prepare_report_calculations(monkeypatch):
    monkeypatch.setattr(sc.yf, "Ticker", lambda ticker: DummyTicker())
    df = sc.prepare_report(window_size=5)

    # Manually compute SMA for one row
    excpected_sma = sum(range(100, 105)) / 5
    actual_sma = df.loc[4, "sma_5"]

    assert actual_sma == excpected_sma