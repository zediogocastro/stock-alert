import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ---------------------## Config ##---------------------#
SP500_VARIANTS = ["^GSPC", "VUAA.DE", "VUAA.L"]
VIX_IDENTIFIER = "^VIX"

# Buy-signal banner thresholds (tune to your own risk tolerance)
DRAWDOWN_FAVORABLE_THRESHOLD = -0.10  # 10%+ off all-time high
VIX_PANIC_THRESHOLD = 30
VIX_CALM_THRESHOLD = 15
SMA200_STRETCH_THRESHOLD = 0.15  # 15% above SMA200 = "running hot"

# Well-known historical bear markets (public dates), used only for chart shading
BEAR_MARKETS = [
    ("Dot-com Crash", "2000-03-24", "2002-10-09"),
    ("Global Financial Crisis", "2007-10-09", "2009-03-09"),
    ("COVID-19 Crash", "2020-02-19", "2020-03-23"),
    ("2022 Bear Market", "2022-01-03", "2022-10-12"),
]

DEFAULT_MONTHLY_DCA = 200
# ---------------------## End ##------------------------#


@st.cache_data
def load_data():
    try:
        df = pd.read_parquet("data/transformed/master_table.parquet")
        df["Date"] = pd.to_datetime(df["Date"])
        return df.sort_values("Date")
    except FileNotFoundError:
        st.error(
            "Master table not found. Please run the data pipeline first (`scripts/fetch_data.py` then `scripts/generate_features.py`)."
        )
        st.stop()


def render_banner(kind: str, text: str) -> None:
    getattr(st, kind)(text)


def compute_banner(drawdown, price_vs_sma21, price_vs_sma200, vix_level):
    """Rule-based, historically-informed heuristic - not a prediction."""
    if (drawdown is not None and drawdown <= DRAWDOWN_FAVORABLE_THRESHOLD) or (
        price_vs_sma21 is not None and price_vs_sma21 < 0
    ):
        return (
            "success",
            "🟢 Historically favorable window — price is pulled back from its recent "
            "trend/highs. A good time to stick to (or add to) your DCA plan.",
        )
    if vix_level is not None and vix_level > VIX_PANIC_THRESHOLD:
        return (
            "success",
            f"🟢 Elevated fear (VIX {vix_level:.1f} > {VIX_PANIC_THRESHOLD}) — markets have "
            "historically overreacted to downside during panic; long-term DCA investors "
            "have been rewarded for staying the course.",
        )
    if (
        price_vs_sma200 is not None
        and price_vs_sma200 > SMA200_STRETCH_THRESHOLD
        and vix_level is not None
        and vix_level < VIX_CALM_THRESHOLD
    ):
        return (
            "warning",
            "🟡 Market is running hot (well above trend, low volatility) — no reason to "
            "stop DCA, just don't chase with extra lump sums.",
        )
    return (
        "info",
        "🔵 Neutral regime — no strong signal either way. Keep your scheduled DCA going.",
    )


df = load_data()

st.title("🧭 DCA Compass")
st.markdown("Your rational, numbers-first companion for monthly S&P 500 investing.")
st.caption(
    "⚠️ Educational tool based on historical data. Not financial advice — past "
    "performance does not guarantee future results."
)

available_variants = [v for v in SP500_VARIANTS if v in df["identifier"].unique()]
if not available_variants:
    st.error("No S&P 500 data available. Please run the data pipeline first.")
    st.stop()

instrument = st.selectbox("S&P 500 instrument", available_variants)

instrument_df = (
    df[df["identifier"] == instrument]
    .dropna(subset=["Close"])
    .sort_values("Date")
    .reset_index(drop=True)
)
vix_df = (
    df[df["identifier"] == VIX_IDENTIFIER]
    .dropna(subset=["Close"])
    .sort_values("Date")
    .reset_index(drop=True)
)

latest = instrument_df.iloc[-1]
latest_vix = vix_df.iloc[-1] if not vix_df.empty else None

price_vs_sma21_pct = (
    (latest["Close"] - latest["sma_21d"]) / latest["sma_21d"]
    if pd.notna(latest["sma_21d"])
    else None
)
price_vs_sma200_pct = (
    (latest["Close"] - latest["sma_200d"]) / latest["sma_200d"]
    if pd.notna(latest["sma_200d"])
    else None
)
current_drawdown = latest["drawdown_pct"] if pd.notna(latest["drawdown_pct"]) else None
golden_cross = (
    bool(latest["sma_gap_50_200d"] > 0) if pd.notna(latest["sma_gap_50_200d"]) else None
)
vix_level = latest_vix["Close"] if latest_vix is not None else None

banner_type, banner_text = compute_banner(
    current_drawdown, price_vs_sma21_pct, price_vs_sma200_pct, vix_level
)
render_banner(banner_type, banner_text)

tab_overview, tab_history, tab_outlook, tab_planner = st.tabs(
    ["🚦 Overview", "📉 History & Trend", "📐 Long-Term Outlook", "💰 DCA Planner"]
)

# --- Overview ---
with tab_overview:
    with st.container(border=True):
        st.markdown("#### 🩺 Market Health Snapshot")
        st.markdown("Five quick reads on where things stand right now — each one explained below.")
        with st.expander("📖 How to read these 5 metrics"):
            st.markdown(
                """
- **Price vs SMA21** — the current price compared to its 21-trading-day (~1 month) average.
  A negative % means price has pulled back below its recent short-term trend — the exact
  "buy the dip" signal referenced by the banner above. A positive % means short-term momentum
  is strong.
- **Trend (vs SMA200)** — the 200-day moving average is one of the most widely used long-term
  trend filters worldwide. 🟢 Bull (price above it) has historically coincided with calmer,
  more reliable growth periods; 🔴 Bear (price below it) has historically coincided with higher
  volatility and elevated drawdown risk — it is not a sell signal by itself.
- **Cross Regime (50/200)** — 🟡 Golden Cross means the 50-day average has crossed above the
  200-day (a bullish handoff, widely reported in financial media); ⚫ Death Cross is the bearish
  reverse. Both are **lagging** signals — by the time they trigger, the trend has usually
  already been underway for weeks, so treat them as confirmation/context, not a precise timing
  tool.
- **Drawdown from ATH** — how far below its all-time high the price currently sits. As a rough
  industry convention: -10% is often called a "correction", -20%+ a "bear market". A small
  drawdown (single digits) is a completely normal, frequent occurrence — not a crisis.
- **VIX (Fear Gauge)** — the CBOE Volatility Index, derived from S&P 500 options prices; it
  measures how much volatility the market expects over the next 30 days. Rough bands:
  **<15 calm/complacent**, **15–30 elevated caution**, **>30 high fear/panic**. Historically,
  the highest VIX spikes have coincided with some of the best long-term entry points — markets
  tend to overreact to bad news in the short term.
"""
            )
        cols = st.columns(5)
        with cols[0]:
            st.metric(
                "Price",
                f"${latest['Close']:.2f}",
                f"{price_vs_sma21_pct * 100:+.2f}% vs SMA21"
                if price_vs_sma21_pct is not None
                else "N/A",
            )
        with cols[1]:
            regime = (
                "🟢 Bull"
                if price_vs_sma200_pct is not None and price_vs_sma200_pct > 0
                else "🔴 Bear"
                if price_vs_sma200_pct is not None
                else "N/A"
            )
            st.metric(
                "Trend (vs SMA200)",
                regime,
                f"{price_vs_sma200_pct * 100:+.2f}%"
                if price_vs_sma200_pct is not None
                else "N/A",
            )
        with cols[2]:
            cross_label = (
                "🟡 Golden Cross"
                if golden_cross
                else "⚫ Death Cross"
                if golden_cross is not None
                else "N/A"
            )
            st.metric("Cross Regime (50/200)", cross_label)
        with cols[3]:
            st.metric(
                "Drawdown from ATH",
                f"{current_drawdown * 100:.1f}%" if current_drawdown is not None else "N/A",
            )
        with cols[4]:
            if vix_level is not None:
                vix_band = (
                    "🟢 Calm"
                    if vix_level < VIX_CALM_THRESHOLD
                    else "🟡 Elevated"
                    if vix_level < VIX_PANIC_THRESHOLD
                    else "🔴 High Fear"
                )
                st.metric("VIX (Fear Gauge)", f"{vix_level:.1f}", vix_band)
            else:
                st.metric("VIX (Fear Gauge)", "N/A")

# --- History & Trend ---
with tab_history:
    with st.container(border=True):
        st.markdown("#### 📉 Drawdown History (How bad has it been before?)")
        st.markdown(
            "How far the price has fallen from its running all-time high. Shaded "
            "regions mark well-known historical bear markets, when covered by this "
            "instrument's available history."
        )
        with st.expander("📖 How to read this chart"):
            st.markdown(
                """
- **What it shows**: at every date, `(price − running all-time high) / running all-time high`,
  always ≤ 0%. It's the "underwater" view of the index — how far below its own peak it was on
  that day.
- **Shape matters**: a sharp V-shaped notch (e.g. COVID 2020) means a fast crash followed by a
  fast recovery. A long, wide trough (e.g. 2000-2002, 2007-2009) means a slow grind that took
  years to recover — this is the pattern most likely to test an investor's patience.
- **Why it's shown over the full history**: seeing that -50%+ drawdowns have happened multiple
  times *and* were eventually fully recovered is the best antidote to the fear that "this time
  it won't come back." It has, every time, for a broad diversified index like the S&P 500.
- **How to use it**: compare today's drawdown level (top metric row) against this chart's
  historical range. A few percent off the highs is unremarkable; only double-digit,
  multi-month drawdowns have historically been unusual/notable events.
- **Caveat**: this describes what *has* happened, not a prediction of how deep or long the
  *next* drawdown will be.
"""
            )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=instrument_df["Date"],
                y=instrument_df["drawdown_pct"] * 100,
                name="Drawdown",
                line=dict(color="crimson"),
                fill="tozeroy",
            )
        )

        data_start = instrument_df["Date"].min()
        data_end = instrument_df["Date"].max()
        shown_labels = []
        for label, start, end in BEAR_MARKETS:
            start_ts = pd.Timestamp(start, tz=data_start.tz)
            end_ts = pd.Timestamp(end, tz=data_start.tz)
            if end_ts >= data_start and start_ts <= data_end:
                fig.add_vrect(
                    x0=max(start_ts, data_start),
                    x1=min(end_ts, data_end),
                    fillcolor="gray",
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                )
                shown_labels.append(label)

        fig.update_layout(yaxis_title="Drawdown (%)")
        st.plotly_chart(fig, key="drawdown_chart")

        if shown_labels:
            st.caption(f"Shaded regions: {', '.join(shown_labels)}.")

        worst_row = instrument_df.loc[instrument_df["drawdown_pct"].idxmin()]
        st.caption(
            f"Worst historical drawdown: **{worst_row['drawdown_pct'] * 100:.1f}%** "
            f"on {worst_row['Date'].date()}."
        )

    with st.container(border=True):
        st.markdown("#### 📈 Trend Regime (Golden Cross / Death Cross)")
        st.markdown(
            "Price alongside its 50-day and 200-day moving averages (log scale, to "
            "keep decades of history readable). A golden cross (50-day above 200-day) "
            "is historically read as bullish; a death cross is the bearish reverse."
        )
        with st.expander("📖 How to read this chart"):
            st.markdown(
                """
- **Log scale**: price is shown on a logarithmic y-axis so that a century of growth (single
  dollars in the 1930s to thousands today) stays readable on one chart — equal vertical
  distances represent equal *percentage* moves, not equal dollar moves.
- **SMA50 / SMA200**: two rolling averages of price, smoothing out day-to-day noise so the
  underlying trend direction is easier to see.
- **Golden Cross / Death Cross**: when the faster SMA50 crosses above the slower SMA200, it's
  read as a bullish trend-change signal (golden cross); crossing below is the bearish death
  cross. These are among the most widely followed trend signals in finance media.
- **Lagging by design**: because both lines are *averages of past prices*, a cross is
  confirmation that a trend has already been underway for a while — not an early warning.
  Crosses can also "whipsaw" (flip back shortly after) in choppy, sideways markets.
- **The regime caption**: a regime that has held for a long time (many days) reflects an
  established trend; a regime that flipped very recently carries a higher chance of being a
  false signal that reverses again soon.
- **For a DCA investor**: this is context, not a trading trigger — long-term DCA doesn't
  require correctly timing every cross.
"""
            )

        trend_df = instrument_df.dropna(subset=["sma_50d", "sma_200d"]).copy()
        if trend_df.empty:
            st.info("Not enough history yet to compute SMA50/SMA200 for this instrument.")
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=trend_df["Date"], y=trend_df["Close"], name="Price", line=dict(color="black")
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=trend_df["Date"], y=trend_df["sma_50d"], name="SMA50", line=dict(color="orange")
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=trend_df["Date"], y=trend_df["sma_200d"], name="SMA200", line=dict(color="blue")
                )
            )
            fig.update_layout(yaxis_title="Price", yaxis_type="log")
            st.plotly_chart(fig, key="trend_chart")

            trend_df["golden"] = trend_df["sma_gap_50_200d"] > 0
            regime_changes = trend_df.loc[trend_df["golden"] != trend_df["golden"].shift(1), "Date"]
            last_change = regime_changes.iloc[-1] if not regime_changes.empty else trend_df["Date"].iloc[0]
            days_in_regime = (trend_df["Date"].iloc[-1] - last_change).days
            current_regime_label = (
                "Golden Cross (bullish)" if trend_df["golden"].iloc[-1] else "Death Cross (bearish)"
            )
            st.caption(
                f"Current regime: **{current_regime_label}**, in place for "
                f"**{days_in_regime}** days (since {last_change.date()})."
            )

# --- Long-Term Outlook ---
with tab_outlook:
    with st.container(border=True):
        st.markdown("#### 📐 Rolling Long-Term Return Ranges")
        st.markdown(
            "For every possible start date in this instrument's history, what was the "
            "annualized return (CAGR) if you'd invested and held for N years? Longer "
            "horizons historically narrow the range of outcomes."
        )
        with st.expander("📖 How to read this chart"):
            st.markdown(
                """
- **What it shows**: pick a holding period N (years). For *every* historical date, the chart
  computes "if I had invested a lump sum on that date and held for exactly N years, what
  annualized return (CAGR) would I have earned?" Each bar groups together how many historical
  start dates landed in that return range.
- **Reading the shape**: a wide histogram with bars stretching into negative territory means
  many possible start dates would have left you worse off after N years. A narrow histogram
  clustered on the positive side means the outcome was historically far more consistent.
- **The key experiment**: move the slider from a small N (e.g. 1 year) to a large N (e.g. 15-20
  years) and watch the histogram narrow and shift right. This is the numeric version of "time
  in the market reduces the odds of a bad outcome" — the core argument for staying invested
  through short-term noise.
- **The 4 summary stats**: *Worst case* and *Best case* are the extremes ever observed for that
  N; *Median* is the "typical" historical outcome; *% of windows negative* is how often that
  holding period would have lost money outright — for long-enough N on `^GSPC`'s full history,
  this is often 0%.
- **Caveat**: this is a purely historical, backward-looking distribution — it is not a
  guarantee about the *next* N years, and results depend heavily on how much history is
  available for the selected instrument (`VUAA.L`/`VUAA.DE` only have a few years, all during a
  bull market, so treat their stats here with extra caution — use `^GSPC` for the fullest
  picture).
"""
            )

        span_years = (instrument_df["Date"].iloc[-1] - instrument_df["Date"].iloc[0]).days / 365.25
        max_n = max(1, int(span_years) - 1)

        if max_n < 2:
            st.info("Not enough history yet for this instrument to compute rolling returns.")
        else:
            n_years = st.slider("Holding period (years)", 1, max_n, min(10, max_n), key="rolling_n_years")

            monthly_prices = instrument_df.set_index("Date")["Close"].resample("ME").last().dropna()
            forward_periods = n_years * 12
            cagr = (monthly_prices.shift(-forward_periods) / monthly_prices) ** (1 / n_years) - 1
            cagr = cagr.dropna()

            if cagr.empty:
                st.info("Not enough history for this holding period.")
            else:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=cagr * 100, nbinsx=40, marker_color="steelblue"))
                fig.update_layout(
                    xaxis_title=f"{n_years}-Year Annualized Return (%)",
                    yaxis_title="Number of historical start dates",
                )
                st.plotly_chart(fig, key="rolling_return_hist")

                neg_pct = (cagr < 0).mean() * 100
                stat_cols = st.columns(4)
                stat_cols[0].metric("Worst case (CAGR)", f"{cagr.min() * 100:.1f}%")
                stat_cols[1].metric("Median case (CAGR)", f"{cagr.median() * 100:.1f}%")
                stat_cols[2].metric("Best case (CAGR)", f"{cagr.max() * 100:.1f}%")
                stat_cols[3].metric("% of windows negative", f"{neg_pct:.1f}%")

    with st.container(border=True):
        st.markdown("#### 🎲 Monte Carlo Future Projection")
        st.markdown(
            "Simulates possible future outcomes for a monthly DCA plan by bootstrap-"
            "resampling (with replacement) from this instrument's own historical monthly "
            "returns. Assumes the future statistically resembles the past — a "
            "simplification, but a data-driven one. Seeded for reproducible results."
        )
        with st.expander("📖 How to read this chart"):
            st.markdown(
                """
- **What a "fan chart" is**: instead of one predicted line, it shows a *range* of thousands of
  simulated futures as percentile bands. **P50** (thick middle line) is the median simulated
  outcome; **P5** means only 5% of simulations did worse (a pessimistic/"unlucky" case); **P95**
  means only 5% did better (an optimistic/"lucky" case). The gap between P5 and P95 is the
  honest uncertainty in the projection — it's normal for it to widen over time.
- **How the simulation works, in plain terms**: it takes this instrument's real historical
  monthly returns, shuffles and re-draws from them at random (with repetition) to build
  thousands of alternate "what could have happened" return sequences, then simulates investing
  your monthly contribution along each one.
- **The black dotted line ("Total Contributed")** is your break-even reference — money in, with
  zero growth. Any point where the colored bands are above it represents a gain; below it, a
  loss.
- **The 4 summary stats**: *Median ending value* is the "typical" simulated outcome after the
  chosen horizon; *5th percentile ending value* is a realistic pessimistic scenario (worse than
  95% of simulations); *P(ending value < contributed)* is the simulated probability of ending up
  with *less* than you put in — for long horizons on a diversified index this is usually small,
  which is the direct, numeric answer to "what if it just stagnates for years?".
- **Key assumption/caveat**: bootstrap resampling treats each historical month as interchangeable
  and independent — it ignores real-world effects like multi-month momentum/mean-reversion
  clustering, and it can only be as representative as the historical sample it draws from (a
  short history, like `VUAA.L`/`VUAA.DE`, means the simulation has only seen bull-market returns
  and will be overly optimistic).
"""
            )

        mc_cols = st.columns(3)
        with mc_cols[0]:
            mc_horizon = st.slider("Projection horizon (years)", 5, 40, 20, key="mc_horizon")
        with mc_cols[1]:
            mc_monthly_amount = st.number_input(
                "Monthly contribution ($)", min_value=1, value=DEFAULT_MONTHLY_DCA, key="mc_monthly_amount"
            )
        with mc_cols[2]:
            mc_sims = st.slider("Simulations", 200, 5000, 2000, step=200, key="mc_sims")

        mc_monthly_prices = instrument_df.set_index("Date")["Close"].resample("ME").last().dropna()
        mc_monthly_returns = mc_monthly_prices.pct_change().dropna().to_numpy()

        if len(mc_monthly_returns) < 12:
            st.info("Not enough history to run a Monte Carlo simulation for this instrument.")
        else:
            rng = np.random.default_rng(seed=42)
            n_months = mc_horizon * 12
            sampled_returns = rng.choice(mc_monthly_returns, size=(mc_sims, n_months), replace=True)

            price_path = np.cumprod(1 + sampled_returns, axis=1)
            price_level = np.concatenate([np.ones((mc_sims, 1)), price_path], axis=1)

            portfolio = np.zeros((mc_sims, n_months))
            mc_shares = np.zeros(mc_sims)
            for m in range(n_months):
                mc_shares += mc_monthly_amount / price_level[:, m]
                portfolio[:, m] = mc_shares * price_level[:, m + 1]

            total_invested = mc_monthly_amount * n_months
            ending_values = portfolio[:, -1]

            percentiles = [5, 25, 50, 75, 95]
            pct_over_time = np.percentile(portfolio, percentiles, axis=0)
            months_axis = np.arange(1, n_months + 1)

            fig = go.Figure()
            for p, series in zip(percentiles, pct_over_time):
                fig.add_trace(
                    go.Scatter(
                        x=months_axis, y=series, name=f"P{p}", line=dict(width=3 if p == 50 else 1)
                    )
                )
            fig.add_trace(
                go.Scatter(
                    x=months_axis,
                    y=mc_monthly_amount * months_axis,
                    name="Total Contributed",
                    line=dict(color="black", dash="dot"),
                )
            )
            fig.update_layout(xaxis_title="Months", yaxis_title="Portfolio Value ($)")
            st.plotly_chart(fig, key="monte_carlo_chart")

            prob_loss = (ending_values < total_invested).mean() * 100
            mc_stat_cols = st.columns(4)
            mc_stat_cols[0].metric("Total contributed", f"${total_invested:,.0f}")
            mc_stat_cols[1].metric("Median ending value", f"${np.median(ending_values):,.0f}")
            mc_stat_cols[2].metric("5th percentile ending value", f"${np.percentile(ending_values, 5):,.0f}")
            mc_stat_cols[3].metric("P(ending value < contributed)", f"{prob_loss:.1f}%")

# --- DCA Planner ---
with tab_planner:
    with st.container(border=True):
        st.markdown("#### 💰 DCA Backtest Simulator")
        st.markdown(
            "Backtests a fixed monthly contribution against this instrument's real "
            "historical prices, compared to investing it all upfront (lump sum) and to "
            "adding a bonus contribution whenever the price is below its SMA21 (your "
            "'buy the dip' rule)."
        )
        with st.expander("📖 How to read this chart"):
            st.markdown(
                """
- **The 4 lines**: *Plain DCA* invests a fixed amount every month; *DCA + Dip Bonus* does the
  same but adds extra money on months where price closed below its SMA21 (your own "buy the
  dip" rule, quantified); *Lump Sum* invests the entire eventual total on day one; *Total
  Contributed* (black dotted) is the simple sum of money put in, with zero growth — your
  break-even line.
- **Quick read**: any colored line above the black dotted line = that strategy is currently
  profitable over the chosen window; below it = currently at a loss. Comparing the colored
  lines to *each other* shows which strategy performed best over that specific window.
- **Why Lump Sum often wins in backtests**: over a period where the market trends upward more
  often than not, money invested earlier has more time to compound — so lump sum tends to beat
  DCA in hindsight. This doesn't make DCA "wrong": DCA's real value is behavioral and practical
  — you don't need a lump sum ready, it smooths out the price you pay over time, and it removes
  the regret risk of investing everything right before a downturn.
- **Try this**: change the start date to include a known downturn (e.g. 2007 or 2020) to see
  DCA's smoothing effect show up much more clearly than in a straight-line bull market.
- **Approximate annualized return**: an estimate based on the *average* time each dollar was
  invested (contributions are spread evenly across the period), not a precise money-weighted
  IRR — treat it as directionally useful, not exact to the decimal.
"""
            )

        data_start_date = instrument_df["Date"].min().date()
        data_end_date = instrument_df["Date"].max().date()

        sim_cols = st.columns(3)
        with sim_cols[0]:
            dca_amount = st.number_input(
                "Monthly contribution ($)", min_value=1, value=DEFAULT_MONTHLY_DCA, key="dca_amount"
            )
        with sim_cols[1]:
            default_start = max(data_start_date, data_end_date - timedelta(days=365 * 10))
            dca_start = st.date_input(
                "Start date",
                value=default_start,
                min_value=data_start_date,
                max_value=data_end_date,
                key="dca_start",
            )
        with sim_cols[2]:
            add_bonus = st.checkbox("Add bonus when price < SMA21", value=True, key="dca_bonus_toggle")
            bonus_amount = st.number_input(
                "Bonus amount ($)",
                min_value=0,
                value=DEFAULT_MONTHLY_DCA,
                key="dca_bonus_amount",
                disabled=not add_bonus,
            )

        sim_df = instrument_df[
            instrument_df["Date"] >= pd.Timestamp(dca_start, tz=instrument_df["Date"].dt.tz)
        ].copy()

        if sim_df.empty:
            st.info("No data available from the selected start date.")
        else:
            monthly_sim = sim_df.set_index("Date").resample("MS").first().dropna(subset=["Close"])

            shares_plain = 0.0
            shares_bonus = 0.0
            invested_plain = 0.0
            invested_bonus = 0.0
            history = []

            for date, row in monthly_sim.iterrows():
                price = row["Close"]
                shares_plain += dca_amount / price
                invested_plain += dca_amount

                is_dip = add_bonus and pd.notna(row.get("sma_21d")) and price < row["sma_21d"]
                bonus_this_month = bonus_amount if is_dip else 0
                shares_bonus += (dca_amount + bonus_this_month) / price
                invested_bonus += dca_amount + bonus_this_month

                history.append(
                    {
                        "Date": date,
                        "Plain DCA Value": shares_plain * price,
                        "Dip-Bonus DCA Value": shares_bonus * price,
                    }
                )

            history_df = pd.DataFrame(history)
            first_price = monthly_sim["Close"].iloc[0]
            lump_shares = invested_plain / first_price
            history_df["Lump Sum Value"] = lump_shares * monthly_sim["Close"].to_numpy()
            history_df["Total Contributed"] = np.arange(1, len(history_df) + 1) * dca_amount

            final_plain_value = history_df["Plain DCA Value"].iloc[-1]
            final_bonus_value = history_df["Dip-Bonus DCA Value"].iloc[-1]
            final_lump_value = history_df["Lump Sum Value"].iloc[-1]

            years_elapsed = (monthly_sim.index[-1] - monthly_sim.index[0]).days / 365.25
            avg_years_invested = years_elapsed / 2  # contributions are spread evenly over the period

            def approx_annualized_return(final_value, total_invested_amount, avg_years):
                if total_invested_amount <= 0 or avg_years <= 0:
                    return None
                return (final_value / total_invested_amount) ** (1 / avg_years) - 1

            plain_annualized = approx_annualized_return(final_plain_value, invested_plain, avg_years_invested)
            bonus_annualized = approx_annualized_return(final_bonus_value, invested_bonus, avg_years_invested)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history_df["Date"], y=history_df["Plain DCA Value"], name="Plain DCA"))
            if add_bonus:
                fig.add_trace(
                    go.Scatter(x=history_df["Date"], y=history_df["Dip-Bonus DCA Value"], name="DCA + Dip Bonus")
                )
            fig.add_trace(go.Scatter(x=history_df["Date"], y=history_df["Lump Sum Value"], name="Lump Sum"))
            fig.add_trace(
                go.Scatter(
                    x=history_df["Date"],
                    y=history_df["Total Contributed"],
                    name="Total Contributed",
                    line=dict(color="black", dash="dot"),
                )
            )
            fig.update_layout(yaxis_title="Value ($)")
            st.plotly_chart(fig, key="dca_sim_chart")

            metric_cols = st.columns(4)
            metric_cols[0].metric("Total invested (plain)", f"${invested_plain:,.0f}")
            metric_cols[1].metric(
                "Plain DCA final value",
                f"${final_plain_value:,.0f}",
                f"{(final_plain_value / invested_plain - 1) * 100:.1f}%",
            )
            metric_cols[2].metric(
                "Lump sum final value",
                f"${final_lump_value:,.0f}",
                f"{(final_lump_value / invested_plain - 1) * 100:.1f}%",
            )
            if add_bonus:
                metric_cols[3].metric(
                    "DCA+Dip-Bonus final value",
                    f"${final_bonus_value:,.0f}",
                    f"{(final_bonus_value / invested_bonus - 1) * 100:.1f}%",
                )

            annualized_caption = "Approximate annualized return"
            if plain_annualized is not None:
                annualized_caption += f" — Plain DCA: {plain_annualized * 100:.1f}%"
            if add_bonus and bonus_annualized is not None:
                annualized_caption += f", DCA+Dip Bonus: {bonus_annualized * 100:.1f}%"
            annualized_caption += (
                " (approximation based on average capital-weighted holding period, not a precise money-weighted IRR)."
            )
            st.caption(annualized_caption)

    with st.container(border=True):
        st.markdown("#### 🔔 Monthly DCA Reminder")
        st.markdown(
            "A simple nudge to keep your DCA schedule on track (this tool doesn't store "
            "or track your actual purchases)."
        )

        reminder_cols = st.columns(2)
        with reminder_cols[0]:
            preferred_day = st.slider("Preferred day of month for your DCA", 1, 28, 1, key="dca_reminder_day")

        today = datetime.now().date()
        if today.day < preferred_day:
            next_dca = today.replace(day=preferred_day)
        else:
            next_month = (today.replace(day=1) + pd.DateOffset(months=1)).date()
            next_dca = next_month.replace(day=preferred_day)
        days_until = (next_dca - today).days

        with reminder_cols[1]:
            st.metric("Next scheduled DCA", str(next_dca), f"{days_until} days")

        render_banner(banner_type, f"Reminder context — {banner_text}")
