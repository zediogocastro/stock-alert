import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.title("📊 Stock Peer Analysis")
st.markdown("Easily compare stocks against others in their peer group.")

# Load data
@st.cache_data
def load_data():
    try:
        # Adjust the path to be relative to the root of the project
        df = pd.read_parquet("data/transformed/master_table.parquet")
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        st.error("Master table not found. Please run the data pipeline first (`scripts/run_stock_check.py`).")
        st.stop()

df = load_data()

# --- Layout ---
col1, col2 = st.columns([0.3, 0.7])

# --- Left Column ---
with col1:
    with st.container(border=True):
        st.markdown("#### ⚙️ Selections")
        tickers = st.multiselect(
            "Stock tickers",
            df["identifier"].unique(),
            default=["AAPL", "MSFT", "AMZN", "TSLA"]
        )
        time_horizon = st.radio(
            "Time horizon",
            ["1 Month", "3 Months", "6 Months", "YTD", "1 Year", "5 Years"],
            index=3,
            horizontal=True
        )

    # Filter data based on selections
    if not tickers:
        st.warning("Please select at least one ticker.")
        st.stop()

    # Calculate date range
    end_date = df['Date'].max()
    if time_horizon == "1 Month":
        start_date = end_date - timedelta(days=30)
    elif time_horizon == "3 Months":
        start_date = end_date - timedelta(days=90)
    elif time_horizon == "6 Months":
        start_date = end_date - timedelta(days=180)
    elif time_horizon == "YTD":
        start_date = datetime(end_date.year, 1, 1).replace(tzinfo=end_date.tzinfo)
    elif time_horizon == "1 Year":
        start_date = end_date - timedelta(days=365)
    else: # 5 Years
        start_date = end_date - timedelta(days=365*5)

    df_filtered = df[(df['identifier'].isin(tickers)) & (df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

    # Normalize prices
    df_normalized = df_filtered.copy()
    if not df_normalized.empty:
        for ticker in tickers:
            base_price = df_normalized[df_normalized['identifier'] == ticker]['Close'].iloc[0]
            df_normalized.loc[df_normalized['identifier'] == ticker, 'Normalized Price'] = df_normalized['Close'] / base_price

    with st.container(border=True):
        st.markdown("#### 🏆 Performance")
        if not df_normalized.empty:
            performance = df_normalized.groupby('identifier')['Normalized Price'].last().sort_values(ascending=False)
            
            if not performance.empty:
                best_stock = performance.index[0]
                worst_stock = performance.index[-1]
                
                best_perf = (performance.iloc[0] - 1) * 100
                worst_perf = (performance.iloc[-1] - 1) * 100

                perf_col1, perf_col2 = st.columns(2)
                with perf_col1:
                    st.metric("Best stock", f"📈 {best_stock}", f"{best_perf:.2f}%")
                with perf_col2:
                    st.metric("Worst stock", f"📉 {worst_stock}", f"{worst_perf:.2f}%")
        else:
            st.info("Not enough data to calculate performance.")


# --- Right Column ---
with col2:
    with st.container(border=True):
        st.markdown("#### 📊 Peer Comparison")
        fig = go.Figure()
        for ticker in tickers:
            ticker_data = df_normalized[df_normalized['identifier'] == ticker]
            fig.add_trace(go.Scatter(x=ticker_data['Date'], y=ticker_data['Normalized Price'], name=ticker))

        if not df_normalized.empty:
            peer_average = df_normalized.groupby('Date')['Normalized Price'].mean()
            peer_ma = peer_average.rolling(window=21, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=peer_ma.index, 
                y=peer_ma.values, 
                name='21-Day Peer Average MA', 
                line=dict(color='black', dash='dot')
            ))

            fig.update_layout(yaxis_title="Normalized Price")
            st.plotly_chart(fig)
        else:
            st.info("Select tickers and a time horizon to see the comparison.")

# --- Individual Stock Analysis ---
st.markdown("---")
with st.container(border=True):
    st.markdown("### 🔬 Price and RSI Analysis")
    st.markdown("""
    This section pairs each stock's price chart with its Relative Strength Index (RSI). The RSI is a momentum oscillator that measures the speed and change of price movements. It oscillates between zero and 100.

    **How to use it for investing:**
    - **Overbought/Oversold Signals:** An RSI above 70 (red shaded area) can indicate that a stock is overbought and may be due for a price correction. An RSI below 30 (green shaded area) can suggest it's oversold and may be poised for a rebound.
    - **Divergence:** Look for divergences between price and RSI. If the price is making a new high but the RSI is not, it's a bearish divergence and could signal a potential reversal. Conversely, if the price makes a new low but the RSI doesn't, it's a bullish divergence, a potential buy signal.
    """)

    if not df_filtered.empty:
        num_cols = 2
        chart_cols = st.columns(num_cols)
        
        for i, ticker in enumerate(tickers):
            with chart_cols[i % num_cols]:
                st.markdown(f"##### {ticker}")
                ticker_data = df_filtered[df_filtered['identifier'] == ticker].copy()

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                      vertical_spacing=0.05, row_heights=[0.7, 0.3])

                fig.add_trace(
                    go.Scatter(x=ticker_data['Date'], y=ticker_data['Close'], name="Price", line=dict(color='black')),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=ticker_data['Date'], y=ticker_data['rsi_14d'], name="RSI", line=dict(color='black')),
                    row=2, col=1
                )

                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                ticker_data['overbought'] = ticker_data['rsi_14d'] > 70
                ticker_data['overbought_shifted'] = ticker_data['overbought'].shift(1, fill_value=False)
                overbought_starts = ticker_data[ticker_data['overbought'] & ~ticker_data['overbought_shifted']]['Date']
                overbought_ends = ticker_data[~ticker_data['overbought'] & ticker_data['overbought_shifted']]['Date']
                
                if len(overbought_starts) > len(overbought_ends):
                    overbought_ends = pd.concat([overbought_ends, pd.Series([ticker_data['Date'].iloc[-1]])], ignore_index=True)

                for start, end in zip(overbought_starts, overbought_ends):
                    fig.add_vrect(x0=start, x1=end, fillcolor="red", opacity=0.2, layer="below", line_width=0, row=1, col=1)

                ticker_data['oversold'] = ticker_data['rsi_14d'] < 30
                ticker_data['oversold_shifted'] = ticker_data['oversold'].shift(1, fill_value=False)
                oversold_starts = ticker_data[ticker_data['oversold'] & ~ticker_data['oversold_shifted']]['Date']
                oversold_ends = ticker_data[~ticker_data['oversold'] & ticker_data['oversold_shifted']]['Date']

                if len(oversold_starts) > len(oversold_ends):
                    oversold_ends = pd.concat([oversold_ends, pd.Series([ticker_data['Date'].iloc[-1]])], ignore_index=True)

                for start, end in zip(oversold_starts, oversold_ends):
                    fig.add_vrect(x0=start, x1=end, fillcolor="green", opacity=0.2, layer="below", line_width=0, row=1, col=1)

                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    height=400,
                    margin=dict(l=20, r=20, t=30, b=20)
                )
                fig.update_yaxes(title_text="Price", row=1, col=1)
                fig.update_yaxes(title_text="RSI", row=2, col=1)

                st.plotly_chart(fig)
    else:
        st.info("Select tickers to see the analysis.")