import yfinance as yf
import pandas as pd
import os

TICKER = "^GSPC"
PERIOD = "2y"
WINDOW_SIZE = 21
REPORTS_DIR = "reports"
CSV_FILE = os.path.join(REPORTS_DIR, "stock_report.csv")
MD_FILE = os.path.join(REPORTS_DIR, "stock_report.md")


def prepare_report(
    ticker: str = TICKER, period: str = PERIOD, window_size: int = WINDOW_SIZE
) -> pd.DataFrame:
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


def save_csv_report(df: pd.DataFrame, filepath: str = CSV_FILE) -> str:
    """Save a machine-readable CSV report, overwriting previous one."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    df_to_save = df.copy()
    for col in df_to_save.select_dtypes("float"):
        df_to_save[col] = df_to_save[col].round(2)

    df_to_save.to_csv(filepath, index=True)
    print(f"CSV report saved to {filepath}")
    return filepath


def save_markdown_report(
    df: pd.DataFrame, filepath: str = MD_FILE, last_n: int = 30
) -> str:
    """Save a human-readable Markdown report, overwriting previous one."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    df_to_save = df.tail(last_n).copy()

    # Format numeric columns nicely
    df_to_save["Close"] = df_to_save["Close"].map("{:.2f}".format)
    sma_col = f"sma_{WINDOW_SIZE}"
    df_to_save[sma_col] = df_to_save[sma_col].map("{:.2f}".format)
    df_to_save["Diff"] = df_to_save["Diff"].map("{:+.2f}".format)
    df_to_save["Diff_pct"] = df_to_save["Diff_pct"].map("{:+.2f}%".format)

    df_to_save_reset = df_to_save.reset_index()
    markdown_table = df_to_save_reset.to_markdown(index=False)

    with open(filepath, "w") as f:
        f.write("# Stock Report\n\n")
        f.write(markdown_table)

    print(f"Markdown report saved to {filepath}")
    return filepath


def generate_reports():
    """Generate both CSV and Markdown reports, overwriting previous ones."""
    df = prepare_report()
    save_csv_report(df)
    save_markdown_report(df)
    return CSV_FILE, MD_FILE
