import streamlit as st
import pandas as pd
import plotly.express as px

# Page config
st.set_page_config(
    page_title="EVE Market Predictions",
    page_icon="📈",
    layout="wide"
)

# Title and description
st.title("EVE Market Predictions")
st.markdown("""
This application provides market predictions for EVE Online items.
""")

# Sidebar
with st.sidebar:
    st.header("Settings")
    # Add filters here later
    st.markdown("---")
    st.markdown("Made with ❤️ by Thomas")

# Footer
st.markdown("---")
st.markdown("Data is updated daily from EVE Online's ESI.")
