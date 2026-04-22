# DEPRECATED: Old app - use trading_system/streamlit_app.py instead
import streamlit as st

st.set_page_config(page_title="AI Traders", layout="centered")
st.title("Please run the updated app:")
st.code("streamlit run trading_system/streamlit_app.py", language="bash")
st.info("The new app is in the trading_system folder with full CrewAI integration!")
