import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("🛢️ Crude Oil Market Monitor")
st.markdown(
    "Daily prices for the two main global crude oil benchmarks — **Brent Crude** (international reference, ~70% of "
    "globally traded oil) and **WTI** (West Texas Intermediate, US domestic benchmark) — sourced from Yahoo Finance "
    "front-month futures. All prices in **USD per barrel**."
)

# ── Constants ──────────────────────────────────────────────────────────────────
BENCHMARKS = ["BRENT", "WTI"]
BENCHMARK_LABELS = {"BRENT": "Brent Crude", "WTI": "WTI Crude"}
BENCHMARK_COLORS = {"BRENT": "#F7931E", "WTI": "#636EFA"}

# Key geopolitical/market events to annotate on the chart
KEY_EVENTS = [
    ("2020-03-01", "2020-05-15", "rgba(239,85,59,0.09)",  "COVID demand collapse"),
    ("2022-02-24", "2022-06-01", "rgba(255,165,0,0.12)",  "Russia–Ukraine invasion"),
    ("2022-10-05", "2023-02-01", "rgba(100,100,255,0.08)", "OPEC+ deep cuts"),
    ("2023-10-07", "2024-03-01", "rgba(255,80,80,0.09)",  "Middle East escalation"),
]

# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet("data/ingested/oil/data.parquet")
        df["Date"] = pd.to_datetime(df["Date"])
        if df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_localize(None)
        df = df.sort_values(["benchmark", "Date"]).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error("Oil data not found. Please run `scripts/fetch_data.py` first.")
        st.stop()


df = load_data()
latest_date = df["Date"].max()

# Pivot wide for spread — used in multiple sections
wide = df.pivot_table(index="Date", columns="benchmark", values="Close").sort_index()
spread_series: pd.Series | None = None
if "BRENT" in wide.columns and "WTI" in wide.columns:
    spread_series = (wide["BRENT"] - wide["WTI"]).dropna()

# ── KPI Row ────────────────────────────────────────────────────────────────────
st.markdown("### 📌 Current Snapshot")
kpi_cols = st.columns(4)

for i, bm in enumerate(BENCHMARKS):
    bm_df = df[df["benchmark"] == bm].sort_values("Date")
    current = bm_df.iloc[-1]
    prev_week = bm_df.iloc[-6] if len(bm_df) >= 6 else bm_df.iloc[0]
    year_ago_cands = bm_df[bm_df["Date"] <= current["Date"] - pd.DateOffset(months=12)]
    year_ago = year_ago_cands.iloc[-1] if not year_ago_cands.empty else None

    wow = ((current["Close"] / prev_week["Close"]) - 1) * 100
    yoy = ((current["Close"] / year_ago["Close"]) - 1) * 100 if year_ago is not None else None

    with kpi_cols[i]:
        with st.container(border=True):
            st.metric(
                label=BENCHMARK_LABELS[bm],
                value=f"${current['Close']:.2f} /bbl",
                delta=f"{wow:+.2f}% WoW",
                delta_color="normal",
            )
            if yoy is not None:
                arrow = "🔴" if yoy < -10 else ("🟢" if yoy > 10 else "⚪")
                st.caption(f"{arrow} YoY: {yoy:+.1f}%")
            st.caption(f"As of {current['Date'].strftime('%d %b %Y')}")

# Spread KPI
if spread_series is not None:
    spread_now = spread_series.iloc[-1]
    spread_1m_avg = spread_series.tail(21).mean()
    spread_delta = spread_now - spread_1m_avg
    with kpi_cols[2]:
        with st.container(border=True):
            st.metric(
                label="Brent – WTI Spread",
                value=f"${spread_now:.2f} /bbl",
                delta=f"{spread_delta:+.2f} vs 1M avg",
                delta_color="off",
            )
            percentile = (spread_series < spread_now).mean() * 100
            st.caption(f"At {percentile:.0f}th percentile of history")
            st.caption("Wide = global risk premium · Narrow = markets converging")

# 52-week range KPI
brent_df = df[df["benchmark"] == "BRENT"].sort_values("Date")
brent_52w = brent_df[brent_df["Date"] >= latest_date - pd.DateOffset(weeks=52)]
with kpi_cols[3]:
    with st.container(border=True):
        hi = brent_52w["High"].max()
        lo = brent_52w["Low"].min()
        last_close = brent_df.iloc[-1]["Close"]
        pos_pct = int((last_close - lo) / (hi - lo) * 100) if hi != lo else 50
        st.metric(label="Brent 52-Week Range", value=f"${lo:.0f} – ${hi:.0f} /bbl")
        st.caption(f"Current at **{pos_pct}th percentile** of yearly range")
        st.progress(pos_pct)

st.markdown("---")

# ── Layout: Controls | Historical chart ───────────────────────────────────────
col_left, col_right = st.columns([0.28, 0.72])

with col_left:
    with st.container(border=True):
        st.markdown("#### ⚙️ Filters")
        selected_bms = st.multiselect(
            "Benchmarks",
            options=BENCHMARKS,
            default=BENCHMARKS,
            format_func=lambda x: BENCHMARK_LABELS[x],
        )
        time_horizon = st.radio(
            "Time horizon",
            ["3 Months", "6 Months", "1 Year", "2 Years", "5 Years", "All"],
            index=2,
            horizontal=True,
        )
        show_events = st.toggle("Highlight key events", value=True)
        show_candles = st.toggle("Candlestick view", value=False)

    if not selected_bms:
        st.warning("Select at least one benchmark.")
        st.stop()

    # Compute date range
    end_date = latest_date
    horizon_months = {"3 Months": 3, "6 Months": 6, "1 Year": 12, "2 Years": 24, "5 Years": 60}
    if time_horizon in horizon_months:
        start_date = end_date - pd.DateOffset(months=horizon_months[time_horizon])
    else:
        start_date = df["Date"].min()

    df_filtered = df[
        (df["benchmark"].isin(selected_bms)) & (df["Date"] >= start_date)
    ].copy()

    # ── Period Statistics ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📊 Period Statistics")
        for bm in selected_bms:
            closes = df_filtered[df_filtered["benchmark"] == bm]["Close"].dropna()
            if not closes.empty:
                period_ret = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
                st.markdown(f"**{BENCHMARK_LABELS[bm]}**")
                s1, s2, s3 = st.columns(3)
                s1.metric("Low", f"${closes.min():.0f}")
                s2.metric("Avg", f"${closes.mean():.0f}")
                s3.metric("High", f"${closes.max():.0f}")
                ret_color = "🟢" if period_ret > 0 else "🔴"
                st.caption(f"{ret_color} Period return: {period_ret:+.1f}%")

with col_right:
    with st.container(border=True):
        st.markdown("#### 📈 Price History (USD/barrel)")
        fig_hist = go.Figure()

        if show_events:
            for x0, x1, color, label in KEY_EVENTS:
                if pd.to_datetime(x0) >= start_date:
                    fig_hist.add_vrect(
                        x0=x0, x1=x1,
                        fillcolor=color,
                        layer="below", line_width=0,
                        annotation_text=label,
                        annotation_position="top left",
                        annotation_font_size=10,
                        annotation_font_color="gray",
                    )

        for bm in selected_bms:
            bm_data = df_filtered[df_filtered["benchmark"] == bm].sort_values("Date")
            if show_candles:
                fig_hist.add_trace(go.Candlestick(
                    x=bm_data["Date"],
                    open=bm_data["Open"],
                    high=bm_data["High"],
                    low=bm_data["Low"],
                    close=bm_data["Close"],
                    name=BENCHMARK_LABELS[bm],
                    increasing_line_color=BENCHMARK_COLORS[bm],
                    decreasing_line_color="#EF553B",
                ))
            else:
                fig_hist.add_trace(go.Scatter(
                    x=bm_data["Date"],
                    y=bm_data["Close"],
                    name=BENCHMARK_LABELS[bm],
                    line=dict(color=BENCHMARK_COLORS[bm], width=2),
                    mode="lines",
                    hovertemplate=(
                        f"<b>{BENCHMARK_LABELS[bm]}</b><br>"
                        "Date: %{x|%d %b %Y}<br>"
                        "Price: $%{y:.2f}/bbl<extra></extra>"
                    ),
                ))

        fig_hist.update_layout(
            yaxis_title="Price (USD/bbl)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=460,
            margin=dict(l=10, r=10, t=40, b=20),
            xaxis_rangeslider_visible=False,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ── Brent – WTI Spread Analysis ────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("### 📐 Brent – WTI Spread Analysis")
    st.markdown(
        "The Brent–WTI spread reflects the **geographic and logistical premium** built into global oil. "
        "Brent prices in more Atlantic-basin supply risk (wars, sanctions, OPEC+), while WTI is driven by "
        "US pipeline capacity and domestic inventory levels. A widening spread typically signals heightened "
        "geopolitical risk or supply disruptions — exactly what you see during active conflicts."
    )

    if spread_series is None:
        st.info("Both BRENT and WTI data are required to display spread analysis.")
    else:
        spread_filtered = spread_series[spread_series.index >= start_date]
        spread_now = spread_series.iloc[-1]

        sp_col1, sp_col2 = st.columns(2)

        with sp_col1:
            st.markdown("##### Spread Over Time (Brent − WTI, USD/bbl)")
            st.caption("Orange fill = Brent premium · Blue fill = WTI premium (rare) · Dashed = 30-day MA")

            fig_spread = go.Figure()
            # Orange fill above zero (normal: Brent > WTI)
            fig_spread.add_trace(go.Scatter(
                x=spread_filtered.index, y=spread_filtered.clip(lower=0),
                fill="tozeroy", fillcolor="rgba(247,147,30,0.20)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip",
            ))
            # Blue fill below zero (WTI premium)
            fig_spread.add_trace(go.Scatter(
                x=spread_filtered.index, y=spread_filtered.clip(upper=0),
                fill="tozeroy", fillcolor="rgba(99,110,250,0.20)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip",
            ))
            # Spread line
            fig_spread.add_trace(go.Scatter(
                x=spread_filtered.index, y=spread_filtered,
                name="Brent − WTI",
                line=dict(color="#AB63FA", width=2),
                hovertemplate="Date: %{x|%d %b %Y}<br>Spread: $%{y:.2f}/bbl<extra></extra>",
            ))
            # 30-day MA
            spread_ma = spread_filtered.rolling(30, min_periods=1).mean()
            fig_spread.add_trace(go.Scatter(
                x=spread_ma.index, y=spread_ma,
                name="30d MA", line=dict(color="gray", dash="dash", width=1.5),
                hovertemplate="30d MA: $%{y:.2f}<extra></extra>",
            ))
            fig_spread.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.6)
            fig_spread.update_layout(
                yaxis_title="Spread (USD/bbl)", height=300,
                margin=dict(l=10, r=10, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_spread, use_container_width=True)

        with sp_col2:
            st.markdown("##### Spread Distribution")
            st.caption("Histogram of daily spread values — shows where today's premium sits relative to history.")

            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=spread_filtered,
                nbinsx=40,
                marker_color="#AB63FA",
                opacity=0.75,
                hovertemplate="Range: $%{x:.1f}/bbl<br>Days: %{y}<extra></extra>",
                showlegend=False,
            ))
            fig_dist.add_vline(
                x=float(spread_filtered.mean()),
                line_dash="dash", line_color="#F7931E",
                annotation_text=f"Avg ${spread_filtered.mean():.2f}",
                annotation_position="top right",
            )
            fig_dist.add_vline(
                x=float(spread_now),
                line_dash="solid", line_color="#EF553B",
                annotation_text=f"Now ${spread_now:.2f}",
                annotation_position="top left",
            )
            fig_dist.update_layout(
                xaxis_title="Spread (USD/bbl)", yaxis_title="Trading Days",
                height=300, margin=dict(l=10, r=10, t=30, b=20),
            )
            st.plotly_chart(fig_dist, use_container_width=True)

            # Interpretation
            percentile = float((spread_filtered < spread_now).mean() * 100)
            q25 = float(spread_filtered.quantile(0.25))
            q75 = float(spread_filtered.quantile(0.75))
            if spread_now > q75:
                spread_msg = (
                    f"🔴 **Spread is wide** (${spread_now:.2f}/bbl · {percentile:.0f}th pct). "
                    "Brent is commanding a large premium — signals elevated geopolitical risk or Atlantic-basin supply disruptions."
                )
            elif spread_now < q25:
                spread_msg = (
                    f"🟢 **Spread is tight** (${spread_now:.2f}/bbl · {percentile:.0f}th pct). "
                    "Brent–WTI convergence suggests eased global supply concerns or rising US export capacity."
                )
            else:
                spread_msg = (
                    f"⚪ **Spread is within normal range** (${spread_now:.2f}/bbl · {percentile:.0f}th pct). "
                    "No structural divergence between global and US benchmarks at present."
                )
            st.info(spread_msg)

# ── Realized Volatility ────────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("### 📉 Realized Volatility (21-Day Rolling, Annualized)")
    st.markdown(
        "Rolling volatility measures how violently prices are moving. It is computed as the 21-day standard "
        "deviation of daily log returns, scaled to an annualized figure. **Spikes signal market stress** — "
        "they coincide with COVID, the Russian invasion, and OPEC+ surprise announcements. "
        "High oil volatility typically feeds into headline inflation and corporate margin uncertainty across the entire economy."
    )

    fig_vol = go.Figure()

    for bm in BENCHMARKS:
        bm_data = df[df["benchmark"] == bm].sort_values("Date").reset_index(drop=True)
        returns = bm_data["Close"].pct_change()
        vol = returns.rolling(21).std() * (252 ** 0.5) * 100  # annualized %

        mask = bm_data["Date"] >= start_date
        fig_vol.add_trace(go.Scatter(
            x=bm_data.loc[mask, "Date"],
            y=vol[mask],
            name=BENCHMARK_LABELS[bm],
            line=dict(color=BENCHMARK_COLORS[bm], width=2),
            fill="tozeroy",
            fillcolor=BENCHMARK_COLORS[bm].replace(")", ", 0.08)").replace("rgb", "rgba") if "rgb" in BENCHMARK_COLORS[bm] else None,
            hovertemplate=(
                f"<b>{BENCHMARK_LABELS[bm]}</b><br>"
                "Date: %{x|%d %b %Y}<br>"
                "Vol: %{y:.1f}%<extra></extra>"
            ),
        ))

    # Threshold band: >50% is historically elevated
    fig_vol.add_hline(
        y=50, line_dash="dot", line_color="#EF553B", opacity=0.6,
        annotation_text="Historically elevated (50%)",
        annotation_position="right",
        annotation_font_size=10,
        annotation_font_color="#EF553B",
    )
    fig_vol.update_layout(
        yaxis_title="Annualized Volatility (%)",
        hovermode="x unified",
        height=280,
        margin=dict(l=10, r=10, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_vol, use_container_width=True)
