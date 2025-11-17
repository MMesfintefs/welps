# ===============================
# NOVA — Minimal Stable Demo App
# ===============================

import os
import re
import datetime as dt

import streamlit as st
import yfinance as yf

# ---- OpenAI (new SDK) ----
from openai import OpenAI


# ===============================
# Setup
# ===============================

st.set_page_config(page_title="NOVA", page_icon="✨")

st.title("✨ NOVA — Simple AI Assistant")


# ===============================
# Key Loading
# ===============================

OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", None)

if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None


# ===============================
# Sidebar Commands
# ===============================

st.sidebar.title("Commands")

st.sidebar.subheader("Stocks")
st.sidebar.write("• price of AAPL")
st.sidebar.write("• check TSLA and MSFT")

st.sidebar.subheader("Chat")
st.sidebar.write("• ask anything")


# ===============================
# Helper: Stock Lookup
# ===============================

def lookup_stock(ticker: str):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except:
        return None


def handle_stocks(text):
    tickers = re.findall(r"\b[A-Z]{2,5}\b", text.upper())
    tickers = [t for t in tickers if t not in ["OF", "THE"]]

    if not tickers:
        return "I didn’t find any valid stock tickers."

    response = "📊 **Stock Prices**\n\n"
    for t in tickers:
        price = lookup_stock(t)
        if price:
            response += f"• **{t}** — ${price:.2f}\n"
        else:
            response += f"• **{t}** — No data available\n"

    return response


# ===============================
# Helper: OpenAI Chat
# ===============================

def chat_with_openai(message):
    if client is None:
        return "AI not configured (missing OPENAI_API_KEY)."

    try:
        reply = client
