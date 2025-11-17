import os
import re
import datetime as dt
import streamlit as st
import yfinance as yf
from openai import OpenAI

# -----------------------------
# Setup
# -----------------------------

st.set_page_config(page_title="NOVA", page_icon="✨")
st.title("✨ NOVA ")

# -----------------------------
# Load OpenAI Key
# -----------------------------

OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", None)

if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None


# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.title("Commands")
st.sidebar.subheader("Stocks")
st.sidebar.write("• price of AAPL")
st.sidebar.write("• check TSLA and MSFT")

st.sidebar.subheader("Chat")
st.sidebar.write("• ask anything")


# -----------------------------
# Stock Lookup
# -----------------------------

def lookup_stock(ticker: str):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
