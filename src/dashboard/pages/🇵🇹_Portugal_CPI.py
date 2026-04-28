import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("🇵🇹 Portugal CPI Monitor")
st.markdown(
    "Monthly **Consumer Price Index (CPI)** year-on-year growth rates for Portugal "
    "by COICOP category, sourced from **Statistics Portugal (INE)**. Base year: 2025."
)

# ── Constants ─────────────────────────────────────────────────────────────────
# Top-level COICOP codes to show in breakdown / KPI cards
TOP_LEVEL_CODES = ["T", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13"]

TOP_LEVEL_LABELS = {
    "T":  "Total CPI",
    "01": "Food & Non-Alcoholic Beverages",
    "02": "Alcoholic Beverages & Tobacco",
    "03": "Clothing & Footwear",
    "04": "Housing, Water, Energy & Fuels",
    "05": "Furnishings & Household Equipment",
    "06": "Health",
    "07": "Transport",
    "08": "Information & Communication",
    "09": "Recreation, Sport & Culture",
    "10": "Education",
    "11": "Restaurants & Accommodation",
    "12": "Insurance & Financial Services",
    "13": "Personal Care & Social Protection",
}

KPI_CODES = ["T", "01", "07", "11"]
KPI_LABELS = {
    "T":  "Total CPI",
    "01": "Food & Beverages",
    "07": "Transport",
    "11": "Restaurants & Hotels",
}
KPI_DELTA_COLOR = {
    "T":  "normal",
    "01": "normal",
    "07": "normal",
    "11": "normal",
}


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet("data/ingested/portugal_cpi/data.parquet")
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values(["coicop_code", "Date"]).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error(
            "Portugal CPI data not found. Please run `scripts/fetch_data.py` first."
        )
        st.stop()


df = load_data()
latest_date = df["Date"].max()
latest_df = df[df["Date"] == latest_date]

# Filter to top-level COICOP codes for the breakdown view
top_df = df[df["coicop_code"].isin(TOP_LEVEL_CODES)].copy()
top_latest = latest_df[latest_df["coicop_code"].isin(TOP_LEVEL_CODES)].copy()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown(f"### 📌 Latest Reading — {latest_date.strftime('%B %Y')}")
kpi_cols = st.columns(4)

for i, code in enumerate(KPI_CODES):
    series = top_df[top_df["coicop_code"] == code].sort_values("Date")
    if series.empty:
        continue
    current = series.iloc[-1]
    prev_m = series.iloc[-2] if len(series) >= 2 else None

    with kpi_cols[i]:
        with st.container(border=True):
            mom_str = None
            if prev_m is not None:
                mom = current["rate_yoy"] - prev_m["rate_yoy"]
                mom_str = f"{mom:+.2f} pp MoM"

            st.metric(
                label=KPI_LABELS[code],
                value=f"{current['rate_yoy']:.1f}%",
                delta=mom_str,
                delta_color="normal",
            )
            st.caption(f"YoY CPI — {current['Date'].strftime('%b %Y')}")

st.markdown("---")

# ── Layout: Sidebar Controls + Main Charts ────────────────────────────────────
col_left, col_right = st.columns([0.26, 0.74])

with col_left:
    with st.container(border=True):
        st.markdown("#### ⚙️ Filters")

        available_codes = [c for c in TOP_LEVEL_CODES if c != "T"]
        selected_codes = st.multiselect(
            "Categories (trend chart)",
            options=available_codes,
            default=["01", "04", "06", "07", "11"],
            format_func=lambda c: f"{c} — {TOP_LEVEL_LABELS.get(c, c)}",
        )

        time_horizon = st.radio(
            "Time horizon",
            ["1 Year", "2 Years", "3 Years", "All"],
            index=0,
        )

        show_total = st.checkbox("Overlay Total CPI", value=True)

# ── Breakdown Bar Chart (latest month) ───────────────────────────────────────
with col_right:
    with st.container(border=True):
        st.markdown(f"#### 📊 CPI by Category — {latest_date.strftime('%B %Y')}")

        bar_df = (
            top_latest[top_latest["coicop_code"] != "T"]
            .dropna(subset=["rate_yoy"])
            .sort_values("rate_yoy")
            .copy()
        )
        bar_df["label"] = bar_df["coicop_code"].map(TOP_LEVEL_LABELS)

        bar_colors = [
            "#EF553B" if v > 0 else "#00CC96" for v in bar_df["rate_yoy"]
        ]

        fig_bar = go.Figure(
            go.Bar(
                x=bar_df["rate_yoy"],
                y=bar_df["label"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:+.1f}%" for v in bar_df["rate_yoy"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Rate: %{x:.2f}%<extra></extra>",
            )
        )
        total_rate = top_latest[top_latest["coicop_code"] == "T"]["rate_yoy"]
        if not total_rate.empty:
            fig_bar.add_vline(
                x=total_rate.iloc[0],
                line_dash="dash",
                line_color="white",
                opacity=0.6,
                annotation_text=f"Total {total_rate.iloc[0]:.1f}%",
                annotation_position="top",
                annotation_font_size=11,
                annotation_font_color="white",
            )
        fig_bar.update_layout(
            xaxis_title="YoY Growth Rate (%)",
            xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=1),
            height=420,
            margin=dict(l=10, r=80, t=20, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, width="stretch")

# ── Historical Trend Chart ────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("#### 📈 Historical Trend")

    n_months = df["Date"].nunique()
    if n_months < 2:
        st.info(
            "Not enough history yet for trend lines. "
            "Run `scripts/fetch_data.py` each month to accumulate data."
        )
    else:
        # Apply time horizon filter
        horizon_map = {
            "1 Year": 12,
            "2 Years": 24,
            "3 Years": 36,
            "All": None,
        }
        months_back = horizon_map[time_horizon]
        if months_back is not None:
            start_date = latest_date - pd.DateOffset(months=months_back)
            trend_df = top_df[top_df["Date"] >= start_date]
        else:
            trend_df = top_df

        codes_to_plot = (["T"] if show_total else []) + list(selected_codes)

        COLORS = [
            "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
            "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
            "#B82E2E", "#316395", "#994499", "#22AA99",
        ]
        color_map = {code: COLORS[i % len(COLORS)] for i, code in enumerate(TOP_LEVEL_CODES)}
        color_map["T"] = "white"

        fig_trend = go.Figure()

        for code in codes_to_plot:
            series = trend_df[trend_df["coicop_code"] == code].sort_values("Date")
            if series.empty:
                continue
            label = TOP_LEVEL_LABELS.get(code, code)
            is_total = code == "T"
            fig_trend.add_trace(
                go.Scatter(
                    x=series["Date"],
                    y=series["rate_yoy"],
                    name=label,
                    line=dict(
                        color=color_map.get(code, "#888"),
                        width=3 if is_total else 1.5,
                        dash="dot" if is_total else "solid",
                    ),
                    mode="lines+markers" if not is_total else "lines",
                    marker=dict(size=5),
                    hovertemplate=(
                        f"<b>{label}</b><br>"
                        "Date: %{x|%b %Y}<br>"
                        "Rate: %{y:.2f}%<extra></extra>"
                    ),
                )
            )

        fig_trend.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            opacity=0.5,
            annotation_text="0%",
            annotation_position="right",
        )
        fig_trend.update_layout(
            yaxis_title="YoY Growth Rate (%)",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            height=460,
            margin=dict(l=10, r=10, t=40, b=20),
        )
        st.plotly_chart(fig_trend, width="stretch")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Data: Statistics Portugal (INE) — indicator 0014647 (CPI YoY%, base 2025). "
    f"Last fetched: {latest_date.strftime('%B %Y')}. "
    "Data accumulates with each run of `fetch_data.py`."
)
