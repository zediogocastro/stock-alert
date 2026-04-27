import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("📉 Euribor Rate Monitor")
st.markdown(
    "Monthly averages of the **European Interbank Offered Rate (EURIBOR)** across all standard maturities, "
    "sourced from the ECB Statistical Data Warehouse."
)

# ── Constants ─────────────────────────────────────────────────────────────────
TENORS = ["1M", "3M", "6M", "12M"]
TENOR_LABELS = {"1M": "1-Month", "3M": "3-Month", "6M": "6-Month", "12M": "12-Month"}
TENOR_COLORS = {"1M": "#636EFA", "3M": "#EF553B", "6M": "#00CC96", "12M": "#AB63FA"}


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet("data/ingested/euribor/data.parquet")
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values(["tenor", "Date"]).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error("Euribor data not found. Please run `scripts/fetch_data.py` first.")
        st.stop()


df = load_data()
latest_date = df["Date"].max()

# ── Current Rates KPIs ────────────────────────────────────────────────────────
st.markdown("### 📌 Current Rates")
kpi_cols = st.columns(4)

for i, tenor in enumerate(TENORS):
    tenor_df = df[df["tenor"] == tenor].sort_values("Date")
    current = tenor_df.iloc[-1]
    prev_m = tenor_df.iloc[-2] if len(tenor_df) >= 2 else current
    year_ago_candidates = tenor_df[
        tenor_df["Date"] <= current["Date"] - pd.DateOffset(months=12)
    ]
    year_ago = year_ago_candidates.iloc[-1] if not year_ago_candidates.empty else None

    mom = current["rate"] - prev_m["rate"]
    yoy = (current["rate"] - year_ago["rate"]) if year_ago is not None else None

    with kpi_cols[i]:
        with st.container(border=True):
            st.metric(
                label=f"EURIBOR {tenor} ({TENOR_LABELS[tenor]})",
                value=f"{current['rate']:.3f}%",
                delta=f"{mom:+.3f}% MoM",
                delta_color="inverse",  # rising rates = red (bad for borrowers)
            )
            if yoy is not None:
                arrow = "🔴" if yoy > 0.05 else ("🟢" if yoy < -0.05 else "⚪")
                st.caption(f"{arrow} YoY: {yoy:+.3f}%")
            st.caption(f"As of {current['Date'].strftime('%b %Y')}")

st.markdown("---")

# ── Layout: Controls  |  Historical Chart ─────────────────────────────────────
col_left, col_right = st.columns([0.28, 0.72])

with col_left:
    with st.container(border=True):
        st.markdown("#### ⚙️ Filters")
        selected_tenors = st.multiselect(
            "Tenors",
            options=TENORS,
            default=TENORS,
            format_func=lambda x: f"{x} — {TENOR_LABELS[x]}",
        )
        time_horizon = st.radio(
            "Time horizon",
            ["1 Year", "3 Years", "5 Years", "10 Years", "All"],
            index=2,
            horizontal=True,
        )
        show_regimes = st.toggle("Highlight rate regimes", value=True)

    if not selected_tenors:
        st.warning("Select at least one tenor.")
        st.stop()

    # Compute date range
    end_date = latest_date
    horizon_months = {"1 Year": 12, "3 Years": 36, "5 Years": 60, "10 Years": 120}
    if time_horizon in horizon_months:
        start_date = end_date - pd.DateOffset(months=horizon_months[time_horizon])
    else:
        start_date = df["Date"].min()

    df_filtered = df[
        (df["tenor"].isin(selected_tenors)) & (df["Date"] >= start_date)
    ].copy()

    # ── Period Stats ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📊 Period Statistics")
        for tenor in selected_tenors:
            t_rates = df_filtered[df_filtered["tenor"] == tenor]["rate"].dropna()
            if not t_rates.empty:
                st.markdown(f"**EURIBOR {tenor}**")
                s1, s2, s3 = st.columns(3)
                s1.metric("Min", f"{t_rates.min():.2f}%")
                s2.metric("Avg", f"{t_rates.mean():.2f}%")
                s3.metric("Max", f"{t_rates.max():.2f}%")

with col_right:
    with st.container(border=True):
        st.markdown("#### 📈 Historical Rates")
        fig_hist = go.Figure()

        if show_regimes:
            # Negative rates era (ECB deposit rate went negative in Jun 2014, Euribor followed ~mid 2015)
            fig_hist.add_vrect(
                x0="2015-01-01",
                x1="2022-06-01",
                fillcolor="rgba(239, 85, 59, 0.07)",
                layer="below",
                line_width=0,
                annotation_text="Negative rate era",
                annotation_position="top left",
                annotation_font_size=11,
                annotation_font_color="gray",
            )
            # ECB hiking cycle
            fig_hist.add_vrect(
                x0="2022-07-01",
                x1=latest_date.strftime("%Y-%m-%d"),
                fillcolor="rgba(255, 200, 0, 0.09)",
                layer="below",
                line_width=0,
                annotation_text="ECB hiking cycle",
                annotation_position="top left",
                annotation_font_size=11,
                annotation_font_color="gray",
            )

        for tenor in selected_tenors:
            t_data = df_filtered[df_filtered["tenor"] == tenor].sort_values("Date")
            fig_hist.add_trace(
                go.Scatter(
                    x=t_data["Date"],
                    y=t_data["rate"],
                    name=f"EURIBOR {tenor}",
                    line=dict(color=TENOR_COLORS[tenor], width=2),
                    mode="lines",
                    hovertemplate=(
                        f"<b>EURIBOR {tenor}</b><br>"
                        "Date: %{x|%b %Y}<br>"
                        "Rate: %{y:.3f}%<extra></extra>"
                    ),
                )
            )

        fig_hist.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            opacity=0.7,
            annotation_text="0%",
            annotation_position="right",
        )
        fig_hist.update_layout(
            yaxis_title="Rate (%)",
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=460,
            margin=dict(l=10, r=10, t=40, b=20),
        )
        st.plotly_chart(fig_hist, width="stretch")

# ── Term Structure + Spread ────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("### 📐 Term Structure & Spread Analysis")

    ts_col1, ts_col2 = st.columns(2)

    # Pivot full history for spread computation
    spread_df = df.pivot(index="Date", columns="tenor", values="rate").sort_index()
    for col in TENORS:
        if col not in spread_df.columns:
            spread_df[col] = float("nan")
    spread_df["12M-3M"] = spread_df["12M"] - spread_df["3M"]
    spread_df["6M-3M"] = spread_df["6M"] - spread_df["3M"]
    spread_filtered = spread_df[spread_df.index >= start_date].dropna(subset=["12M-3M"])

    with ts_col1:
        st.markdown("##### Current vs 1 Year Ago — Term Structure")

        one_year_ago = latest_date - pd.DateOffset(years=1)
        current_rates = {
            t: df[df["tenor"] == t].sort_values("Date").iloc[-1]["rate"] for t in TENORS
        }
        year_ago_rates = {}
        for t in TENORS:
            t_df = df[df["tenor"] == t].sort_values("Date")
            m = t_df[t_df["Date"] <= one_year_ago]
            year_ago_rates[t] = m.iloc[-1]["rate"] if not m.empty else None

        fig_ts = go.Figure()
        fig_ts.add_trace(
            go.Scatter(
                x=TENORS,
                y=[current_rates[t] for t in TENORS],
                name=f"Now ({latest_date.strftime('%b %Y')})",
                mode="lines+markers",
                line=dict(color="#636EFA", width=3),
                marker=dict(size=12, symbol="circle"),
            )
        )
        fig_ts.add_trace(
            go.Scatter(
                x=TENORS,
                y=[year_ago_rates[t] for t in TENORS],
                name=f"1Y ago ({one_year_ago.strftime('%b %Y')})",
                mode="lines+markers",
                line=dict(color="#EF553B", dash="dash", width=2),
                marker=dict(size=9, symbol="diamond"),
            )
        )
        fig_ts.update_layout(
            yaxis_title="Rate (%)",
            xaxis_title="Maturity",
            height=320,
            margin=dict(l=10, r=10, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_ts, width="stretch")

        # Curve shape interpretation
        spread_now = current_rates["12M"] - current_rates["3M"]
        if spread_now > 0.1:
            shape_msg = "🟢 **Normal curve** — longer maturities yield more. Market expects rates to stay elevated or gradually decline."
        elif spread_now < -0.1:
            shape_msg = "🔴 **Inverted curve** — short rates exceed long rates. Historically a signal of expected rate cuts ahead."
        else:
            shape_msg = "⚪ **Flat curve** — minimal term premium between 3M and 12M. Market is uncertain about policy direction."
        st.info(f"{shape_msg} *(12M – 3M spread: {spread_now:+.3f} pp)*")

    with ts_col2:
        st.markdown("##### 12M — 3M Spread (Curve Steepness)")
        st.caption(
            "Positive = normal · Negative = inverted · Reflects market expectations for future ECB policy rates."
        )

        spread_series = spread_filtered["12M-3M"]
        fig_spread = go.Figure()

        # Green fill for positive spread
        fig_spread.add_trace(
            go.Scatter(
                x=spread_series.index,
                y=spread_series.clip(lower=0),
                fill="tozeroy",
                fillcolor="rgba(0, 204, 150, 0.25)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Red fill for negative spread
        fig_spread.add_trace(
            go.Scatter(
                x=spread_series.index,
                y=spread_series.clip(upper=0),
                fill="tozeroy",
                fillcolor="rgba(239, 85, 59, 0.25)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Spread line
        fig_spread.add_trace(
            go.Scatter(
                x=spread_series.index,
                y=spread_series,
                name="12M − 3M",
                line=dict(color="#AB63FA", width=2),
                hovertemplate="Date: %{x|%b %Y}<br>Spread: %{y:.3f} pp<extra></extra>",
            )
        )
        fig_spread.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.8)
        fig_spread.update_layout(
            yaxis_title="Spread (pp)",
            height=320,
            margin=dict(l=10, r=10, t=30, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_spread, width="stretch")

# ── Month-over-Month Change Heatmap ───────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("### 🗓️ Month-over-Month Rate Changes")
    st.markdown(
        "Rate change expressed in **basis points (bp)** relative to the previous month. "
        "Green = rates fell · Red = rates rose."
    )

    heatmap_tenor = st.selectbox("Select tenor for heatmap", TENORS, index=1)
    tenor_series = df[df["tenor"] == heatmap_tenor].sort_values("Date").copy()
    tenor_series["change_bp"] = (tenor_series["rate"].diff() * 100).round(1)
    tenor_series["year"] = tenor_series["Date"].dt.year
    tenor_series["month"] = tenor_series["Date"].dt.month

    recent_years = sorted(tenor_series["year"].unique())[-12:]
    heat_data = tenor_series[tenor_series["year"].isin(recent_years)]
    pivot = heat_data.pivot(index="year", columns="month", values="change_bp")

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    pivot.columns = [month_names[m - 1] for m in pivot.columns]

    valid = pivot.values[~pd.isna(pivot.values)]
    max_abs = max(abs(valid).max(), 1) if len(valid) > 0 else 1

    fig_heat = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[str(y) for y in pivot.index.tolist()],
            colorscale="RdYlGn",  # green = fell, red = rose
            zmid=0,
            zmin=-max_abs,
            zmax=max_abs,
            text=pivot.round(1).values,
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate="Month: %{x}<br>Year: %{y}<br>Change: %{z:.1f} bp<extra></extra>",
            colorbar=dict(title="bp"),
        )
    )
    fig_heat.update_layout(
        yaxis=dict(autorange="reversed", type="category"),
        xaxis_title="Month",
        yaxis_title="Year",
        height=360,
        margin=dict(l=10, r=10, t=20, b=20),
    )
    st.plotly_chart(fig_heat, width="stretch")

# ── Raw Data Table ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Raw Data", expanded=False):
    display_df = df_filtered[["Date", "tenor", "rate", "identifier"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m")
    display_df["rate"] = display_df["rate"].round(4)
    display_df = display_df.sort_values(["Date", "tenor"], ascending=[False, True])
    st.dataframe(display_df, width="stretch", hide_index=True)
