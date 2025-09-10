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

## Continuous Integration (CI) and Reports

This repository uses **GitHub Actions** for CI/CD. The workflows include:

- **Lint and Tests**: Automatically run on every pull request and push to `main`.  
- **Scheduled Reports**: Automatically generate stock reports on weekdays (Monday–Friday) at **11:00 UTC**.  
  - Reports are saved in the `reports/` folder:  
    - `report_machine.csv` → machine-readable data  
    - `report_human.md` → human-readable Markdown summary  
- **Manual Runs**: You can also trigger workflows manually from the **Actions** tab in GitHub (`Run workflow`).

> ⏰ **Note on timezones**: GitHub Actions cron jobs run in **UTC**.  
> 11:00 UTC = 12:00 Lisbon (winter) / 13:00 Lisbon (summer).
