import streamlit as st

st.set_page_config(
    page_title="MacroView",
    page_icon="🦅",
    layout="wide"
)

st.title("Welcome to the Macro Economics Analysis Dashboard! 📈")

st.sidebar.success("Select an analysis page above.")

st.markdown(
    """
    This is an interactive dashboard for analyzing financial market data.
    
    **👈 Select an analysis page from the sidebar** to get started.
    
    ### Available Pages:
    - **📈 Stock Analysis**: Peer comparison and technical analysis (price, RSI, normalized returns).
    - **📉 Euribor**: Live Euribor rates across all maturities, yield curve analysis, spread charts, and MoM change heatmap.
    """
)