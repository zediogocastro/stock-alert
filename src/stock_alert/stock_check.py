import yfinance as yf
import pandas as pd

TICKER = "^GSPC"
PERIOD = "2y"
WINDOW_SIZE = 21

def print_report():
    # Extract SP500 data
    tk = yf.Ticker(TICKER)
    historic_data = tk.history(period=PERIOD, interval="1d", rounding=True)

    # Transform data
    df = historic_data[["Close"]].copy()
    df[f"sma_{WINDOW_SIZE}"] = df["Close"].rolling(window=WINDOW_SIZE).mean()

    df["Diff"] = df["Close"] - df[f"sma_{WINDOW_SIZE}"].round(1)
    df["Diff_pct"] = ((df["Diff"] / df[f"sma_{WINDOW_SIZE}"]) * 100).round(1)

    # Report Data
    # Print last 4 row for quick insight
    print(df.tail(4))