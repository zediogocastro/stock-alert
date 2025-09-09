import yfinance as yf
import pandas as pd
from typing import Optional

def fetch_sma(
    ticker: str = "^GSPC",
    period: str = "6mo",
    window: int = 21
) -> pd.DataFrame:
    """
    Fetch historical data for a ticker and compute SMA and differences.
    
    Args:
        ticker: Stock ticker symbol (default "^GSPC").
        period: Period string for yfinance (e.g., "6mo", "1y").
        window: Moving average window size.
    
    Returns:
        pd.DataFrame with columns:
            - Close
            - sma_{window}
            - Diff (Close - SMA)
            - Diff_pct (percent difference)
    """
    # Fetch historical data
    ticker_data = yf.Ticker(ticker)
    historic_data = ticker_data.history(period=period, interval="1d", rounding=True)

    # Prepare DataFrame
    df = historic_data[["Close"]].copy()
    df[f"sma_{window}"] = df["Close"].rolling(window=window).mean()
    
    # Compute differences
    df["Diff"] = df["Close"] - df[f"sma_{window}"].round(1)
    df["Diff_pct"] = ((df["Diff"] / df[f"sma_{window}"]) * 100).round(1)
    
    # Drop rows with NaN from rolling
    df.dropna(inplace=True)
    
    return df

if __name__ == "__main__":
    # Config
    TICKER = "^GSPC"
    PERIOD = "2y"
    WINDOW_SIZE = 21
    
    # Fetch data
    df = fetch_sma(ticker=TICKER, period=PERIOD, window=WINDOW_SIZE)

    # Print last row for quick insight
    current_diff = df.iloc[-1]
    print("Latest data:")
    print(current_diff)