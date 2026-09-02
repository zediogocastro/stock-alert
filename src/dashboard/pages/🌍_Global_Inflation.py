import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Global Inflation", page_icon="🌍")

st.title("🌍 Global Inflation Monitor")
st.markdown(
    "Monthly **CPI/HICP year-on-year inflation rates** for 47+ economies, sourced from "
    "**Eurostat & ECB** (EU/EEA countries) and **OECD Data Explorer** (non-EU members + G20 emerging). "
    "Official Eurostat & ECB HICP data takes precedence for European coverage."
)

# ── ISO-2 → ISO-3 mapping (for Plotly choropleth) ────────────────────────────
ISO2_TO_ISO3: dict[str, str] = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DK": "DNK", "EE": "EST", "ES": "ESP", "FI": "FIN",
    "FR": "FRA", "GR": "GRC", "HR": "HRV", "HU": "HUN", "IE": "IRL",
    "IT": "ITA", "LT": "LTU", "LU": "LUX", "LV": "LVA", "MT": "MLT",
    "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU", "SE": "SWE",
    "SI": "SVN", "SK": "SVK",
    # OECD non-EU
    "AU": "AUS", "CA": "CAN", "CL": "CHL", "CO": "COL", "GB": "GBR",
    "IS": "ISL", "IL": "ISR", "JP": "JPN", "KR": "KOR", "MX": "MEX",
    "NO": "NOR", "NZ": "NZL", "CH": "CHE", "TR": "TUR", "US": "USA",
    "BR": "BRA", "CN": "CHN", "IN": "IND", "ID": "IDN", "ZA": "ZAF",
    # Other European
    "AL": "ALB", "ME": "MNE", "MK": "MKD", "RS": "SRB", "XK": "XKX",
}

# Region groupings
REGION_GROUPS: dict[str, list[str]] = {
    "EU Countries": [
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
        "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    ],
    "OECD Non-EU": [
        "AU", "CA", "CL", "CO", "GB", "IS", "IL", "JP", "KR", "MX",
        "NO", "NZ", "CH", "TR", "US",
    ],
    "G20 Emerging": ["BR", "CN", "IN", "ID", "ZA"],
    "Other Europe": ["AL", "ME", "MK", "RS", "XK"],
}

# Hero KPI countries: (country_code, display_label)
HERO_COUNTRIES = [
    ("U2", "🇪🇺 Eurozone"),
    ("US", "🇺🇸 United States"),
    ("DE", "🇩🇪 Germany"),
    ("CN", "🇨🇳 China"),
]

# Color palette for trend lines
LINE_COLORS = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
    "#B82E2E", "#316395", "#994499", "#22AA99", "#AAAA11",
    "#6633CC", "#E67300", "#8B0707", "#329262", "#5574A6",
]


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet("data/ingested/inflation/data.parquet")
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values(["country_code", "Date"]).reset_index(drop=True)
        return df
    except FileNotFoundError:
        st.error(
            "Inflation data not found. Please run `scripts/fetch_data.py` first."
        )
        st.stop()


df = load_data()
all_countries_df = df[~df["country_code"].isin(["U2", "EU"])].copy()
all_country_names = (
    all_countries_df[["country_code", "country_name"]]
    .drop_duplicates()
    .sort_values("country_name")
)
latest_df = (
    df.sort_values(["country_code", "Date"])
    .groupby("country_code", as_index=False)
    .tail(1)
    .reset_index(drop=True)
)
latest_date = latest_df["Date"].max()
oldest_latest_date = latest_df["Date"].min()
latest_individual = latest_df[~latest_df["country_code"].isin(["U2", "EU"])].copy()

# ── KPI Hero Cards ────────────────────────────────────────────────────────────
st.markdown("### 📌 Key Economies — Latest Available")
if oldest_latest_date < latest_date:
    lagging_series = int((latest_df["Date"] < latest_date).sum())
    st.caption(
        f"Release window across series: **{oldest_latest_date.strftime('%b %Y')}** to "
        f"**{latest_date.strftime('%b %Y')}** · "
        f"{lagging_series} series are behind the newest release month."
    )
kpi_cols = st.columns(4)

for i, (code, label) in enumerate(HERO_COUNTRIES):
    series = df[df["country_code"] == code].sort_values("Date")
    if series.empty:
        continue
    current = series.iloc[-1]
    prev_m = series.iloc[-2] if len(series) >= 2 else None

    with kpi_cols[i]:
        with st.container(border=True):
            mom_str = None
            if prev_m is not None:
                mom = current["inflation_rate"] - prev_m["inflation_rate"]
                mom_str = f"{mom:+.2f} pp MoM"

            rate = current["inflation_rate"]
            trend_emoji = "🔴" if rate > 4 else ("🟡" if rate > 2 else "🟢")
            st.metric(
                label=f"{label}",
                value=f"{rate:.1f}%",
                delta=mom_str,
                delta_color="inverse",  # rising inflation = red (bad)
            )
            st.caption(f"{trend_emoji} YoY CPI — {current['Date'].strftime('%b %Y')} · Source: {current['source']}")

st.markdown("---")

# ── Layout: Controls | Charts ─────────────────────────────────────────────────
col_ctrl, col_main = st.columns([0.24, 0.76])

with col_ctrl:
    with st.container(border=True):
        st.markdown("#### ⚙️ Filters")

        region_choice = st.radio(
            "Region",
            ["All", "EU Countries", "OECD Non-EU", "G20 Emerging", "Other Europe"],
            index=0,
        )

        time_horizon = st.radio(
            "Time horizon",
            ["1 Year", "2 Years", "5 Years", "All"],
            index=0,
        )

        # Country multiselect scoped to region
        if region_choice == "All":
            eligible_codes = all_country_names["country_code"].tolist()
        else:
            region_codes = set(REGION_GROUPS[region_choice])
            eligible_codes = all_country_names[
                all_country_names["country_code"].isin(region_codes)
            ]["country_code"].tolist()

        eligible_names_map = (
            all_country_names[all_country_names["country_code"].isin(eligible_codes)]
            .set_index("country_code")["country_name"]
            .to_dict()
        )

        default_codes = ["DE", "FR", "US", "GB", "JP", "CN", "BR"]
        default_sel = [c for c in default_codes if c in eligible_codes]

        selected_codes = st.multiselect(
            "Countries (trend & heatmap)",
            options=eligible_codes,
            default=default_sel,
            format_func=lambda c: eligible_names_map.get(c, c),
        )

        show_eurozone = st.toggle("Overlay Eurozone on trend", value=True)
        show_ecb_target = st.toggle("Show ECB 2% target line", value=True)

        st.markdown("---")
        st.markdown("#### 📅 Data Coverage")
        min_date = df["Date"].min()
        st.caption(
            f"From **{min_date.strftime('%b %Y')}** to **{latest_date.strftime('%b %Y')}**  \n"
            f"Latest-by-country window: **{oldest_latest_date.strftime('%b %Y')}** to **{latest_date.strftime('%b %Y')}**  \n"
            f"{df['country_code'].nunique()} series · "
            f"{df['Date'].nunique()} months"
        )

# ── Compute date range for filtered views ────────────────────────────────────
horizon_months = {"1 Year": 12, "2 Years": 24, "5 Years": 60}
if time_horizon in horizon_months:
    start_date = latest_date - pd.DateOffset(months=horizon_months[time_horizon])
else:
    start_date = df["Date"].min()

with col_main:
    # ── World Choropleth ──────────────────────────────────────────────────────
    with st.container(border=True):
        if oldest_latest_date == latest_date:
            map_title_suffix = latest_date.strftime('%B %Y')
        else:
            map_title_suffix = (
                f"Latest by country ({oldest_latest_date.strftime('%b %Y')} to "
                f"{latest_date.strftime('%b %Y')})"
            )
        st.markdown(f"#### 🗺️ World Inflation Map — {map_title_suffix}")

        map_df = latest_individual.copy()
        map_df["period_label"] = map_df["Date"].dt.strftime("%b %Y")
        map_df["iso3"] = map_df["country_code"].map(ISO2_TO_ISO3)
        map_df = map_df.dropna(subset=["iso3", "inflation_rate"])

        abs_max = max(abs(map_df["inflation_rate"].min()), abs(map_df["inflation_rate"].max()))
        color_range = [-abs_max, abs_max]

        fig_map = go.Figure(
            go.Choropleth(
                locations=map_df["iso3"],
                z=map_df["inflation_rate"],
                text=map_df["country_name"],
                customdata=map_df[["source", "country_name", "period_label"]],
                colorscale="RdBu_r",
                zmin=color_range[0],
                zmax=color_range[1],
                colorbar=dict(
                    title=dict(text="YoY %", font=dict(size=12)),
                    thickness=14,
                    len=0.75,
                ),
                marker_line_color="rgba(255,255,255,0.3)",
                marker_line_width=0.5,
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "Inflation: <b>%{z:.2f}%</b><br>"
                    "Source: %{customdata[0]}<br>"
                    "Period: %{customdata[2]}"
                    "<extra></extra>"
                ),
            )
        )
        fig_map.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor="rgba(255,255,255,0.2)",
                projection_type="natural earth",
                bgcolor="rgba(0,0,0,0)",
                landcolor="rgba(50,50,50,0.8)",
                showocean=True,
                oceancolor="rgba(20,20,30,0.9)",
                showlakes=False,
                showcountries=True,
                countrycolor="rgba(255,255,255,0.1)",
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_map, width='stretch')

    # ── Ranking Bar Chart ─────────────────────────────────────────────────────
    st.markdown("---")
    with st.container(border=True):
        if oldest_latest_date == latest_date:
            rank_title_suffix = latest_date.strftime('%B %Y')
        else:
            rank_title_suffix = (
                f"Latest by country ({oldest_latest_date.strftime('%b %Y')} to "
                f"{latest_date.strftime('%b %Y')})"
            )
        st.markdown(f"#### 📊 Inflation Ranking — {rank_title_suffix}")

        region_filter_codes = (
            None if region_choice == "All"
            else set(REGION_GROUPS[region_choice])
        )

        if region_filter_codes is not None:
            bar_df = latest_individual[
                latest_individual["country_code"].isin(region_filter_codes)
            ].copy()
        else:
            bar_df = latest_individual.copy()

        bar_df = (
            bar_df.dropna(subset=["inflation_rate"])
            .sort_values("inflation_rate")
            .reset_index(drop=True)
        )
        bar_df["label"] = bar_df.apply(
            lambda r: f"{r['country_name']}  [{r['source']}]", axis=1
        )

        # Color by value: blue (low/negative) → white (0) → red (high)
        norm = bar_df["inflation_rate"]
        _max = max(abs(norm.min()), abs(norm.max())) or 1
        bar_colors = [
            f"rgb({int(min(255, 255 * max(0, v/_max)))}, "
            f"{int(max(0, 255 * (1 - abs(v/_max))))}, "
            f"{int(min(255, 255 * max(0, -v/_max)))})"
            for v in norm
        ]

        u2_rate = latest_df[latest_df["country_code"] == "U2"]["inflation_rate"]
        u2_val = float(u2_rate.iloc[0]) if not u2_rate.empty else None

        fig_rank = go.Figure(
            go.Bar(
                x=bar_df["inflation_rate"],
                y=bar_df["label"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:+.1f}%" for v in bar_df["inflation_rate"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Inflation: %{x:.2f}%<extra></extra>",
            )
        )

        if u2_val is not None:
            fig_rank.add_vline(
                x=u2_val,
                line_dash="dash",
                line_color="rgba(255,200,0,0.8)",
                line_width=1.5,
                annotation_text=f"Eurozone {u2_val:.1f}%",
                annotation_position="top",
                annotation_font_size=11,
                annotation_font_color="rgba(255,200,0,0.9)",
            )

        n_countries = len(bar_df)
        fig_rank.update_layout(
            xaxis_title="YoY Inflation Rate (%)",
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.3)", zerolinewidth=1),
            height=max(350, 22 * n_countries),
            margin=dict(l=10, r=90, t=10, b=30),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_rank, width='stretch')

# ── Historical Trend Chart ────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("#### 📈 Historical Trend")

    BAR_SOFT_LIMIT = 6  # grouped bars get cramped beyond this

    if not selected_codes:
        st.info("Select at least one country in the Filters panel to display the trend chart.")
    else:
        # Include Eurozone in bar traces if toggled (treated like any other country)
        trend_codes = list(selected_codes)
        if show_eurozone and "U2" not in trend_codes:
            trend_codes = ["U2"] + trend_codes

        n_series = len(trend_codes)
        if n_series > BAR_SOFT_LIMIT:
            st.warning(
                f"You have **{n_series} series** selected. "
                f"Grouped bars work best with ≤ {BAR_SOFT_LIMIT} countries — "
                "consider reducing your selection for a cleaner chart."
            )

        trend_df = df[
            (df["country_code"].isin(trend_codes)) &
            (df["Date"] >= start_date)
        ].copy()

        fig_trend = go.Figure()

        for idx, code in enumerate(trend_codes):
            series = trend_df[trend_df["country_code"] == code].sort_values("Date")
            if series.empty:
                continue
            name = series["country_name"].iloc[0]
            is_eurozone = code == "U2"
            fig_trend.add_trace(
                go.Bar(
                    x=series["Date"],
                    y=series["inflation_rate"],
                    name=name,
                    marker_color=("rgba(255,200,0,0.85)" if is_eurozone
                                  else LINE_COLORS[idx % len(LINE_COLORS)]),
                    hovertemplate=(
                        f"<b>{name}</b><br>"
                        "Date: %{x|%b %Y}<br>"
                        "Rate: <b>%{y:.2f}%</b><extra></extra>"
                    ),
                )
            )

        if show_ecb_target:
            fig_trend.add_hline(
                y=2,
                line_dash="dash",
                line_color="rgba(0,204,150,0.5)",
                annotation_text="ECB target 2%",
                annotation_position="right",
                annotation_font_size=10,
                annotation_font_color="rgba(0,204,150,0.8)",
            )

        fig_trend.add_hline(
            y=0,
            line_dash="dot",
            line_color="rgba(255,255,255,0.25)",
            opacity=0.7,
        )

        fig_trend.update_layout(
            barmode="group",
            bargap=0.15,
            bargroupgap=0.05,
            yaxis_title="YoY Inflation Rate (%)",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11),
            ),
            height=460,
            margin=dict(l=10, r=10, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, gridcolor="rgba(255,255,255,0.07)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
        )
        st.plotly_chart(fig_trend, width='stretch')

# ── Annual Heatmap ────────────────────────────────────────────────────────────
st.markdown("---")
with st.container(border=True):
    st.markdown("#### 🔥 Annual Inflation Heatmap")
    st.caption("Average YoY inflation rate per year, for selected countries. Sorted by most-recent year (descending).")

    heat_codes = selected_codes if selected_codes else eligible_codes[:20]
    heat_df = df[df["country_code"].isin(heat_codes)].copy()
    heat_df["Year"] = heat_df["Date"].dt.year

    pivot = (
        heat_df.groupby(["country_name", "Year"])["inflation_rate"]
        .mean()
        .unstack("Year")
    )

    # Sort by latest available year descending
    latest_year = pivot.columns.max()
    pivot = pivot.sort_values(latest_year, ascending=True)  # ascending=True → hottest at top in heatmap

    z_vals = pivot.values
    y_labels = pivot.index.tolist()
    x_labels = [str(c) for c in pivot.columns.tolist()]

    abs_heat_max = max(abs(float(pivot.min().min())), abs(float(pivot.max().max()))) if not pivot.empty else 10

    fig_heat = go.Figure(
        go.Heatmap(
            z=z_vals,
            x=x_labels,
            y=y_labels,
            colorscale="RdBu_r",
            zmid=0,
            zmin=-abs_heat_max,
            zmax=abs_heat_max,
            colorbar=dict(
                title=dict(text="YoY %", font=dict(size=12)),
                thickness=14,
                len=0.9,
            ),
            hovertemplate="<b>%{y}</b><br>Year: %{x}<br>Avg Inflation: %{z:.2f}%<extra></extra>",
            text=[[f"{v:.1f}%" if not pd.isna(v) else "N/A" for v in row] for row in z_vals],
            texttemplate="%{text}",
            textfont=dict(size=9),
        )
    )
    fig_heat.update_layout(
        height=max(280, 26 * len(y_labels)),
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(title="Year", side="bottom"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_heat, width='stretch')

# ── Raw Data Expander ─────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Raw data — latest available per country"):
    show_df = (
        latest_df[["country_name", "country_code", "inflation_rate", "source", "Date"]]
        .sort_values("inflation_rate", ascending=False)
        .reset_index(drop=True)
    )
    show_df["inflation_rate"] = show_df["inflation_rate"].round(2)
    show_df.columns = ["Country", "Code", "Inflation Rate (%)", "Source", "Date"]
    st.dataframe(show_df, width='stretch', hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    f"Sources: **Eurostat & ECB** (HICP YoY%) · "
    f"**OECD Data Explorer** (CPI YoY%). "
    f"Latest-by-country window: **{oldest_latest_date.strftime('%b %Y')}** to "
    f"**{latest_date.strftime('%b %Y')}**. "
    "Run `scripts/fetch_data.py` to refresh."
)
