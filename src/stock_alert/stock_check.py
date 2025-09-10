import yfinance as yf
import pandas as pd

TICKER = "^GSPC"
PERIOD = "2y"
WINDOW_SIZE = 21

def prepare_report(ticker: str = TICKER, period: str = PERIOD, window_size: int = WINDOW_SIZE) -> pd.DataFrame:
    """Fetch ticker data and compute SMA & differences."""
    tk = yf.Ticker(ticker)
    historic_data = tk.history(period=period, interval="1d", rounding=True)

    df = historic_data[["Close"]].copy()
    df[f"sma_{window_size}"] = df["Close"].rolling(window=window_size).mean()

    df["Diff"] = df["Close"] - df[f"sma_{window_size}"].round(1)
    df["Diff_pct"] = ((df["Diff"] / df[f"sma_{window_size}"]) * 100).round(1)

    return df

def print_report():
    df = prepare_report()
    print(df.tail(4))