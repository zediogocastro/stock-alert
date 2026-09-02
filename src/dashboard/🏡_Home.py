import streamlit as st

st.set_page_config(page_title="MacroView", page_icon="🦅", layout="wide")

st.title("Welcome to the Macro Economics Analysis Dashboard! 📈")

st.sidebar.success("Select an analysis page above.")

st.markdown(
    """
    This is an interactive dashboard for analyzing financial market data.
    
    **👈 Select an analysis page from the sidebar** to get started.
    
    ### Available Pages:
    - **📈 Stock Analysis**: Peer comparison and technical analysis (price, RSI, normalized returns).
    - **📉 Euribor**: Live Euribor rates across all maturities, yield curve analysis, spread charts, and MoM change heatmap.
    - **🛢️ Crude Oil**: Brent and WTI price history, Brent–WTI spread analysis, and realized volatility — the key commodity to watch during geopolitical stress.
    - **🌍 Global Inflation**: World choropleth map, country ranking, multi-economy trend chart, and annual heatmap for 50+ economies (Eurostat + ECB + OECD).
    """
)
