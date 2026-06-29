import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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
    ("2020-03-01", "2020-05-15", "rgba(239,85,59,0.09)", "COVID demand collapse"),
    ("2022-02-24", "2022-06-01", "rgba(255,165,0,0.12)", "Russia–Ukraine invasion"),
    ("2022-10-05", "2023-02-01", "rgba(100,100,255,0.08)", "OPEC+ deep cuts"),
    ("2023-10-07", "2024-03-01", "rgba(255,80,80,0.09)", "Middle East escalation"),
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
    yoy = (
        ((current["Close"] / year_ago["Close"]) - 1) * 100
        if year_ago is not None
        else None
    )

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
    horizon_months = {
        "3 Months": 3,
        "6 Months": 6,
        "1 Year": 12,
        "2 Years": 24,
        "5 Years": 60,
    }
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
                        x0=x0,
                        x1=x1,
                        fillcolor=color,
                        layer="below",
                        line_width=0,
                        annotation_text=label,
                        annotation_position="top left",
                        annotation_font_size=10,
                        annotation_font_color="gray",
                    )

        for bm in selected_bms:
            bm_data = df_filtered[df_filtered["benchmark"] == bm].sort_values("Date")
            if show_candles:
                fig_hist.add_trace(
                    go.Candlestick(
                        x=bm_data["Date"],
                        open=bm_data["Open"],
                        high=bm_data["High"],
                        low=bm_data["Low"],
                        close=bm_data["Close"],
                        name=BENCHMARK_LABELS[bm],
                        increasing_line_color=BENCHMARK_COLORS[bm],
                        decreasing_line_color="#EF553B",
                    )
                )
            else:
                fig_hist.add_trace(
                    go.Scatter(
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
                    )
                )

        fig_hist.update_layout(
            yaxis_title="Price (USD/bbl)",
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=460,
            margin=dict(l=10, r=10, t=40, b=20),
            xaxis_rangeslider_visible=False,
        )
        st.plotly_chart(fig_hist, width="stretch")

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
            st.caption(
                "Orange fill = Brent premium · Blue fill = WTI premium (rare) · Dashed = 30-day MA"
            )

            fig_spread = go.Figure()
            # Orange fill above zero (normal: Brent > WTI)
            fig_spread.add_trace(
                go.Scatter(
                    x=spread_filtered.index,
                    y=spread_filtered.clip(lower=0),
                    fill="tozeroy",
                    fillcolor="rgba(247,147,30,0.20)",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            # Blue fill below zero (WTI premium)
            fig_spread.add_trace(
                go.Scatter(
                    x=spread_filtered.index,
                    y=spread_filtered.clip(upper=0),
                    fill="tozeroy",
                    fillcolor="rgba(99,110,250,0.20)",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            # Spread line
            fig_spread.add_trace(
                go.Scatter(
                    x=spread_filtered.index,
                    y=spread_filtered,
                    name="Brent − WTI",
                    line=dict(color="#AB63FA", width=2),
                    hovertemplate="Date: %{x|%d %b %Y}<br>Spread: $%{y:.2f}/bbl<extra></extra>",
                )
            )
            # 30-day MA
            spread_ma = spread_filtered.rolling(30, min_periods=1).mean()
            fig_spread.add_trace(
                go.Scatter(
                    x=spread_ma.index,
                    y=spread_ma,
                    name="30d MA",
                    line=dict(color="gray", dash="dash", width=1.5),
                    hovertemplate="30d MA: $%{y:.2f}<extra></extra>",
                )
            )
            fig_spread.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.6)
            fig_spread.update_layout(
                yaxis_title="Spread (USD/bbl)",
                height=300,
                margin=dict(l=10, r=10, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_spread, width="stretch")

        with sp_col2:
            st.markdown("##### Spread Distribution")
            st.caption(
                "Histogram of daily spread values — shows where today's premium sits relative to history."
            )

            fig_dist = go.Figure()
            fig_dist.add_trace(
                go.Histogram(
                    x=spread_filtered,
                    nbinsx=40,
                    marker_color="#AB63FA",
                    opacity=0.75,
                    hovertemplate="Range: $%{x:.1f}/bbl<br>Days: %{y}<extra></extra>",
                    showlegend=False,
                )
            )
            fig_dist.add_vline(
                x=float(spread_filtered.mean()),
                line_dash="dash",
                line_color="#F7931E",
                annotation_text=f"Avg ${spread_filtered.mean():.2f}",
                annotation_position="top right",
            )
            fig_dist.add_vline(
                x=float(spread_now),
                line_dash="solid",
                line_color="#EF553B",
                annotation_text=f"Now ${spread_now:.2f}",
                annotation_position="top left",
            )
            fig_dist.update_layout(
                xaxis_title="Spread (USD/bbl)",
                yaxis_title="Trading Days",
                height=300,
                margin=dict(l=10, r=10, t=30, b=20),
            )
            st.plotly_chart(fig_dist, width="stretch")

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

# ── Price vs 12-Month MA ───────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("### 📊 Price vs 12-Month Moving Average")
    st.markdown(
        "Shows how far the current price sits above or below its **12-month (252-day) moving average**, "
        "expressed as a percentage deviation. "
        "The **+20% / −20% bands** act as mean-reversion thresholds: "
        "historically, sustained moves beyond these levels signal either a major supply shock (spikes above) "
        "or a demand collapse / over-supply regime (drops below), and tend to precede corrective moves back toward the MA. "
        "The MA itself is the trend anchor — when price crosses it from below it is a bullish momentum signal, and vice-versa."
    )

    smooth_deviation = st.toggle("Smooth series (3-month rolling avg)", value=False)

    fig_ma = go.Figure()

    for bm in BENCHMARKS:
        bm_data = df[df["benchmark"] == bm].sort_values("Date").reset_index(drop=True)
        ma252 = bm_data["Close"].rolling(252, min_periods=126).mean()
        deviation = ((bm_data["Close"] - ma252) / ma252 * 100).round(2)
        if smooth_deviation:
            deviation = deviation.rolling(63, min_periods=1).mean().round(2)

        mask = bm_data["Date"] >= start_date

        # Green fill when price is above MA, red fill when below
        fig_ma.add_trace(
            go.Scatter(
                x=bm_data.loc[mask, "Date"],
                y=deviation[mask].clip(lower=0),
                fill="tozeroy",
                fillcolor="rgba(0, 204, 150, 0.15)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig_ma.add_trace(
            go.Scatter(
                x=bm_data.loc[mask, "Date"],
                y=deviation[mask].clip(upper=0),
                fill="tozeroy",
                fillcolor="rgba(239, 85, 59, 0.15)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Deviation line
        fig_ma.add_trace(
            go.Scatter(
                x=bm_data.loc[mask, "Date"],
                y=deviation[mask],
                name=BENCHMARK_LABELS[bm],
                line=dict(color=BENCHMARK_COLORS[bm], width=2),
                hovertemplate=(
                    f"<b>{BENCHMARK_LABELS[bm]}</b><br>"
                    "Date: %{x|%d %b %Y}<br>"
                    "Deviation: %{y:+.1f}%<extra></extra>"
                ),
            )
        )

    # Zero line (price = MA)
    fig_ma.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

    # +20% threshold
    fig_ma.add_hline(
        y=20,
        line_dash="dash",
        line_color="rgba(0,204,150,0.8)",
        line_width=1.5,
        annotation_text="+20% — extended above trend",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="rgba(0,180,130,1)",
    )
    # −20% threshold
    fig_ma.add_hline(
        y=-20,
        line_dash="dash",
        line_color="rgba(239,85,59,0.8)",
        line_width=1.5,
        annotation_text="−20% — extended below trend",
        annotation_position="bottom right",
        annotation_font_size=11,
        annotation_font_color="rgba(239,85,59,1)",
    )

    fig_ma.update_layout(
        yaxis_title="Deviation from 12M MA (%)",
        yaxis_ticksuffix="%",
        hovermode="x unified",
        height=340,
        margin=dict(l=10, r=10, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_ma, width="stretch")

    # Live interpretation
    interp_cols = st.columns(len(BENCHMARKS))
    for i, bm in enumerate(BENCHMARKS):
        bm_data = df[df["benchmark"] == bm].sort_values("Date").reset_index(drop=True)
        ma252 = bm_data["Close"].rolling(252, min_periods=126).mean()
        deviation = (bm_data["Close"] - ma252) / ma252 * 100
        dev_now = deviation.dropna().iloc[-1]
        with interp_cols[i]:
            if dev_now > 20:
                st.warning(
                    f"**{BENCHMARK_LABELS[bm]}**: {dev_now:+.1f}% above MA — extended, watch for reversal."
                )
            elif dev_now < -20:
                st.error(
                    f"**{BENCHMARK_LABELS[bm]}**: {dev_now:+.1f}% below MA — deeply oversold."
                )
            elif dev_now > 0:
                st.success(
                    f"**{BENCHMARK_LABELS[bm]}**: {dev_now:+.1f}% — above trend, momentum positive."
                )
            else:
                st.info(
                    f"**{BENCHMARK_LABELS[bm]}**: {dev_now:+.1f}% — below trend, momentum negative."
                )

# ── European Fuel Prices ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## ⛽ European Fuel Prices")
st.markdown(
    "Weekly consumer pump prices (EUR/litre) for all EU member states, sourced from the "
    "[EC Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en). "
    "Prices are reported every Monday. Both pump prices (with taxes) and pre-tax prices (without taxes) "
    "are available, enabling tax-wedge decomposition and direct comparison with crude oil costs."
)


@st.cache_data
def load_fuel_data() -> pd.DataFrame:
    try:
        df_f = pd.read_parquet("data/ingested/eu_fuel/data.parquet")
        df_f["Date"] = pd.to_datetime(df_f["Date"])
        if df_f["Date"].dt.tz is not None:
            df_f["Date"] = df_f["Date"].dt.tz_localize(None)
        return df_f.sort_values(
            ["country_code", "fuel_type", "price_type", "Date"]
        ).reset_index(drop=True)
    except FileNotFoundError:
        st.error("EU fuel data not found. Please run `scripts/fetch_data.py` first.")
        st.stop()


fuel_df = load_fuel_data()

_fuel_country_name: dict[str, str] = dict(
    zip(fuel_df["country_code"], fuel_df["country"])
)
_member_codes: list[str] = sorted(
    c for c in fuel_df["country_code"].unique() if c not in ("EU", "EUR")
)
_FUEL_COLORS = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24

# ── Shared fuel controls ───────────────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns([0.32, 0.22, 0.22, 0.24])
with fc1:
    fuel_selected_countries = st.multiselect(
        "Countries",
        options=_member_codes,
        default=["PT", "DE", "ES", "FR"],
        format_func=lambda x: f"{_fuel_country_name.get(x, x)} ({x})",
        key="fuel_countries",
    )
with fc2:
    fuel_type_sel = st.selectbox(
        "Fuel type",
        options=["GASOLINE_95", "DIESEL"],
        format_func=lambda x: "Eurosuper 95" if x == "GASOLINE_95" else "Diesel",
        key="fuel_type",
    )
with fc3:
    price_type_sel = st.selectbox(
        "Price type",
        options=["with_tax", "without_tax"],
        format_func=lambda x: (
            "With taxes (pump)" if x == "with_tax" else "Without taxes (pre-tax)"
        ),
        key="fuel_price_type",
    )
with fc4:
    include_eu_avg = st.checkbox("Include EU average", value=True, key="fuel_eu_avg")

if not fuel_selected_countries:
    st.warning("Select at least one country.")
else:
    display_codes: list[str] = (["EU"] if include_eu_avg else []) + list(
        fuel_selected_countries
    )
    _color_map: dict[str, str] = {
        code: _FUEL_COLORS[i % len(_FUEL_COLORS)]
        for i, code in enumerate(display_codes)
    }
    _FUEL_LABEL = {"GASOLINE_95": "Eurosuper 95", "DIESEL": "Diesel"}
    _PRICE_LABEL = {"with_tax": "pump", "without_tax": "pre-tax"}

    fuel_filtered = fuel_df[
        (fuel_df["country_code"].isin(display_codes))
        & (fuel_df["fuel_type"] == fuel_type_sel)
        & (fuel_df["price_type"] == price_type_sel)
        & (fuel_df["Date"] >= start_date)
    ].copy()

    # ── KPI: Portugal snapshot ─────────────────────────────────────────────────
    if "PT" in display_codes:
        st.markdown("#### 📌 Portugal Snapshot")

        _pt_series = fuel_df[
            (fuel_df["country_code"] == "PT") & (fuel_df["fuel_type"] == fuel_type_sel)
        ]
        _eu_series = fuel_df[
            (fuel_df["country_code"] == "EU") & (fuel_df["fuel_type"] == fuel_type_sel)
        ]

        pt_pump = _pt_series[_pt_series["price_type"] == "with_tax"].sort_values("Date")
        pt_notax = _pt_series[_pt_series["price_type"] == "without_tax"].sort_values(
            "Date"
        )
        eu_pump = _eu_series[_eu_series["price_type"] == "with_tax"].sort_values("Date")

        if not pt_pump.empty and not pt_notax.empty and not eu_pump.empty:
            _pt_now = pt_pump.iloc[-1]
            _eu_now = eu_pump.iloc[-1]
            _pt_notax_now = pt_notax.iloc[-1]["price"]
            _tax_wedge = _pt_now["price"] - _pt_notax_now
            _tax_pct = _tax_wedge / _pt_now["price"] * 100

            _pt_yoy_cands = pt_pump[
                pt_pump["Date"] <= _pt_now["Date"] - pd.DateOffset(months=12)
            ]
            _yoy_base = (
                _pt_yoy_cands.iloc[-1]["price"] if not _pt_yoy_cands.empty else None
            )
            _yoy_pct = (_pt_now["price"] / _yoy_base - 1) * 100 if _yoy_base else None

            _brent_weekly = (
                df[df["benchmark"] == "BRENT"]
                .set_index("Date")["Close"]
                .resample("W-MON")
                .mean()
            )
            _pt_fuel_weekly = pt_pump.set_index("Date")["price"]
            _joined_kpi = pd.concat(
                [_brent_weekly, _pt_fuel_weekly], axis=1, join="inner"
            )
            _joined_kpi.columns = ["oil", "fuel"]
            _corr_all = _joined_kpi["oil"].corr(_joined_kpi["fuel"])

            kf1, kf2, kf3, kf4 = st.columns(4)
            with kf1:
                with st.container(border=True):
                    st.metric(
                        f"🇵🇹 PT {_FUEL_LABEL[fuel_type_sel]} ({_PRICE_LABEL[price_type_sel]})",
                        value=f"€{_pt_now['price']:.3f}/L",
                        delta=f"{_yoy_pct:+.1f}% YoY" if _yoy_pct is not None else None,
                    )
                    st.caption(f"As of {_pt_now['Date'].strftime('%d %b %Y')}")
            with kf2:
                with st.container(border=True):
                    _gap = _pt_now["price"] - _eu_now["price"]
                    st.metric(
                        "vs EU Average",
                        value=f"€{_eu_now['price']:.3f}/L",
                        delta=f"PT {_gap:+.3f} vs EU",
                        delta_color="inverse",
                    )
                    st.caption("Negative = cheaper than EU avg")
            with kf3:
                with st.container(border=True):
                    st.metric(
                        "🧾 Tax wedge (PT)",
                        value=f"€{_tax_wedge:.3f}/L",
                        delta=f"{_tax_pct:.1f}% of pump price",
                        delta_color="off",
                    )
            with kf4:
                with st.container(border=True):
                    st.metric(
                        "📐 Brent ↔ PT Fuel Corr",
                        value=f"{_corr_all:.2f}",
                        delta=f"Full history ({_joined_kpi.index.min().year}–{_joined_kpi.index.max().year})",
                        delta_color="off",
                    )

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_hist, tab_oil, tab_passthrough, tab_tax, tab_corr = st.tabs(
        [
            "📈 Price History",
            "🛢️ Oil vs Fuel",
            "⚡ Pass-Through Rate",
            "🧾 Tax Wedge",
            "🔗 Rolling Correlation",
        ]
    )

    with tab_hist:
        st.markdown(
            f"Weekly **{_FUEL_LABEL[fuel_type_sel]}** prices "
            f"({'pump price' if price_type_sel == 'with_tax' else 'pre-tax'}), EUR/litre."
        )
        fig_fuel_hist = go.Figure()
        for code in display_codes:
            cdf = fuel_filtered[fuel_filtered["country_code"] == code].sort_values(
                "Date"
            )
            if cdf.empty:
                continue
            name = _fuel_country_name.get(code, code)
            fig_fuel_hist.add_trace(
                go.Scatter(
                    x=cdf["Date"],
                    y=cdf["price"],
                    name=name,
                    line=dict(
                        color=_color_map[code],
                        width=2.5 if code in ("EU", "EUR") else 1.5,
                        dash="dash" if code in ("EU", "EUR") else "solid",
                    ),
                    mode="lines",
                    hovertemplate=(
                        f"<b>{name}</b><br>Date: %{{x|%d %b %Y}}<br>Price: €%{{y:.3f}}/L<extra></extra>"
                    ),
                )
            )
        fig_fuel_hist.update_layout(
            yaxis_title="EUR/litre",
            hovermode="x unified",
            height=420,
            margin=dict(l=10, r=10, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_fuel_hist, width="stretch")

    with tab_oil:
        st.markdown(
            "Normalized index (base = 100 at the earliest common date). "
            "Shows how crude oil price moves have transmitted into consumer fuel prices over time."
        )
        brent_weekly_norm = (
            df[df["benchmark"] == "BRENT"]
            .set_index("Date")["Close"]
            .resample("W-MON")
            .mean()
        )
        # Common start
        _country_starts = [
            fuel_filtered[fuel_filtered["country_code"] == c]["Date"].min()
            for c in display_codes
            if not fuel_filtered[fuel_filtered["country_code"] == c].empty
        ]
        _common_start = max(
            max(_country_starts) if _country_starts else start_date,
            brent_weekly_norm.dropna().index.min(),
            start_date,
        )
        brent_win = brent_weekly_norm[brent_weekly_norm.index >= _common_start].dropna()

        fig_norm = go.Figure()
        if not brent_win.empty:
            _base_oil = brent_win.iloc[0]
            fig_norm.add_trace(
                go.Scatter(
                    x=brent_win.index,
                    y=(brent_win / _base_oil * 100).round(2),
                    name="Brent Crude",
                    line=dict(color=BENCHMARK_COLORS["BRENT"], width=2.5),
                    mode="lines",
                    hovertemplate="<b>Brent</b><br>%{x|%d %b %Y}<br>Index: %{y:.1f}<extra></extra>",
                )
            )
        for code in display_codes:
            cdf = fuel_filtered[fuel_filtered["country_code"] == code].sort_values(
                "Date"
            )
            cdf = cdf[cdf["Date"] >= _common_start]
            if cdf.empty:
                continue
            _base_fuel = cdf["price"].iloc[0]
            name = _fuel_country_name.get(code, code)
            fig_norm.add_trace(
                go.Scatter(
                    x=cdf["Date"],
                    y=(cdf["price"] / _base_fuel * 100).round(2),
                    name=name,
                    line=dict(
                        color=_color_map[code],
                        width=1.5,
                        dash="dash" if code in ("EU", "EUR") else "solid",
                    ),
                    mode="lines",
                    hovertemplate=f"<b>{name}</b><br>%{{x|%d %b %Y}}<br>Index: %{{y:.1f}}<extra></extra>",
                )
            )
        fig_norm.add_hline(y=100, line_dash="dot", line_color="gray", opacity=0.4)
        fig_norm.update_layout(
            yaxis_title="Index (base = 100)",
            hovermode="x unified",
            height=420,
            margin=dict(l=10, r=10, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_norm, width="stretch")

    with tab_passthrough:
        st.markdown(
            "The **pass-through rate (β)** measures how much of a crude-oil price change "
            "is transmitted to consumer fuel prices. "
            "β ≈ **1.0** = full pass-through (every 1% rise in Brent → 1% rise in pump price); "
            "β < 1 = buffering by taxes, subsidies or refinery-margin absorption; "
            "β > 1 = amplification (FX effects, tight refinery capacity, or margin expansion).\n\n"
            "Computed as the rolling 52-week OLS slope (β) from regressing weekly **% changes** in "
            "fuel price on weekly % changes in Brent crude. Unlike correlation, β captures the "
            "**magnitude** of transmission — not just direction."
        )

        _brent_pt = (
            df[df["benchmark"] == "BRENT"]
            .set_index("Date")["Close"]
            .resample("W-MON")
            .mean()
        )

        pt_col_chart, pt_col_scatter = st.columns([0.62, 0.38])

        with pt_col_chart:
            fig_pt = go.Figure()
            for code in display_codes:
                _fseries_pt = fuel_df[
                    (fuel_df["country_code"] == code)
                    & (fuel_df["fuel_type"] == fuel_type_sel)
                    & (fuel_df["price_type"] == price_type_sel)
                ].set_index("Date")["price"]

                _joined_pt = pd.concat([_brent_pt, _fseries_pt], axis=1, join="inner")
                _joined_pt.columns = ["oil", "fuel"]
                _joined_pt = _joined_pt[_joined_pt.index >= start_date].dropna()

                if len(_joined_pt) < 26:
                    continue

                _oil_pct = _joined_pt["oil"].pct_change()
                _fuel_pct = _joined_pt["fuel"].pct_change()
                # Rolling OLS β = Cov(Δfuel%, Δoil%) / Var(Δoil%)
                _rolling_beta = (
                    _oil_pct.rolling(52, min_periods=26).cov(_fuel_pct)
                    / _oil_pct.rolling(52, min_periods=26).var()
                )
                _rolling_beta = _rolling_beta.dropna()
                name = _fuel_country_name.get(code, code)
                fig_pt.add_trace(
                    go.Scatter(
                        x=_rolling_beta.index,
                        y=_rolling_beta.round(3),
                        name=name,
                        line=dict(
                            color=_color_map[code],
                            width=1.5,
                            dash="dash" if code in ("EU", "EUR") else "solid",
                        ),
                        mode="lines",
                        hovertemplate=(
                            f"<b>{name}</b><br>%{{x|%d %b %Y}}<br>β: %{{y:.2f}}<extra></extra>"
                        ),
                    )
                )
            fig_pt.add_hline(
                y=1.0,
                line_dash="dash",
                line_color="rgba(0,204,150,0.7)",
                line_width=1.5,
                annotation_text="Full pass-through (β = 1)",
                annotation_font_size=10,
                annotation_font_color="rgba(0,204,150,1)",
            )
            fig_pt.add_hline(
                y=0.5,
                line_dash="dot",
                line_color="rgba(255,165,0,0.5)",
                line_width=1,
                annotation_text="50% pass-through",
                annotation_font_size=10,
                annotation_font_color="rgba(255,165,0,0.9)",
            )
            fig_pt.add_hline(y=0.0, line_dash="dot", line_color="gray", opacity=0.4)
            fig_pt.update_layout(
                yaxis_title="Pass-through β (52-week rolling)",
                hovermode="x unified",
                height=420,
                margin=dict(l=10, r=10, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_pt, width="stretch")

        with pt_col_scatter:
            st.markdown("**Weekly Δ% scatter** — full selected period")
            fig_sc = go.Figure()
            _x_all: list[float] = []
            for code in display_codes:
                _fseries_sc = fuel_df[
                    (fuel_df["country_code"] == code)
                    & (fuel_df["fuel_type"] == fuel_type_sel)
                    & (fuel_df["price_type"] == price_type_sel)
                ].set_index("Date")["price"]

                _joined_sc = pd.concat([_brent_pt, _fseries_sc], axis=1, join="inner")
                _joined_sc.columns = ["oil", "fuel"]
                _joined_sc = _joined_sc[_joined_sc.index >= start_date].dropna()
                if len(_joined_sc) < 4:
                    continue

                _x_sc = (_joined_sc["oil"].pct_change().dropna() * 100).round(2)
                _y_sc = (_joined_sc["fuel"].pct_change().dropna() * 100).round(2)
                _x_all.extend(_x_sc.tolist())
                name = _fuel_country_name.get(code, code)
                fig_sc.add_trace(
                    go.Scatter(
                        x=_x_sc,
                        y=_y_sc,
                        name=name,
                        mode="markers",
                        marker=dict(color=_color_map[code], size=4, opacity=0.45),
                        hovertemplate=(
                            f"<b>{name}</b><br>Brent Δ%: %{{x:.1f}}%<br>"
                            f"Fuel Δ%: %{{y:.1f}}%<extra></extra>"
                        ),
                    )
                )
            if _x_all:
                _xy_lim = max(abs(min(_x_all)), abs(max(_x_all)), 5)
                fig_sc.add_trace(
                    go.Scatter(
                        x=[-_xy_lim, _xy_lim],
                        y=[-_xy_lim, _xy_lim],
                        name="β = 1 (full)",
                        mode="lines",
                        line=dict(color="rgba(0,204,150,0.6)", dash="dash", width=1.5),
                        showlegend=True,
                    )
                )
            fig_sc.update_layout(
                xaxis_title="Brent weekly Δ%",
                yaxis_title="Fuel weekly Δ%",
                height=420,
                margin=dict(l=10, r=10, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=9)),
            )
            st.plotly_chart(fig_sc, width="stretch")

    with tab_tax:
        st.markdown(
            f"Tax wedge per country — pump price minus pre-tax price for "
            f"**{_FUEL_LABEL[fuel_type_sel]}**, as of the most recent reporting week. "
            "Highlighted bars are your selected countries."
        )
        _latest_fuel_date = fuel_df[
            (fuel_df["fuel_type"] == fuel_type_sel)
            & (fuel_df["country_code"].isin(_member_codes))
        ]["Date"].max()

        _with_col = fuel_df[
            (fuel_df["fuel_type"] == fuel_type_sel)
            & (fuel_df["price_type"] == "with_tax")
            & (fuel_df["Date"] == _latest_fuel_date)
            & (fuel_df["country_code"].isin(_member_codes))
        ].set_index("country_code")[["price", "country"]]

        _wo_col = (
            fuel_df[
                (fuel_df["fuel_type"] == fuel_type_sel)
                & (fuel_df["price_type"] == "without_tax")
                & (fuel_df["Date"] == _latest_fuel_date)
                & (fuel_df["country_code"].isin(_member_codes))
            ]
            .set_index("country_code")[["price"]]
            .rename(columns={"price": "price_wo"})
        )

        _tax_df = _with_col.join(_wo_col).dropna()
        _tax_df["tax_wedge"] = _tax_df["price"] - _tax_df["price_wo"]
        _tax_df["tax_pct"] = _tax_df["tax_wedge"] / _tax_df["price"] * 100
        _tax_df["label"] = _tax_df["country"] + " (" + _tax_df.index + ")"
        _tax_df = _tax_df.sort_values("tax_wedge", ascending=False)

        _bar_colors = [
            "#F7931E" if c in fuel_selected_countries else "rgba(99,110,250,0.65)"
            for c in _tax_df.index
        ]
        fig_tax = go.Figure()
        fig_tax.add_trace(
            go.Bar(
                x=_tax_df["label"],
                y=_tax_df["tax_wedge"],
                marker_color=_bar_colors,
                customdata=_tax_df[["price", "price_wo", "tax_pct"]].values,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Pump price: €%{customdata[0]:.3f}/L<br>"
                    "Pre-tax: €%{customdata[1]:.3f}/L<br>"
                    "Tax wedge: €%{y:.3f}/L (%{customdata[2]:.1f}%)<extra></extra>"
                ),
                showlegend=False,
            )
        )

        _eu_w = fuel_df[
            (fuel_df["country_code"] == "EU")
            & (fuel_df["fuel_type"] == fuel_type_sel)
            & (fuel_df["price_type"] == "with_tax")
            & (fuel_df["Date"] == _latest_fuel_date)
        ]
        _eu_wo = fuel_df[
            (fuel_df["country_code"] == "EU")
            & (fuel_df["fuel_type"] == fuel_type_sel)
            & (fuel_df["price_type"] == "without_tax")
            & (fuel_df["Date"] == _latest_fuel_date)
        ]
        if not _eu_w.empty and not _eu_wo.empty:
            _eu_wedge = float(_eu_w.iloc[0]["price"] - _eu_wo.iloc[0]["price"])
            fig_tax.add_hline(
                y=_eu_wedge,
                line_dash="dash",
                line_color="white",
                opacity=0.7,
                annotation_text=f"EU avg €{_eu_wedge:.3f}/L",
                annotation_position="top right",
                annotation_font_size=11,
            )

        fig_tax.update_layout(
            yaxis_title="Tax wedge (EUR/litre)",
            height=420,
            margin=dict(l=10, r=10, t=30, b=110),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_tax, width="stretch")
        st.caption(
            f"As of {_latest_fuel_date.strftime('%d %b %Y')}. "
            "Orange = selected countries. "
            "Dashed line = EU weighted average."
        )

    with tab_corr:
        st.markdown(
            "Rolling 52-week Pearson correlation between weekly **Brent crude** price "
            "and consumer fuel prices per country. "
            "A coefficient near 1 means pump prices track crude oil tightly; "
            "lower values signal domestic factors (taxes, subsidies, regulation lag) dominating."
        )
        _brent_for_corr = (
            df[df["benchmark"] == "BRENT"]
            .set_index("Date")["Close"]
            .resample("W-MON")
            .mean()
        )
        fig_corr = go.Figure()
        for code in display_codes:
            _fseries = fuel_df[
                (fuel_df["country_code"] == code)
                & (fuel_df["fuel_type"] == fuel_type_sel)
                & (fuel_df["price_type"] == price_type_sel)
            ].set_index("Date")["price"]

            _joined = pd.concat([_brent_for_corr, _fseries], axis=1, join="inner")
            _joined.columns = ["oil", "fuel"]
            _rolling_corr = (
                _joined["oil"].rolling(52, min_periods=26).corr(_joined["fuel"])
            )
            _rolling_corr = _rolling_corr[_rolling_corr.index >= start_date].dropna()
            if _rolling_corr.empty:
                continue
            name = _fuel_country_name.get(code, code)
            fig_corr.add_trace(
                go.Scatter(
                    x=_rolling_corr.index,
                    y=_rolling_corr.round(3),
                    name=name,
                    line=dict(
                        color=_color_map[code],
                        width=1.5,
                        dash="dash" if code in ("EU", "EUR") else "solid",
                    ),
                    mode="lines",
                    hovertemplate=(
                        f"<b>{name}</b><br>%{{x|%d %b %Y}}<br>Corr: %{{y:.2f}}<extra></extra>"
                    ),
                )
            )
        fig_corr.add_hline(
            y=0.7,
            line_dash="dot",
            line_color="rgba(0,204,150,0.7)",
            line_width=1.5,
            annotation_text="High (0.7)",
            annotation_font_size=10,
            annotation_font_color="rgba(0,204,150,1)",
        )
        fig_corr.add_hline(y=0.0, line_dash="dot", line_color="gray", opacity=0.4)
        fig_corr.update_layout(
            yaxis_title="Pearson r (52-week rolling)",
            yaxis_range=[-0.3, 1.05],
            hovermode="x unified",
            height=420,
            margin=dict(l=10, r=10, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_corr, width="stretch")
