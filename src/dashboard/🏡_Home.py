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
    - **Stock Analysis**: A powerful tool for peer comparison and technical analysis of individual stocks.
    
    More pages with economic data and other analyses will be added soon!
    """
)