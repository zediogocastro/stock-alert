# S&P500 SMA21 Alert 🚨

This project checks the latest S&P500 index value and compares it to its **21-day Simple Moving Average (SMA21)**.  
If the value is below the SMA21, it sends a notification (email or other).  

The goal is to practice **CI/CD concepts** using **GitHub Actions**.

---

## Features
- Fetch latest S&P500 data (using `yfinance`).
- Compute the 21-day Simple Moving Average (SMA21).
- Check if the index is below the SMA21.
- Send an alert (email, Slack, etc.).
- Run automatically via **GitHub Actions (scheduled job)**.

---

## Project Structure

```
sp500-alert/
│── sp500_check.py    # Main Python script
│── .github/workflows # GitHub Actions workflows (CI/CD)
│── README.md         # Project documentation
````

